"""Public reference data returned by the API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class LocalizedName(BaseModel):
    name: str
    name_language: str | None
    name_fallback: bool


class Port(LocalizedName):
    id: int
    code: str
    unlocode: str | None
    port_type: str
    waterway_id: int
    country_code: str
    river_km: Decimal | None
    is_active: bool


class Lock(LocalizedName):
    id: int
    code: str
    port_id: int
    chamber_count: int | None
    chamber_length_m: Decimal | None
    chamber_width_m: Decimal | None
    max_draft_m: Decimal | None
    operator_id: int | None
    avg_transit_min: int | None
    river_km: Decimal | None


class Waterway(LocalizedName):
    id: int
    code: str
    waterway_type: str
    length_km: Decimal | None
    is_active: bool


class RiverSection(LocalizedName):
    id: int
    code: str
    waterway_id: int
    country_code: str
    km_from: Decimal
    km_to: Decimal
    risk_level: str
    max_draft_m: Decimal | None
    fairway_code: str | None


class Basin(LocalizedName):
    id: int
    code: str
    waterway_id: int


class VesselType(LocalizedName):
    code: str
    un_code_28: str | None
    ais_type_code: int | None
    cargo_category: str | None
    is_self_propelled: bool
    operating_area: str


class Operator(LocalizedName):
    id: int
    legal_name: str
    country_code: str
    website: str | None
    founded: int | None


class RouteStop(BaseModel):
    seq: int
    port_id: int
    typical_offset_h: Decimal | None


class Route(LocalizedName):
    id: int
    code: str
    origin_port_id: int
    dest_port_id: int
    distance_km: Decimal | None
    typical_duration_h: Decimal | None
    cargo_types: list[str] | None
    stops: list[RouteStop]


class CargoType(LocalizedName):
    code: str
    nst_code: str | None
    adn_code: str | None
    imdg_code: str | None
    is_bulk: bool
    is_container: bool


class Berth(BaseModel):
    id: int
    code: str
    length_m: Decimal | None
    depth_m: Decimal | None
    max_draft_m: Decimal | None
    unload_rate_t_h: Decimal | None


class Terminal(BaseModel):
    id: int
    operator_id: int | None
    annual_capacity_t: Decimal | None
    storage_capacity_t: Decimal | None
    rail_access: bool
    gear_types: list[str] | None


class PortDetail(Port):
    berths: list[Berth]
    terminals: list[Terminal]
    locks: list[Lock]


class LockStatus(BaseModel):
    id: int
    status: str
    valid_from: datetime
    valid_to: datetime | None
    note: str | None
    source: str


class LockDetail(Lock):
    statuses: list[LockStatus]
