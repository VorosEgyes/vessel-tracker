"""A 6 bites dekódolás unit tesztje (a `08` §4.1, a `04` §4.1).

**A mérésből igazolt értékek (a `bud01` vevő, a 2026-11-24-i mérés):**
- a `13HOI:0P0000VOHLCnHQKwvL05Ip` → a fizikai MMSI **227 006 760**,
  a `type` **1**;
- a `83Wj9l@j2dv=d<N=MhO@S@QU3L00` → a fizikai MMSI **243 173 873**,
  a `type` **8**.

> **A `08` §4.1 eredeti példái (a 244 660 000 és a 243 042 769) a
> vevő NORMALIZÁLT `mmsi` oszlopértékei voltak** → **a fizikai
> payload-dekódolás nem ezt adja** → **a `08` §4.1 javítva lett**
> (a 2026-11-24-i felfedezés).
"""

import pytest

from duna.ingest.decoder import (
    STANDARD_ARMOR,
    decode_message,
    decode_physical_6bit,
    decode_standard_6bit,
    encode_standard_6bit,
    payload_to_bits,
)


# ---------------------------------------------------------------------
# a 6 bites karakterkódolás (a 04 §4.1)
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    ("char", "value"),
    [
        ("0", 0),
        ("9", 9),
        ("A", 10),
        ("Z", 35),
        ("a", 36),
        ("z", 61),
        ("@", 62),
    ],
)
def test_a_standard_armor_ertekei(char, value):
    """A `04` §4.1 táblázata: a karakterek a 0–62 értékekre."""
    assert STANDARD_ARMOR[char] == value


def test_a_standard_armor_a_dekodalas_es_visszaalakitas():
    """A `decode_standard_6bit` és az `encode_standard_6bit` egymás
    fordítottja.

    **A standard armor karakterkészlete szűkebb** (a `0-9A-Za-z@`) →
    **a mérési payloadok `:` `<` `>` karakterei nem tartoznak bele** →
    **a round-trip csak a standard karakterekre működik.**
    """
    payload = "13HOI0P0000VOHLCnHQKwvL05Ip"  # a `:` nélkül
    assert encode_standard_6bit(decode_standard_6bit(payload)) == payload


def test_a_fizikai_ertekek_a_vevo_formaja():
    """A vevő a fizikai értékeket tárolja (a `chr(value + 48)`).

    **A mérés igazolja:** a vevő `type` oszlopa megegyezik a
    `payload[0]` karakter `ord - 48` értékével (a `B`→18, az `E`→21,
    a `G`→23, a `H`→24) → **a fizikai érték a karakter ord-48.**
    """
    assert decode_physical_6bit("B") == [18]
    assert decode_physical_6bit("E") == [21]
    assert decode_physical_6bit("G") == [23]
    assert decode_physical_6bit("H") == [24]
    assert decode_physical_6bit("?") == [15]


def test_a_fizikai_dekodalas_a_meresi_peldakon():
    """A fizikai dekódolás a mérési payloadokon a helyes típust adja.

    **A visszafejtés nem egyértelmű** (a vevő egy inverz táblázattal
    alakít karakterré) → **a fizikai forma decode-only** → **a
    mérésből igazolt értékekkel ellenőrizzük.**
    """
    # a 08 §4.1 peldak (a fizikai MMSI-vel, a 2026-11-24-i javitas)
    assert decode_message("13HOI:0P0000VOHLCnHQKwvL05Ip", physical=True).message_type == 1
    assert decode_message("83Wj9l@j2dv=d<N=MhO@S@QU3L00", physical=True).message_type == 8


def test_a_fizikai_dekodalas_a_gpsd_referencia_peldan():
    """**A GPSD/AIS referencia-példa** (a fizikai formátumban).

    A `15M67FC000G?ufbE`FepT@3n00Sa` a legismertebb AIS példa →
    **a fizikai dekódolás az MMSI-t HIBATLANUL adja: 366 053 209**
    (a standard armor-értékekkel 358 713 148 jönne ki → **a fizikai
    dekódolás a helyes**).
    """
    msg = decode_message("15M67FC000G?ufbE`FepT@3n00Sa", physical=True)
    assert msg.message_type == 1
    assert msg.mmsi == 366053209


def test_a_standard_armor_es_a_fizikai_elter():
    """A `B` a standard armorban 11, a fizikai értékben 18.

    **Ez a különbség a `type` oszlop értelmezését is meghatározza:**
    a vevő a FIZIKAI értéket írja → a `type=18` (a Class B) a
    standard armorral `L`(11) lenne.
    """
    assert decode_standard_6bit("B") == [11]
    assert decode_physical_6bit("B") == [18]


def test_a_standard_armor_elutasitja_a_meresi_karaktereket():
    """A `:` `<` `>` nem érvényes a standard armorban (a `04` §7).

    **Ez a mérésben is látszik:** a `bud01` vevő fizikai értékeket
    tárol → a mérési payloadot a FIZIKAI dekódolás kezeli.
    """
    for ch in ":<>":
        with pytest.raises(ValueError, match="ervénytelen AIS karakter"):
            decode_standard_6bit(ch)


def test_az_ervenytelen_karakter_hibat_dob():
    """A standard armorban érvénytelen karakter → `ValueError` (a `04` §7)."""
    with pytest.raises(ValueError, match="ervénytelen AIS karakter"):
        decode_standard_6bit("13HO!")


def test_a_ervenytelen_ertek_hibat_dob():
    """A 64-es érték nem érvényes."""
    with pytest.raises(ValueError, match="ervénytelen 6 bites érték"):
        encode_standard_6bit([64])


# ---------------------------------------------------------------------
# a bitek (a 04 §3.3: a fill_bits)
# ---------------------------------------------------------------------
def test_a_fill_bits_eltavolitas():
    """A kitöltő bitek nem kerülnek a kimenetbe (a `04` §3.3)."""
    assert len(payload_to_bits("13HO", 2)) == len(payload_to_bits("13HO", 0)) - 2


def test_a_payload_to_bits_a_hossz():
    """A 6 bites kódolás → a bitek száma a karakterek száma × 6."""
    assert len(payload_to_bits("12345")) == 30


# ---------------------------------------------------------------------
# a meresi peldak (a 08 §4.1 — a javított ertekekkel)
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    ("payload", "expected_mmsi", "expected_type"),
    [
        ("13HOI:0P0000VOHLCnHQKwvL05Ip", 227006760, 1),
        ("83Wj9l@j2dv=d<N=MhO@S@QU3L00", 243173873, 8),
    ],
)
def test_decode_known_messages(payload, expected_mmsi, expected_type):
    """A mért payloadokból a fizikai MMSI és a típus (a `08` §4.1)."""
    msg = decode_message(payload, physical=True)
    assert msg.mmsi == expected_mmsi
    assert msg.message_type == expected_type


def test_a_uzenet_tipusa():
    """A `13HOI...` payload a 3-as (pozíció) üzenet (a `04` §4.3)."""
    msg = decode_message("13HOI:0P0000VOHLCnHQKwvL05Ip", physical=True)
    assert msg.message_type == 1
    assert msg.is_position
    assert not msg.is_static


def test_a_rovid_payload_hibat_dob():
    """A túl rövid payload → `ValueError` (a `04` §7)."""
    with pytest.raises(ValueError, match="túl rövid"):
        decode_message("13")
