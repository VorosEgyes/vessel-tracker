"""A hajó-válaszok (a 03 §5.2).

**A `VesselListItem` a katalóguslista eleme** (a F-CAT-03 oszlopai:
a hajónév, a típus, az azonosító, az üzemeltető, az állapot).
"""

from __future__ import annotations

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
