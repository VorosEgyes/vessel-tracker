"""A bizonyossági szint unit tesztje (a F-DET-14, a F-CAT-14).

**A szabály forrása:** a 02 §6.2 `vessel_verification` nézet — **a
Python implementáció és az SQL nézet ugyanazt a logikát követi.**

**A mérési kontextus** (a 40 órás mérés, a `bud01` vevő): a hajók
**99,6%-a `name_only`** (az ENI-arány 0,4%) → **ez a szint a
leggyakoribb**, nem a ritka kivétel.
"""

import pytest

from duna.domain.verification import (
    Identifier,
    Origin,
    VerificationLevel,
    compute_verification_level,
    label,
)


# ---------------------------------------------------------------------
# az ais_identified (a legerősebb forrás)
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "identifier_type",
    ["eni", "imo"],
)
def test_ais_identified_az_aktualis_ais_azonositobol(identifier_type):
    """ENI vagy IMO, AIS eredettel → `ais_identified`."""
    assert (
        compute_verification_level(
            identifiers=[Identifier(identifier_type=identifier_type, origin="ais")]
        )
        == VerificationLevel.AIS_IDENTIFIED
    )


def test_az_ais_identified_ag_nem_fedi_le_a_mmsi_t():
    """A MMSI NEM ad `ais_identified`-et (az `ais_partial` ágba megy).

    **A 02 §6.2 nézet és a Python implementáció ugyanaz** → ha
    itt a MMSI `ais_identified` lenne, az `ais_partial` ág halott
    kód lenne a DB-ben is.
    """
    assert (
        compute_verification_level(identifiers=[Identifier(identifier_type="mmsi", origin="ais")])
        == VerificationLevel.AIS_PARTIAL
    )


def test_ais_identified_akkor_is_ha_van_operator_claimed():
    """Az AIS-azonosított mindent megelőz."""
    assert (
        compute_verification_level(
            identifiers=[Identifier(identifier_type="eni", origin="ais")],
            origins=[Origin(origin="operator_claimed")],
        )
        == VerificationLevel.AIS_IDENTIFIED
    )


# ---------------------------------------------------------------------
# az ais_partial
# ---------------------------------------------------------------------
def test_ais_partial_csak_mmsi_ais_eredettel():
    """MMSI AIS eredettel (ENI/IMO nélkül) → `ais_partial`."""
    assert (
        compute_verification_level(identifiers=[Identifier(identifier_type="mmsi", origin="ais")])
        == VerificationLevel.AIS_PARTIAL
    )


def test_ais_partial_nem_bevasz_arlo_mmsi_nem_aktiv():
    """A lezárt (történeti) MMSI nem számít → `name_only`."""
    assert (
        compute_verification_level(
            identifiers=[Identifier(identifier_type="mmsi", origin="ais", valid_to="2026-01-01")]
        )
        == VerificationLevel.NAME_ONLY
    )


def test_ais_partial_a_lezart_eni_nem_aktiv():
    """A lezárt ENI nem aktiv → a maradék MMSI → `ais_partial`."""
    assert (
        compute_verification_level(
            identifiers=[
                Identifier(identifier_type="eni", origin="ais", valid_to="2026-01-01"),
                Identifier(identifier_type="mmsi", origin="ais"),
            ]
        )
        == VerificationLevel.AIS_PARTIAL
    )


def test_a_lezart_azonositok_egyike_sem_szamit():
    """Ha minden azonosító lezárt → `name_only`."""
    assert (
        compute_verification_level(
            identifiers=[
                Identifier(identifier_type="eni", origin="ais", valid_to="2026-01-01"),
                Identifier(identifier_type="mmsi", origin="ais", valid_to="2026-01-01"),
            ]
        )
        == VerificationLevel.NAME_ONLY
    )


# ---------------------------------------------------------------------
# az operator_claimed
# ---------------------------------------------------------------------
def test_operator_claimed_a_vessel_data_origin_bel_rol():
    """Aktuális üzemeltetői állítás → `operator_claimed`."""
    assert (
        compute_verification_level(origins=[Origin(origin="operator_claimed")])
        == VerificationLevel.OPERATOR_CLAIMED
    )


def test_operator_claimed_akkor_is_ha_van_ais_hivatkozas():
    """Az üzemeltetői állítás → `operator_claimed`."""
    assert (
        compute_verification_level(
            identifiers=[Identifier(identifier_type="callsign", origin="official")],
            origins=[Origin(origin="operator_claimed")],
        )
        == VerificationLevel.OPERATOR_CLAIMED
    )


def test_a_lezart_operator_claimed_nem_szamit():
    """A nem aktuális (`is_current=False`) üzemeltetői állítás nem számít."""
    assert (
        compute_verification_level(origins=[Origin(origin="operator_claimed", is_current=False)])
        == VerificationLevel.NAME_ONLY
    )


# ---------------------------------------------------------------------
# a name_only (a mérésben a leggyakoribb)
# ---------------------------------------------------------------------
def test_name_only_a_név_alapján():
    """Név, de semmi más → `name_only`."""
    assert compute_verification_level() == VerificationLevel.NAME_ONLY


def test_name_only_az_egyeb_eredet_nem_valtoztatja():
    """Az `official` vagy az `editorial` eredet nem növeli a szintet."""
    assert (
        compute_verification_level(origins=[Origin(origin="official"), Origin(origin="editorial")])
        == VerificationLevel.NAME_ONLY
    )


def test_name_only_a_hivatkozas_nem_ais_eredet():
    """A hivatkozás (callsign) AIS-eredet nélkül → `name_only`."""
    assert (
        compute_verification_level(
            identifiers=[Identifier(identifier_type="callsign", origin="official")]
        )
        == VerificationLevel.NAME_ONLY
    )


# ---------------------------------------------------------------------
# az unverified
# ---------------------------------------------------------------------
def test_unverified_ha_nincs_nev():
    """Név nélkül és forrás nélkül → `unverified`."""
    assert compute_verification_level(has_name=False) == VerificationLevel.UNVERIFIED


# ---------------------------------------------------------------------
# a badge feliratai (a 05 §8.2)
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (VerificationLevel.AIS_IDENTIFIED, "AIS-azonosított"),
        (VerificationLevel.AIS_PARTIAL, "AIS-részleges"),
        (VerificationLevel.OPERATOR_CLAIMED, "Üzemeltető állítása"),
        (VerificationLevel.NAME_ONLY, "Név alapján — ENI nélkül"),
        (VerificationLevel.UNVERIFIED, "Forrás nélkül"),
    ],
)
def test_a_badge_magyar_felirata(level, expected):
    assert label(level) == expected
