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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from duna.db.models import (
    Operator,
    OperatorI18n,
    Vessel,
    VesselI18n,
    VesselIdentifier,
    VesselType,
    VesselTypeI18n,
)
from duna.db.views import VESSEL_VERIFICATION
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
    stmt = (
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
            # **AZ EGYEDI LABEL LÉNYEGES:** a `Vessel.verification_level`
            # (a TÁROLT érték) és a nézet oszlopa ugyanaz a nevű lenne
            # -> **a `row.verification_level` a TÁROLT értéket adná**
            # -> **a label egyedi** -> **a `row.computed_verification_level`
            # a SZÁMÍTOTT érték (a 03 §3.1).
            VESSEL_VERIFICATION.c.computed_verification_level.label("computed_verification_level"),
            VESSEL_VERIFICATION.c.is_stale.label("is_stale"),
        )
        .join(
            VesselI18n,
            (VesselI18n.vessel_id == Vessel.id) & (VesselI18n.lang == filters.lang),
        )
        .join(VesselType, VesselType.code == Vessel.vessel_type_code)
        .outerjoin(
            VesselTypeI18n,
            (VesselTypeI18n.vessel_type_code == VesselType.code)
            & (VesselTypeI18n.lang == filters.lang),
        )
        .outerjoin(Operator, Operator.id == Vessel.operator_id)
        .outerjoin(
            OperatorI18n,
            (OperatorI18n.operator_id == Vessel.operator_id) & (OperatorI18n.lang == filters.lang),
        )
        .outerjoin(
            VesselIdentifier,
            (VesselIdentifier.vessel_id == Vessel.id) & (VesselIdentifier.valid_to.is_(None)),
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
        stmt = stmt.where(VesselI18n.name.ilike(f"%{filters.q}%"))

    # **a rendezés** (a F-CAT-02: a hajónév az alapértelmezett)
    order_col = {
        "name": VesselI18n.name,
        "type": VesselTypeI18n.name,
        "operator": OperatorI18n.display_name,
        "length": Vessel.length_m,
        "updated_at": Vessel.updated_at,
    }.get(filters.sort, VesselI18n.name)
    stmt = stmt.order_by(
        order_col.desc() if filters.order == "desc" else order_col.asc(),
        Vessel.id.asc(),
    )

    return stmt


async def list_vessels(
    session: AsyncSession, filters: VesselFilters
) -> tuple[list[VesselListItem], int | None]:
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

    paged = stmt.limit(filters.per_page).offset(filters.offset)
    rows = (await session.execute(paged)).all()

    items = [
        VesselListItem(
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
        for row in rows
    ]
    return items, total
