"""A hajók lekérdezése és a write-oldal (a 03 §5.1).

**A router nem ír SQL-t** -> **a service tartja a lekérdezést**, a
repository pedig a SQLAlchemy query-ket.

**A WRITE-OLDAL (a 02 §8.1a):**
- **a `slug`-ot az alkalmazás generálja** (a `duna.domain.slug`) ->
  **a DB csak a `NOT NULL` + `UNIQUE` constraintet enforces**;
- **a `sort_name`-t az alkalmazás tölti be** (a `02` §8.1a: "a
  `sort_name`-t az ingest tölti be") -> **a NORMALIZÁLT alak**
  (a `duna.domain.text` `normalize_search_text`) -> **a trigger
  CSAK az üres `sort_name`-t állítja be** (a `02` v1.12) ->
  **így a DB `sort_name` mindig a `lower(unaccent(name))` alakja** ->
  **a trigram-index a keresést szolgálja ki** (a F-SRCH-03).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.models import Vessel, VesselI18n
from duna.domain.slug import generate_slug
from duna.domain.text import normalize_search_text
from duna.repositories.vessel_detail_repo import get_vessel_detail
from duna.repositories.vessel_repo import VesselFilters, list_vessels
from duna.repositories.vessel_sub_repo import (
    list_aliases,
    list_certificates,
    list_data_origins,
    list_identifiers,
    list_ownership,
)
from duna.schemas.vessel import (
    FieldOrigin,
    OwnershipPeriod,
    VesselAlias,
    VesselCertDetail,
    VesselDetail,
    VesselIdentifierDetail,
    VesselListItem,
)


@dataclass(frozen=True, slots=True)
class VesselWriteResult:
    """A write-oldal eredménye."""

    vessel_id: int
    slug: str
    created: bool


async def list_catalog(
    session: AsyncSession, filters: VesselFilters
) -> tuple[list[VesselListItem], int | None]:
    """A katalóguslista (a F-CAT-02)."""
    return await list_vessels(session, filters)


async def get_detail(
    session: AsyncSession, vessel_id: int, lang: str = "hu"
) -> VesselDetail | None:
    """A hajóadatlap (a F-DET-01…16)."""
    return await get_vessel_detail(session, vessel_id, lang)


async def get_aliases(session: AsyncSession, vessel_id: int) -> list[VesselAlias]:
    """A történeti nevek (a F-DET-05)."""
    return await list_aliases(session, vessel_id)


async def get_ownership(
    session: AsyncSession, vessel_id: int, lang: str = "hu"
) -> list[OwnershipPeriod]:
    """A tulajdonosváltások (a F-DET-05)."""
    return await list_ownership(session, vessel_id, lang)


async def get_certificates(session: AsyncSession, vessel_id: int) -> list[VesselCertDetail]:
    """A hajó engedélyei (a F-DET-02)."""
    return await list_certificates(session, vessel_id)


async def get_identifiers(session: AsyncSession, vessel_id: int) -> list[VesselIdentifierDetail]:
    """A hajó azonosítói (a F-DET-02, a F-DET-15)."""
    return await list_identifiers(session, vessel_id)


async def get_origins(session: AsyncSession, vessel_id: int) -> list[FieldOrigin]:
    """A mezőnkénti eredet (a F-DET-15)."""
    return await list_data_origins(session, vessel_id)


async def upsert_vessel_name(
    session: AsyncSession,
    vessel_id: int,
    lang: str,
    name: str,
) -> VesselWriteResult:
    """A hajónév beírása (a write-oldal).

    **A `sort_name` NORMALIZÁLT alakban kerül be** (a `02` §8.1a) ->
    **a trigger nem írja felül** (a `02` v1.12: csak az üres
    `sort_name`-t állítja) -> **a DB `sort_name` a
    `lower(unaccent(name))` alakja.**

    **A `slug` csak az új hajónál képződik** (a meglévőt nem
    módosítjuk → **a mély linkek nem törnek**, a F-CAT-07).

    **DE: a `vessel_i18n` upsert** -> **a trigger a `vessel_i18n`
    UPDATE-en fut** -> **a `sort_name`-t a service írja utána** ->
    **a sorrend kritikus.**
    """
    import sqlalchemy as sa

    # **a `created` az ELOTTAllAPOT-bol** -> **a `vessel_i18n` mar
    # letezett?** (a `rowcount` az `UPDATE`-nel a PostgreSQL-en nem
    # megbizható, a `mypy` is elkapja).
    existing = (
        await session.execute(
            sa.select(VesselI18n.vessel_id).where(
                (VesselI18n.vessel_id == vessel_id) & (VesselI18n.lang == lang)
            )
        )
    ).first()
    created = existing is None

    # **az upsert** -> **a `RETURNING`-es forma** (a `mypy` a
    # `rowcount`-ot nem fogadja el az `UPDATE`-hez).
    # **a PostgreSQL-specifikus `insert`** (a `on_conflict_do_update`
    # csak a `postgresql` dialecten van -> **a `mypy` a generic
    # `sa.insert`-et nem fogadja el**).
    stmt = (
        pg_insert(VesselI18n)
        .values(vessel_id=vessel_id, lang=lang, name=name)
        .on_conflict_do_update(
            index_elements=[VesselI18n.vessel_id, VesselI18n.lang],
            set_={"name": name},
        )
        .returning(VesselI18n.vessel_id)
    )
    await session.execute(stmt)

    # **a `sort_name` NORMALIZALTAN** (a trigger UTAN, hogy a trigger
    # ne írhassa felül)
    normalized = normalize_search_text(name)
    await session.execute(
        sa.update(Vessel).where(Vessel.id == vessel_id).values(sort_name=normalized)
    )

    # **a `slug`** (csak az uj hajon)
    vessel_row = (
        await session.execute(
            sa.select(Vessel.id, Vessel.slug, Vessel.mmsi).where(Vessel.id == vessel_id)
        )
    ).one()
    slug = vessel_row.slug
    if not slug:
        slug = generate_slug(name, vessel_row.mmsi)
        await session.execute(sa.update(Vessel).where(Vessel.id == vessel_id).values(slug=slug))

    await session.commit()
    return VesselWriteResult(vessel_id=vessel_id, slug=slug, created=created)
