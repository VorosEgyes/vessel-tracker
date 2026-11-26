"""A hajóadatlap lekérdezése (a 03 §3.1, §5.4 — a F-DET-01…16).

**A `GET /api/v1/vessels/{id}`** → **a `vessel` + a `vessel_i18n` +
a `vessel_type_i18n` + az `operator_i18n` + a `port` +
a `country` + a `vessel_verification` nézet** (az alapadatok) →
**a `vessel_data_origin` + a `data_source`** (a mezőnkénti eredet) →
**a `vessel_ownership` + az `operator_i18n`** (a hajtörténet) →
**a `vessel_last_position` nézet** (a „hol van").

**A `Decimal` -> `string` a válaszban** (a `prof` reviewer M-4
findingje) → **a `str()` konverzió a `VesselDetail` feltöltésekor.**
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from duna.db.models import (
    Country,
    Vessel,
)
from duna.db.views import VESSEL_LAST_POSITION, VESSEL_VERIFICATION
from duna.repositories.expressions import operator_name, port_name, vessel_name, vessel_type_name
from duna.repositories.vessel_sub_repo import list_data_origins, list_ownership
from duna.schemas.vessel import VesselDetail


def _decimal_to_str(value: Decimal | None) -> str | None:
    """A `Decimal` -> `string` (a `prof` reviewer M-4 findingje).

    **A JSON-ban a `Decimal` nem szabványos** → **a Pydantic stringként
    adja vissza** → **a `None` megmarad `None`-nek.**
    """
    return None if value is None else str(value)


def build_detail_query(vessel_id: int, lang: str) -> Select[Any]:
    """A hajóadatlap alapadatainak lekérdezése."""
    # **A `Select` tipusparametere INVARIANS** -> **a `select()` a
    # konret oszlopok miatt `Select[int, str, ...]`-t ad** ->
    # **a `Select[Any]` annotacio nem eleg** -> **a `cast` a
    # tipust szabaditja fel** (a `vessel_repo`-ban ugyanez a
    # megoldas).
    stmt = cast(
        Select[Any],
        select(
            Vessel.id,
            Vessel.slug,
            func.coalesce(vessel_name(lang), Vessel.sort_name).label("name"),
            Vessel.mmsi,
            Vessel.eni,
            Vessel.imo,
            Vessel.callsign,
            Vessel.status,
            Vessel.operating_area,
            func.coalesce(vessel_type_name(lang), Vessel.vessel_type_code).label(
                "vessel_type_name"
            ),
            operator_name(lang).label("operator_name"),
            port_name(lang).label("home_port_name"),
            Country.name_local.label("flag_country_name"),
            Vessel.build_year,
            Vessel.length_m,
            Vessel.beam_m,
            Vessel.draught_max_m,
            Vessel.gross_tonnage,
            Vessel.deadweight_t,
            Vessel.teu,
            Vessel.passenger_capacity,
            Vessel.is_passenger_certified,
            Vessel.destination,
            VESSEL_VERIFICATION.c.computed_verification_level.label("computed_verification_level"),
            VESSEL_VERIFICATION.c.is_stale.label("is_stale"),
            VESSEL_LAST_POSITION.c.ts.label("last_position_ts"),
            VESSEL_LAST_POSITION.c.river_km.label("last_river_km"),
            VESSEL_LAST_POSITION.c.river_section_id.label("river_section_id"),
            VESSEL_LAST_POSITION.c.basin_id.label("basin_id"),
        )
        .outerjoin(Country, Country.code == Vessel.flag_country_code)
        .outerjoin(
            VESSEL_VERIFICATION,
            VESSEL_VERIFICATION.c.vessel_id == Vessel.id,
        )
        .outerjoin(
            VESSEL_LAST_POSITION,
            VESSEL_LAST_POSITION.c.vessel_id == Vessel.id,
        )
        .where(Vessel.id == vessel_id),
    )
    return stmt


async def get_vessel_detail(
    session: AsyncSession, vessel_id: int, lang: str = "hu"
) -> VesselDetail | None:
    """A hajóadatlap (a F-DET-01…16).

    **`None`, ha nincs ilyen hajó** → **a router 404-et ad.**
    """
    stmt = build_detail_query(vessel_id, lang)
    row = (await session.execute(stmt)).first()
    if row is None:
        return None

    origins = await list_data_origins(session, vessel_id)
    ownership = await list_ownership(session, vessel_id, lang)
    location_text = None
    if row.last_position_ts is not None:
        location = (
            await session.execute(
                text("""
                    SELECT
                      (SELECT wi.name FROM waterway_i18n wi
                       WHERE wi.waterway_id = COALESCE(rs.waterway_id, b.waterway_id)
                       ORDER BY CASE WHEN wi.lang = :lang THEN 0
                                     WHEN wi.lang = 'en' THEN 1
                                     WHEN wi.lang = 'hu' THEN 2 ELSE 3 END, wi.lang
                       LIMIT 1) AS waterway_name,
                      (SELECT ri.name FROM river_section_i18n ri
                       WHERE ri.river_section_id = rs.id
                       ORDER BY CASE WHEN ri.lang = :lang THEN 0
                                     WHEN ri.lang = 'en' THEN 1
                                     WHEN ri.lang = 'hu' THEN 2 ELSE 3 END, ri.lang
                       LIMIT 1) AS section_name,
                      (SELECT bi.name FROM basin_i18n bi
                       WHERE bi.basin_id = b.id
                       ORDER BY CASE WHEN bi.lang = :lang THEN 0
                                     WHEN bi.lang = 'en' THEN 1
                                     WHEN bi.lang = 'hu' THEN 2 ELSE 3 END, bi.lang
                       LIMIT 1) AS basin_name
                    FROM (SELECT 1) base
                    LEFT JOIN river_section rs ON rs.id = :section_id
                    LEFT JOIN basin b ON b.id = :basin_id
                """),
                {"lang": lang, "section_id": row.river_section_id, "basin_id": row.basin_id},
            )
        ).one()
        parts = [location.waterway_name]
        if row.last_river_km is not None:
            parts.append(f"{row.last_river_km:.0f} km")
        parts.extend([location.section_name, location.basin_name])
        location_text = ", ".join(part for part in parts if part) or None

    return VesselDetail(
        id=row.id,
        name=row.name,
        slug=row.slug,
        mmsi=row.mmsi,
        eni=row.eni,
        imo=row.imo,
        callsign=row.callsign,
        verification_level=row.computed_verification_level,
        verification_source="stored_stale" if row.is_stale else "computed",
        status=row.status,
        operating_area=row.operating_area,
        vessel_type_name=row.vessel_type_name,
        operator_name=row.operator_name,
        home_port_name=row.home_port_name,
        flag_country_name=row.flag_country_name,
        build_year=row.build_year,
        length_m=_decimal_to_str(row.length_m),
        beam_m=_decimal_to_str(row.beam_m),
        draught_max_m=_decimal_to_str(row.draught_max_m),
        gross_tonnage=_decimal_to_str(row.gross_tonnage),
        deadweight_t=_decimal_to_str(row.deadweight_t),
        teu=row.teu,
        passenger_capacity=row.passenger_capacity,
        is_passenger_certified=row.is_passenger_certified,
        destination=row.destination,
        location_text=location_text,
        last_position_ts=row.last_position_ts,
        last_river_km=_decimal_to_str(row.last_river_km),
        origins=origins,
        ownership=ownership,
    )
