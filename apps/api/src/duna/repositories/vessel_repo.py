"""A katalóguslista lekérdezése (a 03 §3.1, §5.2).

**A JOIN-ek (a 03 §5.2 táblázata):**
- a `vessel` (a `id`, a `slug`, a `status`, az `operating_area`);
- a `vessel_i18n` (a `name`) — a nyelvenkénti JOIN;
- a `vessel_type` + a `vessel_type_i18n` (a `vessel_type_name`);
- a `operator` + a `operator_i18n` (a `operator_name`);
- a `vessel_identifier` (a `identifier`, az `identifier_type`);
- **a `vessel_verification` nézet** (a SZÁMÍTOTT `verification_level`).

**A `verification_level` a SZÁMÍTOTT érték** (a `bori` reviewer C-8
findingje) → **a tárolt `vessel.verification_level`-lal szemben a
nézet a hiteles** → **a `verification_source` jelzi, ha a tárolt
eltér** (`stored_stale`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from duna.db.models import (
    Vessel,
    VesselIdentifier,
)
from duna.db.views import VESSEL_VERIFICATION
from duna.domain.text import normalize_search_text
from duna.repositories.expressions import (
    display_identifier_id,
    operator_name,
    vessel_name,
    vessel_type_name,
)
from duna.schemas.vessel import VesselListItem


@dataclass(frozen=True, slots=True)
class VesselFilters:
    """A katalóguslista szűrői (a 03 §3.1).

    **Az `area` KÖTELEZŐ** (a F-CAT-01: a két katalógus
    elkülönül) → **a `query` rétegben kötelező.**
    """

    area: str
    lang: str = "hu"
    q: str | None = None
    type_code: str | None = None
    operator_id: int | None = None
    status: str | None = None
    verification: str | None = None
    sort: str = "name"
    order: str = "asc"
    page: int = 1
    per_page: int = 50

    @property
    def offset(self) -> int:
        """A lapozás eltolása."""
        return (self.page - 1) * self.per_page


def build_vessel_query(filters: VesselFilters) -> Select[Any]:
    """A katalóguslista lekérdezése (a szűrőkkel).

    **A `q` a trigram-alapú keresés** (a F-SRCH-01…03) → **a
    `vessel_i18n.name`-re** → **a `meta.total` ilyenkor `None`**
    (a 03 §5.5: "nem indexelhető").
    """
    name = vessel_name(filters.lang)
    type_name = func.coalesce(vessel_type_name(filters.lang), Vessel.vessel_type_code)
    operator = operator_name(filters.lang)
    stmt = (
        select(
            Vessel.id,
            Vessel.slug,
            func.coalesce(name, Vessel.sort_name).label("name"),
            type_name.label("vessel_type_name"),
            VesselIdentifier.value.label("identifier"),
            VesselIdentifier.identifier_type.label("identifier_type"),
            operator.label("operator_name"),
            Vessel.operating_area,
            Vessel.status,
            # **AZ EGYEDI LABEL LÉNYEGES:** a `Vessel.verification_level`
            # (a TÁROLT érték) és a nézet oszlopa ugyanaz a nevű lenne
            # -> **a `row.verification_level` a TÁROLT értéket adná**
            # -> **a label egyedi** -> **a `row.computed_verification_level`
            # a SZÁMÍTOTT érték (a 03 §3.1).
            VESSEL_VERIFICATION.c.computed_verification_level.label("computed_verification_level"),
            VESSEL_VERIFICATION.c.is_stale.label("is_stale"),
        )
        .outerjoin(
            VesselIdentifier,
            VesselIdentifier.id == display_identifier_id(filters.area),
        )
        .outerjoin(
            VESSEL_VERIFICATION,
            VESSEL_VERIFICATION.c.vessel_id == Vessel.id,
        )
        .where(Vessel.operating_area == filters.area)
    )

    if filters.type_code:
        stmt = stmt.where(Vessel.vessel_type_code == filters.type_code)
    if filters.operator_id is not None:
        stmt = stmt.where(Vessel.operator_id == filters.operator_id)
    if filters.status:
        stmt = stmt.where(Vessel.status == filters.status)
    if filters.verification:
        # **a TÁROLT érték** (a 03 §3.1: a szűrő indexelt -> a
        # tárolt `vessel.verification_level`-ra épül)
        stmt = stmt.where(Vessel.verification_level == filters.verification)
    if filters.q:
        # **A `q` a `vessel.sort_name`-re epul** (a F-SRCH-03) ->
        # **a `sort_name` a triggerben `lower(unaccent(name))`** ->
        # **a normalizalt keresokifejezes egyezik vele** ->
        # **a `vessel_sort_name_trgm` index hasznalodik**.
        #
        # **A `vessel_i18n.name` is kell** (a `vessel_i18n_name_trgm`
        # indexen) -> **az eredeti `q`-val** -> **a fejlesztoi
        # `pgserver`-ben (a `unaccent` NELKUL) a `sort_name` ekezetes,
        # igy csak ez talal** -> **a ket forma OR-ja mindket
        # kornyezetben ekezet-fuggetlen keresest ad**.
        normalized_q = normalize_search_text(filters.q)
        stmt = stmt.where(
            or_(
                Vessel.sort_name.contains(normalized_q),
                name.ilike(f"%{filters.q.strip()}%"),
                name.ilike(f"%{normalized_q}%"),
            )
        )

    # **a rendezés** (a F-CAT-02: a hajónév az alapértelmezett)
    order_col = {
        "name": func.coalesce(name, Vessel.sort_name),
        "type": type_name,
        "operator": operator,
        "length": Vessel.length_m,
        "updated_at": Vessel.updated_at,
    }.get(filters.sort, Vessel.sort_name)
    stmt = stmt.order_by(
        order_col.desc() if filters.order == "desc" else order_col.asc(),
        Vessel.id.asc(),
    )

    return stmt


def vessel_list_item(row: Row[Any]) -> VesselListItem:
    """Map a catalog query row consistently for listing and search."""
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


async def list_vessels(
    session: AsyncSession, filters: VesselFilters
) -> tuple[list[VesselListItem], int | None, bool]:
    """A katalóguslista (a lapozott elemek + a teljes darabszám).

    **A `meta.total` a szűrés utáni teljes darabszám** (a 03 §5.5) →
    **a `q` keresésnél `None`** (a trigram-alapú keresés nem
    indexelhető a számláláshoz).
    """
    stmt = build_vessel_query(filters)

    total: int | None = None
    if filters.q is None:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await session.execute(count_stmt)).scalar_one()

    paged = stmt.limit(filters.per_page + 1).offset(filters.offset)
    rows = (await session.execute(paged)).all()
    has_more = len(rows) > filters.per_page
    rows = rows[: filters.per_page]

    items = [vessel_list_item(row) for row in rows]
    return items, total, has_more
