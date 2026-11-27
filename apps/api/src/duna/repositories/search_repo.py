"""Global vessel search, with area isolation and identifier priority."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from duna.db.models import Vessel, VesselIdentifier
from duna.domain.text import normalize_search_text
from duna.repositories.expressions import vessel_name
from duna.repositories.vessel_repo import VesselFilters, build_vessel_query, vessel_list_item
from duna.schemas.vessel import VesselListItem


@dataclass(frozen=True, slots=True)
class SearchParams:
    area: str
    q: str
    lang: str = "hu"
    limit: int = 20


def _base_select(params: SearchParams) -> Select[Any]:
    return build_vessel_query(VesselFilters(area=params.area, lang=params.lang)).order_by(None)


def _identifier_match(raw: str) -> ColumnElement[bool]:
    return exists(
        select(VesselIdentifier.id)
        .where(
            VesselIdentifier.vessel_id == Vessel.id,
            VesselIdentifier.valid_to.is_(None),
            VesselIdentifier.value == raw,
        )
        .correlate(Vessel)
    )


def _name_match(raw: str, lang: str) -> ColumnElement[bool]:
    normalized = normalize_search_text(raw)
    name = vessel_name(lang)
    conditions: list[ColumnElement[bool]] = [
        name.ilike(f"%{raw}%"),
        Vessel.callsign.ilike(f"%{raw}%"),
    ]
    if normalized:
        conditions.extend([Vessel.sort_name.contains(normalized), name.ilike(f"%{normalized}%")])
    return or_(*conditions)


async def search(
    session: AsyncSession, params: SearchParams
) -> tuple[list[VesselListItem], int | None, bool, bool]:
    raw = params.q.strip()
    if not raw:
        raise ValueError("a keresoszoveg nem lehet ures")

    identifier_stmt = _base_select(params).where(_identifier_match(raw)).order_by(Vessel.id)
    rows = (await session.execute(identifier_stmt.limit(params.limit + 1))).all()
    if rows:
        count_stmt = select(func.count()).select_from(identifier_stmt.order_by(None).subquery())
        total = (await session.execute(count_stmt)).scalar_one()
        return (
            [vessel_list_item(row) for row in rows[: params.limit]],
            total,
            False,
            len(rows) > params.limit,
        )

    name_stmt = (
        _base_select(params)
        .where(_name_match(raw, params.lang))
        .order_by(Vessel.sort_name, Vessel.id)
    )
    rows = (await session.execute(name_stmt.limit(params.limit + 1))).all()
    items = [vessel_list_item(row) for row in rows[: params.limit]]
    other_has_matches = False
    if not items:
        other_area = "balaton" if params.area == "duna" else "duna"
        other = SearchParams(area=other_area, q=raw, lang=params.lang, limit=1)
        stmt = (
            _base_select(other)
            .where(or_(_identifier_match(raw), _name_match(raw, params.lang)))
            .limit(1)
        )
        other_has_matches = (await session.execute(stmt)).first() is not None
    return items, None, other_has_matches, len(rows) > params.limit
