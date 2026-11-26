"""A globális kereső (a 03 §3.2 — a F-SRCH-01…07).

**A KERESÉS KÉT LÉPCSŐBŐL ÁLL** (a 03 §3.2):

1. **először a pontos azonosító-egyezés** (a F-SRCH-02) → **az
   `vessel_identifier`-ben** (az `eni`, az `mmsi`, az `imo`, a
   `callsign`) → **a `vessel_identifier_value_trgm` index**;
2. **aztán a név-egyezés** (a F-SRCH-03) → **a `vessel.sort_name`-en**
   (a triggerben `lower(unaccent(name))` → **ékezet- és
   kis-nagybetű-független**) → **a `vessel_sort_name_trgm` index**.

**A `q` normalizálása az alkalmazás oldalán** (a `duna.domain.text`)
→ **egyezik a DB `sort_name`-ével.**

**A terület szűkít** (a F-SRCH-04, a F-SRCH-07) → **a `duna` keresés
soha nem talál Balaton-hajót.**

**A `meta.total` a trigram-alapú néven keresésnél `None`** (a 03 §5.5:
nem indexelhető a számláláshoz) → **az azonosító-egyezésnél a darabszám
pontos.**
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select as SelectType

from duna.db.models import (
    OperatorI18n,
    Vessel,
    VesselI18n,
    VesselIdentifier,
    VesselType,
    VesselTypeI18n,
)
from duna.db.views import VESSEL_VERIFICATION
from duna.domain.text import is_identifier_like, normalize_search_text
from duna.schemas.vessel import VesselListItem


@dataclass(frozen=True, slots=True)
class SearchParams:
    """A kereső paraméterei (a 03 §3.2)."""

    area: str
    q: str
    lang: str = "hu"
    limit: int = 20


def _base_select(filters: SearchParams) -> SelectType[Any]:
    """A közös SELECT (ugyanaz, mint a katalóguslistáé)."""
    return (
        select(
            Vessel.id,
            Vessel.slug,
            VesselI18n.name.label("name"),
            VesselTypeI18n.name.label("vessel_type_name"),
            VesselIdentifier.value.label("identifier"),
            VesselIdentifier.identifier_type.label("identifier_type"),
            OperatorI18n.display_name.label("operator_name"),
            Vessel.operating_area,
            Vessel.status,
            VESSEL_VERIFICATION.c.computed_verification_level.label("computed_verification_level"),
            VESSEL_VERIFICATION.c.is_stale.label("is_stale"),
        )
        .join(
            VesselI18n,
            (VesselI18n.vessel_id == Vessel.id) & (VesselI18n.lang == filters.lang),
        )
        .outerjoin(VesselType, VesselType.code == Vessel.vessel_type_code)
        .outerjoin(
            VesselTypeI18n,
            (VesselTypeI18n.vessel_type_code == VesselType.code)
            & (VesselTypeI18n.lang == filters.lang),
        )
        .outerjoin(OperatorI18n, OperatorI18n.operator_id == Vessel.operator_id)
        .outerjoin(
            VesselIdentifier,
            (VesselIdentifier.vessel_id == Vessel.id) & (VesselIdentifier.valid_to.is_(None)),
        )
        .outerjoin(VESSEL_VERIFICATION, VESSEL_VERIFICATION.c.vessel_id == Vessel.id)
        .where(Vessel.operating_area == filters.area)
    )


def _to_item(row: Any) -> VesselListItem:
    """A DB-sor -> a `VesselListItem`."""
    return VesselListItem(
        id=row.id,
        slug=row.slug,
        name=row.name,
        vessel_type_name=row.vessel_type_name,
        identifier=row.identifier,
        identifier_type=row.identifier_type,
        operator_name=row.operator_name,
        operating_area=row.operating_area,
        status=row.status,
        verification_level=row.computed_verification_level,
        verification_source="stored_stale" if row.is_stale else "computed",
    )


async def search(
    session: AsyncSession, params: SearchParams
) -> tuple[list[VesselListItem], int | None, bool]:
    """A globális keresés.

    **A visszatérés:** `(a találatok, a teljes darabszám vagy None,
    van-e találat a MASIK területen)`.

    **A harmadik érték a `meta.area_hint`-hoz kell** (a `bori`
    reviewer H-2 findingje) → **a szám NÉLKÜL** (a terület-szivárgás
    tiltása) → **a felhasználó tudja, hogy területet kell váltania,
    de nem tudja, melyik hajóról van szó.**
    """
    raw = params.q.strip()
    normalized = normalize_search_text(raw)

    # --- 1) a pontos azonosito-egyezes (a F-SRCH-02) ---
    if is_identifier_like(raw):
        identifier_stmt = (
            _base_select(params).where(VesselIdentifier.value == raw).order_by(Vessel.id.asc())
        )
        rows = (await session.execute(identifier_stmt.limit(params.limit))).all()
        if rows:
            count_stmt = select(func.count()).select_from(identifier_stmt.order_by(None).subquery())
            total = (await session.execute(count_stmt)).scalar_one()
            return [_to_item(r) for r in rows], total, False

    # --- 2) a nev-egyezes (a F-SRCH-03) ---
    #
    # **A KET FORMA:**
    # - a `vessel.sort_name` (a triggerben `lower(unaccent(name))`) ->
    #   **a normalizalt `q`-val egyezik** -> **ez a trigram-indexes
    #   ut** (a `vessel_sort_name_trgm`);
    # - a `vessel_i18n.name` (a `vessel_i18n_name_trgm` indexen) ->
    #   **az eredeti `q`-val egyezik** (a `lower(name)`).
    #
    # **MINDKETT kell:**
    # - **a production/CI DB-ben** (a `unaccent` extensionnel) a
    #   `sort_name` az ekezetmentes forma -> **a normalizalt `q`
    #   talal**;
    # - **a fejlesztoi `pgserver`-ben** (a `unaccent` NELKUL, a
    #   `strip_unaccent` preprocesszor miatt) a `sort_name` ekezetes ->
    #   **az eredeti `q` talal** a `vessel_i18n.name`-en.
    #
    # **A ket forma OR-ja mindket kornyezetben ekezet-fuggetlen
    # keresest ad.**
    if normalized:
        name_stmt = (
            _base_select(params)
            .where(
                or_(
                    # **a `sort_name`** (a triggerben `lower(unaccent(name))`)
                    # -> **a normalizalt `q`-val** -> **a trigram-indexes ut**
                    Vessel.sort_name.contains(normalized),
                    # **a `vessel_i18n.name`** (a `vessel_i18n_name_trgm`
                    # indexen) -> **AZ EREDETI `q`-val** (a `lower(name)`)
                    VesselI18n.name.ilike(f"%{raw}%"),
                    # **ES a normalizalt `q`-val is** -> **a fejlesztoi
                    # `pgserver`-ben (a `unaccent` NELKUL) a `sort_name`
                    # ekezetes, es a `name` is -> **a `q` normalizalt
                    # alakja nem talalja** -> **a ket forma OR-ja
                    # mindket kornyezetben ekezet-fuggetlen keresest ad**
                    VesselI18n.name.ilike(f"%{normalized}%"),
                    Vessel.callsign.ilike(f"%{raw}%"),
                )
            )
            .order_by(Vessel.sort_name.asc(), Vessel.id.asc())
        )
    else:
        name_stmt = _base_select(params).order_by(Vessel.sort_name.asc(), Vessel.id.asc())

    rows = (await session.execute(name_stmt.limit(params.limit))).all()
    items = [_to_item(r) for r in rows]

    # **a `meta.total` a trigram-alapú néven keresésnél `None`** (a
    # 03 §5.5: nem indexelhető a számláláshoz)
    name_total: int | None = None

    # --- a masik teruleten van-e talalat? (a `bori` H-2) ---
    other_area = "balaton" if params.area == "duna" else "duna"
    other_has_matches = await _other_area_has_match(session, params, normalized, other_area)

    return items, name_total, other_has_matches


async def _other_area_has_match(
    session: AsyncSession, params: SearchParams, normalized: str, other_area: str
) -> bool:
    """**Van-e találat a másik területen?** (a `bori` reviewer H-2)

    **A szám NÉLKÜL** → **csak a `has_matches` boolean** → **a
    terület-szivárgás tiltása** (a felhasználó nem tudja meg, melyik
    hajóról van szó).
    """
    other = SearchParams(area=other_area, q=params.q, lang=params.lang, limit=1)
    stmt = _base_select(other)
    if normalized:
        raw_other = params.q.strip()
        stmt = stmt.where(
            or_(
                Vessel.sort_name.contains(normalized),
                VesselI18n.name.ilike(f"%{raw_other}%"),
                VesselI18n.name.ilike(f"%{normalized}%"),
                Vessel.callsign.ilike(f"%{raw_other}%"),
            )
        )
    stmt = stmt.limit(1)
    result = await session.execute(stmt)
    return result.first() is not None
