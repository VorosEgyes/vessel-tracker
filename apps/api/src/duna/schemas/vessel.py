"""A hajó-válaszok (a 03 §5.2).

**A `VesselListItem` a katalóguslista eleme** (a F-CAT-03 oszlopai:
a hajónév, a típus, az azonosító, az üzemeltető, az állapot).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VesselListItem(BaseModel):
    """A katalóguslista egy eleme (a F-CAT-03 oszlopai).

    A `GET /api/v1/vessels` és a `GET /api/v1/search` ELEMETJE is
    ez a modell (a F-SRCH-05 ugyanezeket az oszlopokat kéri).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str = Field(description="a hajonev (nem fordul, a latin hivatalos ne)")
    vessel_type_name: str = Field(description="a tipus neve (fordul)")
    identifier: str | None = Field(
        default=None,
        description=(
            "a teruletenkenti azonosito: a Dunan az ENI, "
            "a Balatonon a hajoszam vagy a nemzeti hajoszam"
        ),
    )
    identifier_type: str | None = Field(
        default=None, description="'eni' | 'national_reg_no' | 'callsign' | ..."
    )
    operator_name: str | None = Field(default=None, description="az uzemelteto neve (fordul)")
    operating_area: str = Field(description="'duna' | 'balaton'")
    status: str = Field(description="'active' | 'excluded' | 'inactive' | 'scrapped'")
    verification_level: str = Field(
        description="a bizonyossagi szint (a badge) — a SZAMITOTT ertek"
    )
    verification_source: Literal["computed", "stored_stale"] = Field(
        default="computed",
        description="a badge forrasa; a 'stored_stale' az elterest jelzi",
    )


class FieldOrigin(BaseModel):
    """A mezőnkénti eredet (a F-DET-15 mezőnkénti eredete).

    **A `value_snapshot` az aktuális érték EBBEN az eredetben** → **a
    konfliktus (a `prof` reviewer C-3 findingje) csak ezzel látható:
    két forrás, két különböző érték.**
    """

    model_config = ConfigDict(from_attributes=True)

    field_name: str
    origin: Literal["ais", "operator_claimed", "official", "editorial"]
    value_snapshot: str | None = Field(
        default=None,
        description="az adott forrástól származó érték (a konfliktus láttatásához)",
    )
    observed_at: datetime
    confidence: float | None = None
    source_name: str | None = None
    is_current: bool = Field(
        default=True,
        description="False, ha a forrás már nem aktuális (a történet)",
    )


class OwnershipPeriod(BaseModel):
    """Egy tulajdonos periódus (a F-DET-05 hajtörténet blokkja)."""

    model_config = ConfigDict(from_attributes=True)

    operator_name: str = Field(description="az üzemeltető neve (fordul)")
    valid_from: date
    valid_to: date | None = Field(default=None, description="None = jelenleg is aktuális")


class VesselDetail(BaseModel):
    """A hajó adatlapja (a F-DET-01…16).

    **A `verification_level` a SZÁMÍTOTT érték** (a
    `vessel_verification` nézetből) → **nem a tároltból** → **a
    `verification_source` jelzi az eltérést** (`stored_stale`).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    mmsi: int | None = None
    eni: str | None = None
    imo: str | None = None
    callsign: str | None = None
    verification_level: str = Field(
        description=(
            "a bizonyossági badge — a SZÁMÍTOTT érték "
            "(ais_identified|ais_partial|operator_claimed|name_only|unverified; "
            "a 02 §6.2 vessel_verification nézet számítja, a 05 §8.2 a badge)"
        )
    )
    verification_source: Literal["computed", "stored_stale"] = Field(
        default="computed",
        description="a badge forrása; a 'stored_stale' az eltérést jelzi",
    )
    status: str
    operating_area: str
    vessel_type_name: str | None = Field(default=None, description="a típus neve (fordul)")
    operator_name: str | None = Field(default=None, description="az üzemeltető neve (fordul)")
    home_port_name: str | None = Field(default=None, description="a hazai kikötő neve (fordul)")
    flag_country_name: str | None = Field(default=None, description="a zászlóország neve")
    build_year: int | None = None
    length_m: str | None = Field(
        default=None, description="a hossz méterben (a Decimal stringként megy ki)"
    )
    beam_m: str | None = None
    draught_max_m: str | None = None
    gross_tonnage: str | None = None
    deadweight_t: str | None = None
    teu: int | None = None
    passenger_capacity: int | None = None
    is_passenger_certified: bool = False

    # **A szöveges „hol van"** (a F-DET-06, R1-ben szövegesen) →
    # **a `vessel_last_position` nézetből + a szakasz- és a
    # vízway-nevekből** (a 02 §6.3a)
    location_text: str | None = Field(
        default=None,
        description=(
            'pl. „Duna, 1642–1635 km, Szob–Budapest szakasz"; '
            "None, ha nincs pozícióadat (a F-DET-16 jelölése)"
        ),
    )
    last_position_ts: datetime | None = Field(
        default=None, description="az utolsó pozíció időbélyege"
    )
    last_river_km: str | None = Field(default=None, description="az utolsó folyó-kilométer")

    # **A CÉLÁLLOMÁS** (a `bori` reviewer B-C-3 findingje) → **a
    # mérésben 100%-ban üres** → **a szerkesztő adja meg kézzel**
    destination: str | None = Field(
        default=None,
        description="a hajó célállomása; None, ha még nincs megadva",
    )
    destination_eta: datetime | None = Field(
        default=None, description="a várható érkezés (a FI 10 `eta` mezője)"
    )

    # **A mezőnkénti eredet** (a F-DET-15) → **a `vessel_data_origin`**
    origins: list[FieldOrigin] = Field(
        default_factory=list,
        description="a mezőnkénti eredet (F-DET-15).",
    )

    # **A hajótörténet** (a F-DET-05): a korábbi nevek külön
    # végponton, a tulajdonosváltások itt.
    ownership: list[OwnershipPeriod] = Field(
        default_factory=list,
        description="a tulajdonosváltások (a dátumtartománnyal)",
    )


class VesselAlias(BaseModel):
    """A történeti név (a F-DET-05).

    **A `/aliases` a LEZÁRT neveket adja** (a `03` §3.1: a
    `valid_to IS NOT NULL` = a történet) → **a jelenlegi név a
    `vessel_i18n`-ből jön, nem duplikálódik itt.**
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_type: str = Field(description="'former' | 'official' | 'shipyard'")
    valid_from: date | None = None
    valid_to: date | None = None


class VesselIdentifierDetail(BaseModel):
    """A hajó azonosítója (a F-DET-02, a F-DET-15).

    **Az `/identifiers` szűrés nélkül mindent ad** (az aktív + a
    lezárt azonosítók egyaránt) → **a `valid_to` megmutatja, hogy
    aktív-e.**
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    identifier_type: str = Field(
        description="'eni' | 'imo' | 'mmsi' | 'callsign' | 'national_reg_no' | 'internal_code'"
    )
    value: str
    is_primary: bool = False
    origin: str = Field(description="'ais' | 'official' | 'operator_claimed'")
    valid_from: date | None = None
    valid_to: date | None = None
    source_name: str | None = Field(default=None, description="a forras neve (a `data_source`-bol)")


class VesselCertDetail(BaseModel):
    """A hajó engedélye (a F-DET-02)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cert_type: str
    authority: str | None = None
    issued_at: date | None = None
    expires_at: date | None = None
    document_ref: str | None = None
