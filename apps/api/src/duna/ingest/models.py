"""A normalizált AIS-rekord (a `04` §5 — a közös szerződés).

**A `02` és a `04` közötti EGYETLEN definíció** -> **a `02` ebből
generálja az oszlopokat** -> **a `position`/`vessel_static`/
`ais_message` táblák oszlopai itt vannak tükrözve.**

**A `04` §5 tanulsaga (a `bud01` vevő normalizálása):**
**a vevő `ais_message.mmsi` oszlopa NEM a `nmea` payloadból
számítható** -> **a mérési adat normalizált** -> **a hajót a
`mmsi` oszlopból vesszük**, **a nevet/hívójelet/type-ot a
`nmea`-ból dekódoljuk** (a `decoder.py`).

**A `msg_type`/`msg_subtype`:** **a `msg_type` ONMAGABAN nem eleg**
(a `02`: a belvízi FI 10 a 6-os/8-as `msg_type`, a Class B a 21-es)
-> **a `msg_subtype` a DAC/FID** (a `04` C-3 findingje).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NormalizedAisMessage(BaseModel):
    """A parser kimenete — a `02`-es terv sémaoszlopaival egyezik.

    **A `nav_status` a `02`-es sémában `text`** (a `prof` C-2
    findingje: a korábbi `int` nem illeszkedett) -> **a `02`-es CHECK
    értékészletével.**
    """

    model_config = ConfigDict(from_attributes=True)

    # **a forras**
    source_code: str = Field(description="a data_source.code")
    received_at: datetime = Field(description="a fogadas idopontja (UTC)")
    msg_hash: bytes = Field(description="a dedup-kulcs (sha256)")

    # **a hajo**
    mmsi: int
    eni: str | None = Field(default=None, description="a FI 10 vin-je")
    imo: int | None = None
    callsign: str | None = None
    name: str | None = Field(default=None, description="a FI 10 neve")

    # **a pozicio**
    ts: datetime | None = Field(default=None, description="a hajo GNSS-idobelyege")
    lat_e7: int | None = None
    lon_e7: int | None = None
    sog_mps: float | None = None
    cog_deg: float | None = None
    heading_deg: float | None = None
    rot_deg: float | None = None
    nav_status: str | None = None
    ais_accuracy_m: float | None = None
    river_km: float | None = Field(default=None, description="a fairway hectometre")

    # **a statikus meretek**
    vessel_type_code: str | None = None
    length_m: float | None = None
    beam_m: float | None = None
    draught_max_m: float | None = None
    draught_reference: Literal["RNW"] | None = Field(
        default=None, description="a merules referenciaja (a FI 10 flag-je)"
    )

    # **a diszpoziciok**
    msg_type: int = Field(description="az AIS type mezője (1-27)")
    msg_subtype: int | None = Field(
        default=None, description="a DAC/FID (a belvízi FI 10 vs. a 8-as)"
    )

    # **a forras novel**
    source_kind: Literal["ais", "derived", "manual"] = "ais"


class PositionUpsert(BaseModel):
    """A `position` tabla egy sora (a `02` §5.1).

    **A `geom` a PostGIS `geometry(Point,4326)`** -> **a fejlesztoi
    DB-ben (a `pgserver`, PostGIS nelkul) a `geom` `text`** -> **a
    `lat_e7`/`lon_e7` a biztonsagos iras** (a `CHECK` constraint-ek
    is ezekre vonatkoznak).
    """

    model_config = ConfigDict(from_attributes=True)

    vessel_id: int
    ts: datetime
    msg_type: int | None = None
    msg_subtype: int | None = None
    sog_mps: float | None = None
    cog_deg: float | None = None
    heading_deg: float | None = None
    rot_deg: float | None = None
    nav_status: str | None = None
    ais_accuracy_m: float | None = None
    lat_e7: int | None = None
    lon_e7: int | None = None
    river_km: float | None = None
    shoreline_km: float | None = None
    source_kind: str = "ais"
