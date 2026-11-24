"""A 6 bites dekódolás unit tesztje (a `08` §4.1, a `04` §4.1).

**A REFERENCIA: a `pyais`** (a `04` §11 Q6) — **a GPSD hivatalos
példáin a `pyais` és a mi dekódolásunk egyezik.**

**A GPSD/AIS referencia-példa:**
```
!AIVDM,1,1,,A,15M67FC000G?ufbE`FepT@3n00Sa,0*5C
```
→ a `type=1`, az **MMSI 366 053 209**, a `lat=37.802118`,
a `lon=-122.341618`.

**A `bud01` vevő fizikai `nmea` oszlopa ugyanez a kódolás** (a mérés
igazolja: a `type` 8000/8000 egyezik) → **a `physical=True` csak a
szándék kifejezésére szolgál.**
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
# a 6 bites karakterkódolás (a 04 §4.1, a GPSD/pyais szerint)
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "char"),
    [
        (0, "0"),
        (9, "9"),
        (10, ":"),
        (15, "?"),
        (39, "W"),
        (40, "`"),
        (50, "j"),
        (61, "u"),
        (62, "v"),
        (63, "w"),
    ],
)
def test_a_standard_armor_ertekei(value, char):
    """**A GPSD/pyais kódolás:** a 0-39 ertek -> `chr(v+48)`, a
    40-63 -> `chr(v+56)`.

    **A 40-es érték a backtick, az 50-es a `j`** → **a klasszikus
    armor (`A`-`Z`, `a`-`z`) NEM a standard** → **a `04` §4.1
    táblázata a GPSD-táblázatot írja le.**
    """
    assert STANDARD_ARMOR[char] == value


def test_a_standard_armor_a_dekodalas_es_visszaalakitas():
    """A `decode_standard_6bit` és az `encode_standard_6bit` egymás
    fordítottja."""
    payload = "15M67FC000G?ufbE`FepT@3n00Sa"
    assert encode_standard_6bit(decode_standard_6bit(payload)) == payload


def test_a_fizikai_dekodalas_azonos_a_standarddal():
    """A vevo fizikai formatuma = a standard armor (a GPSD szerint).

    **A mérés igazolja:** a `type` oszlop **8000/8000** egyezik.

    **A fizikai forma a `chr(v+48)` armor (a 0-39 tartomany) -> a
    standarddal egyezik a 0-39 tartomanyban.**
    """
    payload = "15M67FC000G?ufbE`FepT@3n00Sa"
    assert decode_physical_6bit(payload) == decode_standard_6bit(payload)


def test_az_ervenytelen_karakter_hibat_dob():
    """Az érvénytelen karakter → `ValueError` (a `04` §7)."""
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
# a GPSD referencia-peldak (a 08 §4.1)
# ---------------------------------------------------------------------
def test_a_gpsd_referencia_pelda():
    """**A GPSD/AIS referencia-példa** — a `pyais` referenciaértékei.

    A `!AIVDM,1,1,,A,15M67FC000G?ufbE`FepT@3n00Sa,0*5C` → a `type=1`,
    az **MMSI 366 053 209**.
    """
    msg = decode_message("15M67FC000G?ufbE`FepT@3n00Sa")
    assert msg.message_type == 1
    assert msg.mmsi == 366053209
    assert msg.is_position
    assert not msg.is_static


def test_a_meresi_peldak():
    """A `bud01` mérési payloadjai (a `08` §4.1).

    **A `physical=True` a vevő oszlopát jelöli** → **a `type` a
    mérési `type` oszloppal egyezik** (a mérés 8000/8000).
    """
    # a 08 §4.1 peldak (a fizikai MMSI-vel, a 2026-11-24-i javitas)
    assert decode_message("13HOI:0P0000VOHLCnHQKwvL05Ip", physical=True).message_type == 1
    assert decode_message("83Wj9l@j2dv=d<N=MhO@S@QU3L00", physical=True).message_type == 8


def test_a_rovid_payload_hibat_dob():
    """A túl rövid payload → `ValueError` (a `04` §7)."""
    with pytest.raises(ValueError, match="túl rövid"):
        decode_message("13")
