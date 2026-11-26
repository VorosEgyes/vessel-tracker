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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from duna.db.models import (
    Country,
    OperatorI18n,
    Port,
    PortI18n,
    Vessel,
    VesselI18n,
    VesselTypeI18n,
)
from duna.db.views import VESSEL_LAST_POSITION, VESSEL_VERIFICATION
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
            VesselI18n.name.label("name"),
            Vessel.mmsi,
            Vessel.eni,
            Vessel.imo,
            Vessel.callsign,
            Vessel.status,
            Vessel.operating_area,
            VesselTypeI18n.name.label("vessel_type_name"),
            OperatorI18n.display_name.label("operator_name"),
            PortI18n.name.label("home_port_name"),
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
        )
        .join(
            VesselI18n,
            (VesselI18n.vessel_id == Vessel.id) & (VesselI18n.lang == lang),
        )
        .outerjoin(VesselTypeI18n, VesselTypeI18n.vessel_type_code == Vessel.vessel_type_code)
        .outerjoin(OperatorI18n, OperatorI18n.operator_id == Vessel.operator_id)
        .outerjoin(Port, Port.id == Vessel.home_port_id)
        .outerjoin(PortI18n, (PortI18n.port_id == Port.id) & (PortI18n.lang == lang))
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
        location_text=None,
        last_position_ts=row.last_position_ts,
        last_river_km=_decimal_to_str(row.last_river_km),
        origins=origins,
        ownership=ownership,
    )
