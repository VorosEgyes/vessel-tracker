"""A hajóadatlap al-végpontjai (a 03 §3.1 — a F-DET-02, -05, -15).

**A `GET /api/v1/vessels/{id}/...` végpontok:**

| A végpont | A forrás | A szűrő |
|---|---|---|
| `/aliases` | a `vessel_alias` | **a LEZÁRTak** (`valid_to IS NOT NULL`) — a jelenlegi név a `vessel_i18n`-ből jön |
| `/ownership` | a `vessel_ownership` + az `operator_i18n` | **nincs** (a dátumtartomány a szűrő) |
| `/certificates` | a `vessel_cert` | **nincs** (az aktív + a lezárt egyaránt) |
| `/identifiers` | a `vessel_identifier` + a `data_source` | **nincs** (az aktív + a lezárt egyaránt) |
| `/data-origin` | a `vessel_data_origin` + a `data_source` | **csak az aktuális források** (`is_current`) |

**A `03` §3.1 megjegyzése:** az `/aliases` a **történeti** neveket
adja → **a szűrő `valid_to IS NOT NULL`** → **a `name_type='official'`
**és** `valid_to IS NULL` sor a **jelenlegi** név — az a
`vessel`/`vessel_i18n`-ből jön, **nem** duplikálódik itt.**
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.models import (
    DataSource,
    OperatorI18n,
    VesselAlias,
    VesselCert,
    VesselDataOrigin,
    VesselIdentifier,
    VesselOwnership,
)
from duna.repositories.expressions import language_order
from duna.schemas.vessel import (
    FieldOrigin,
    OwnershipPeriod,
    VesselCertDetail,
    VesselIdentifierDetail,
)
from duna.schemas.vessel import (
    VesselAlias as VesselAliasSchema,
)


async def list_aliases(session: AsyncSession, vessel_id: int) -> list[VesselAliasSchema]:
    """A történeti nevek (a F-DET-05) → **a `vessel_alias`**.

    **A LEZÁRTak** (`valid_to IS NOT NULL`) → **a jelenlegi név a
    `vessel_i18n`-ből jön** (a `03` §3.1).
    """
    stmt = (
        select(
            VesselAlias.id,
            VesselAlias.name,
            VesselAlias.name_type,
            VesselAlias.valid_from,
            VesselAlias.valid_to,
        )
        .where((VesselAlias.vessel_id == vessel_id) & (VesselAlias.valid_to.is_not(None)))
        .order_by(VesselAlias.valid_to.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        VesselAliasSchema(
            id=row.id,
            name=row.name,
            name_type=row.name_type,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
        )
        for row in rows
    ]


async def list_ownership(session: AsyncSession, vessel_id: int, lang: str) -> list[OwnershipPeriod]:
    """A tulajdonosváltások (a F-DET-05) → **a `vessel_ownership` +
    az `operator_i18n`** → **a legújabb elöl.**
    """
    operator_name = (
        select(OperatorI18n.display_name)
        .where(
            OperatorI18n.operator_id == VesselOwnership.operator_id,
            OperatorI18n.display_name.is_not(None),
        )
        .order_by(language_order(lang, OperatorI18n.lang), OperatorI18n.lang)
        .limit(1)
        .correlate(VesselOwnership)
        .scalar_subquery()
    )
    stmt = (
        select(
            operator_name.label("operator_name"),
            VesselOwnership.valid_from,
            VesselOwnership.valid_to,
        )
        .where(VesselOwnership.vessel_id == vessel_id)
        .order_by(VesselOwnership.valid_from.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        OwnershipPeriod(
            operator_name=row.operator_name,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
        )
        for row in rows
    ]


async def list_certificates(session: AsyncSession, vessel_id: int) -> list[VesselCertDetail]:
    """A hajó engedélyei (a F-DET-02) → **a `vessel_cert`**.

    **Szűrés NÉLKÜL** (a `03` §3.1) → **az aktív + a lezárt
    engedélyek egyaránt** → **a lejárton legrégebbi elöl.**
    """
    stmt = (
        select(
            VesselCert.id,
            VesselCert.cert_type,
            VesselCert.authority,
            VesselCert.issued_at,
            VesselCert.expires_at,
            VesselCert.document_ref,
        )
        .where(VesselCert.vessel_id == vessel_id)
        .order_by(VesselCert.expires_at.asc().nulls_last(), VesselCert.id.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        VesselCertDetail(
            id=row.id,
            cert_type=row.cert_type,
            authority=row.authority,
            issued_at=row.issued_at,
            expires_at=row.expires_at,
            document_ref=row.document_ref,
        )
        for row in rows
    ]


async def list_identifiers(session: AsyncSession, vessel_id: int) -> list[VesselIdentifierDetail]:
    """A hajó azonosítói (a F-DET-02, a F-DET-15) → **a
    `vessel_identifier` + a `data_source`**.

    **Szűrés NÉLKÜL** (a `03` §3.1) → **az aktív + a lezárt
    azonosítók egyaránt** → **az `is_primary` elöl.**
    """
    stmt = (
        select(
            VesselIdentifier.id,
            VesselIdentifier.identifier_type,
            VesselIdentifier.value,
            VesselIdentifier.is_primary,
            VesselIdentifier.origin,
            VesselIdentifier.valid_from,
            VesselIdentifier.valid_to,
            DataSource.name.label("source_name"),
        )
        .outerjoin(DataSource, DataSource.id == VesselIdentifier.source_id)
        .where(VesselIdentifier.vessel_id == vessel_id)
        .order_by(
            VesselIdentifier.is_primary.desc(),
            VesselIdentifier.identifier_type.asc(),
            VesselIdentifier.id.asc(),
        )
    )
    rows = (await session.execute(stmt)).all()
    return [
        VesselIdentifierDetail(
            id=row.id,
            identifier_type=row.identifier_type,
            value=row.value,
            is_primary=row.is_primary,
            origin=row.origin,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            source_name=row.source_name,
        )
        for row in rows
    ]


async def list_data_origins(session: AsyncSession, vessel_id: int) -> list[FieldOrigin]:
    """A mezőnkénti eredet (a F-DET-15) → **a `vessel_data_origin` +
    a `data_source`** → **csak az aktuális források** (`is_current`).
    """
    stmt = (
        select(
            VesselDataOrigin.field_name,
            VesselDataOrigin.origin,
            VesselDataOrigin.value_snapshot,
            VesselDataOrigin.observed_at,
            VesselDataOrigin.confidence,
            VesselDataOrigin.is_current,
            DataSource.name.label("source_name"),
        )
        .outerjoin(DataSource, DataSource.id == VesselDataOrigin.source_id)
        .where((VesselDataOrigin.vessel_id == vessel_id) & (VesselDataOrigin.is_current.is_(True)))
        .order_by(VesselDataOrigin.field_name, VesselDataOrigin.observed_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        FieldOrigin(
            field_name=row.field_name,
            origin=row.origin,
            value_snapshot=row.value_snapshot,
            observed_at=row.observed_at,
            confidence=float(row.confidence) if row.confidence is not None else None,
            source_name=row.source_name,
            is_current=row.is_current,
        )
        for row in rows
    ]
