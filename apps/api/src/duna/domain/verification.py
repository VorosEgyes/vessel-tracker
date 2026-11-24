"""A bizonyossági szint számítása (a F-DET-14, a F-CAT-14).

**Mi ez:** a hajó adatlap fejlécében megjelenő badge (az 05 §8.2). A
`03` §5.4 szerint a `verification_level` **SZÁMÍTOTT** érték — nem
szabadon beírható (a F-NF-12: „jogi: minden adathoz a forrás").

**A kanonikus szabály** (a 02 §6.2 `vessel_verification` nézet
tükrözete — **a kettőnek egyeznie kell**):

| A szint | A feltétel |
|---|---|
| `ais_identified` | van aktív ENI vagy IMO azonosító `ais` eredettel |
| `ais_partial` | van aktív MMSI `ais` eredettel (de nincs ENI/IMO) |
| `operator_claimed` | van aktív `operator_claimed` eredet |
| `name_only` | van név, de semmi más |
| `unverified` | forrás nélkül (nincs semmi) |

**A sorrend fontos:** az AIS-azonosított mindent megelőz, mert a
legerősebb forrás. Az `ais_partial` csak akkor él, ha nincs erősebb
AIS-azonosító.

**A tiszta függvény:** a bemenet egy egyszerű adatszerkezet (a
`Identifier` és az `Origin` dataclass), a kimenet egy szint.
**Nincs DB, nincs SQL** → unit tesztelhető (a 08 §2.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# **Az `ais_identified` azonosító típusai** (a 02 §5.1
# `vessel_identifier.identifier_type`) — **a MMSI NINCS benne**, mert
# az a `ais_partial` szintet adja (a 05 §8.2) → **mind az 5 szint
# elérhető.**
IDENTIFIER_TYPES = frozenset({"eni", "imo"})

# Az `ais_partial` azonosító típusa
IDENTIFIER_TYPE_MMSI = "mmsi"

# Az eredetek (a 02 §5.1 `vessel_data_origin.origin`)
ORIGIN_AIS = "ais"
ORIGIN_OPERATOR_CLAIMED = "operator_claimed"


class VerificationLevel(StrEnum):
    """A bizonyossági szint (a 05 §8.2 badge)."""

    AIS_IDENTIFIED = "ais_identified"
    AIS_PARTIAL = "ais_partial"
    OPERATOR_CLAIMED = "operator_claimed"
    NAME_ONLY = "name_only"
    UNVERIFIED = "unverified"


# A magyar felirat (a 05 §8.2 táblázata)
LABELS: dict[VerificationLevel, str] = {
    VerificationLevel.AIS_IDENTIFIED: "AIS-azonosított",
    VerificationLevel.AIS_PARTIAL: "AIS-részleges",
    VerificationLevel.OPERATOR_CLAIMED: "Üzemeltető állítása",
    VerificationLevel.NAME_ONLY: "Név alapján — ENI nélkül",
    VerificationLevel.UNVERIFIED: "Forrás nélkül",
}


@dataclass(frozen=True, slots=True)
class Identifier:
    """Egy hajóazonosító (a `vessel_identifier` egy sora).

    **A `valid_to is None` jelenti az AKTÍV-t** (a 02 §5.1: az
    egyediség és a számítás is csak az aktívakra vonatkozik).
    """

    identifier_type: str
    origin: str
    valid_to: str | None = None

    @property
    def is_active(self) -> bool:
        return self.valid_to is None

    @property
    def is_ais(self) -> bool:
        return self.origin == ORIGIN_AIS

    @property
    def is_ais_identifier(self) -> bool:
        """AIS-eredetű, aktív, és ENI/IMO típusú.

        **A MMSI nem tartozik bele** → az a `ais_partial` szintet adja.
        """
        return self.is_active and self.is_ais and self.identifier_type in IDENTIFIER_TYPES

    @property
    def is_ais_mmsi(self) -> bool:
        """AIS-eredetű, aktív MMSI (az `ais_partial` szintje)."""
        return self.is_active and self.is_ais and self.identifier_type == IDENTIFIER_TYPE_MMSI


@dataclass(frozen=True, slots=True)
class Origin:
    """Egy mező eredete (a `vessel_data_origin` egy sora).

    **A `is_current` jelenti az aktuálisat** — a számítás csak az
    aktuális eredeteket nézi (a 02 §6.2).
    """

    origin: str
    is_current: bool = True

    @property
    def is_operator_claimed(self) -> bool:
        return self.is_current and self.origin == ORIGIN_OPERATOR_CLAIMED


def compute_verification_level(
    identifiers: list[Identifier] | tuple[Identifier, ...] = (),
    origins: list[Origin] | tuple[Origin, ...] = (),
    *,
    has_name: bool = True,
) -> VerificationLevel:
    """A bizonyossági szint kiszámítása.

    Args:
        identifiers: a hajó azonosítói (`vessel_identifier`).
        origins: a hajó mezőinek eredetei (`vessel_data_origin`).
        has_name: van-e név a hajónak (a `name_only` és az
            `unverified` között ezt dönti el).

    Returns:
        A bizonyossági szint.

    **A sorrend** (a legerősebb forrás előbb):
    1. `ais_identified` — aktív AIS ENI vagy IMO;
    2. `ais_partial` — aktív AIS MMSI (de nincs ENI/IMO);
    3. `operator_claimed` — aktuális üzemeltetői állítás;
    4. `name_only` — van név;
    5. `unverified` — forrás nélkül.
    """
    # 1) AIS-azonosított: ENI vagy IMO, AIS eredettel
    #    (**A MMSI NEM benne** -> különben a 2. ág halott kód lenne)
    if any(i.is_ais_identifier for i in identifiers):
        return VerificationLevel.AIS_IDENTIFIED

    # 2) AIS-részleges: MMSI, AIS eredettel (de nincs ENI/IMO)
    if any(i.is_ais_mmsi for i in identifiers):
        return VerificationLevel.AIS_PARTIAL

    # 3) Üzemeltető állítása
    if any(o.is_operator_claimed for o in origins):
        return VerificationLevel.OPERATOR_CLAIMED

    # 4) Név alapján (a mérésben a hajók 99,6%-a ez)
    if has_name:
        return VerificationLevel.NAME_ONLY

    # 5) Forrás nélkül
    return VerificationLevel.UNVERIFIED


def label(level: VerificationLevel) -> str:
    """A badge magyar felirata (a 05 §8.2)."""
    return LABELS[level]
