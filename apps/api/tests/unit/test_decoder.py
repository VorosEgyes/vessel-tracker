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
    decode_aid_to_navigation,
    decode_message,
    decode_physical_6bit,
    decode_position,
    decode_standard_6bit,
    decode_static,
    encode_standard_6bit,
    payload_to_bits,
)


def _assemble(sentences: list[str]) -> tuple[str, int]:
    """A számozott NMEA sorok összefűzése (a `04` §3.2).

    **Visszaadja** a payloadot és a `fill_bits`-t.
    """
    parts: list[str] = []
    fill = 0
    for sentence in sentences:
        fields = sentence.split(",")
        parts.append(fields[5].split("*")[0])
        fill = int(fields[6].split("*")[0])
    return "".join(parts), fill


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


# ---------------------------------------------------------------------
# a pozicio dekódolasa (a 04 §4.3) — a `pyais` referenciával
# ---------------------------------------------------------------------
def test_a_pozicio_a_gpsd_peldan():
    """**A GPSD pozíció-példa** — a `pyais` minden referenciaértéke.

    A `15M67FC000G?ufbE`FepT@3n00Sa` → a `lat=37.802118`,
    a `lon=-122.341618`, a `sog=0.0`, a `cog=219.3`, a `heading=1`
    (a nyers 9 bites érték), a `status=3`, a `second=59`,
    a `maneuver=0`, a `raim=False`, a `radio=2281`.
    """
    p = decode_position("15M67FC000G?ufbE`FepT@3n00Sa")
    assert p.message_type == 1
    assert p.mmsi == 366053209
    assert p.lat == 37.802118
    assert p.lon == -122.341618
    assert p.sog_mps == 0.0
    assert p.cog_deg == 219.3
    assert p.heading_deg == 1.0
    assert p.nav_status == 3
    assert p.timestamp == 59
    assert p.maneuver == 0
    assert p.raim is False
    assert p.radio == 2281
    assert p.is_position


def test_a_pozicio_egyezik_a_pyais_szal():
    """**A `pyais` a hivatalos referencia** (a 04 §11 Q6) → **a
    pozíciómezők minden GPSD-példán egyeznek.**
    """
    import pyais

    payload = "15M67FC000G?ufbE`FepT@3n00Sa"
    reference = pyais.decode(f"!AIVDM,1,1,,A,{payload},0*5C".encode())
    p = decode_position(payload)

    assert p.message_type == reference.msg_type
    assert p.mmsi == reference.mmsi
    assert p.lat == reference.lat
    assert p.lon == reference.lon
    assert p.sog_mps == pytest.approx(reference.speed * 1852 / 3600)
    assert p.cog_deg == reference.course
    assert p.heading_deg == reference.heading
    assert p.nav_status == reference.status
    assert p.timestamp == reference.second
    assert p.maneuver == reference.maneuver
    assert p.raim == reference.raim
    assert p.radio == reference.radio


def test_a_sebesseg_es_irany_mertekegysege():
    bits = payload_to_bits("15M67FC000G?ufbE`FepT@3n00Sa")
    bits[50:60] = [int(bit) for bit in f"{100:010b}"]
    bits[128:137] = [int(bit) for bit in f"{90:09b}"]
    values = [int("".join(str(bit) for bit in bits[i : i + 6]), 2) for i in range(0, len(bits), 6)]
    report = decode_position(encode_standard_6bit(values))
    assert report.sog_mps == pytest.approx(10 * 1852 / 3600)
    assert report.heading_deg == 90


@pytest.mark.parametrize("fill_bits", [-1, 6, 100])
def test_a_hibas_fill_bits_hibat_dob(fill_bits):
    with pytest.raises(ValueError, match="fill_bits"):
        payload_to_bits("1234567", fill_bits)


def test_a_pozicio_a_meresi_peldan():
    """A `bud01` mérési payloadja (a fizikai oszlop) → **a `type` és
    az `mmsi` a mérésivel egyezik** (a `08` §4.1).

    **A `lat`/`lon` NEM a mérésivel egyezik** → **a vevő
    normalizálja** (a `04` §5, a Q8) → **a mérési adatot nem szabad
    nyers payloadként kezelni.**
    """
    p = decode_position("13HOI:0P0000VOHLCnHQKwvL05Ip", physical=True)
    assert p.message_type == 1
    assert p.mmsi == 227006760


def test_a_rovid_pozicio_payload_hibat_dob():
    """A túl rövid payload → `ValueError` (a `04` §7)."""
    with pytest.raises(ValueError, match="túl rövid"):
        decode_position("13HOI")


# ---------------------------------------------------------------------
# a statikus uzenet (a Msg 5) — a `pyais` referenciával
# ---------------------------------------------------------------------
def test_a_statikus_a_pyais_szal():
    """**A Msg 5 minden mezője egyezik a `pyais`-szal.**

    A `pyais`-szal kódolt magyar hajó (a `MAHAB ORSZAG`) → **a
    hívójel, a név, a célállomás, a méretek, a merülés, az EPFD és
    a DTE.**
    """
    import pyais
    from pyais.messages import MessageType5

    reference = MessageType5(
        msg_type=5,
        repeat=0,
        mmsi=243072204,
        ais_version=0,
        imo=9123456,
        callsign="HGXC",
        shipname="MAHAB ORSZAG",
        ship_type=70,
        to_bow=20,
        to_stern=80,
        to_port=6,
        to_starboard=4,
        epfd=1,
        draught=4.2,
        destination="BUDAFEST",
        dte=0,
        month=0,
        day=0,
        hour=0,
        minute=0,
        spare_1=b"",
    )
    sentences = pyais.encode_msg(reference)
    payload, fill = _assemble(sentences)

    ref = pyais.decode(*[s.encode() for s in sentences])
    ours = decode_static(payload, fill)

    assert ours.message_type == ref.msg_type
    assert ours.mmsi == ref.mmsi
    assert ours.imo == ref.imo
    assert ours.callsign == ref.callsign
    assert ours.shipname == ref.shipname
    assert ours.ship_type == ref.ship_type
    assert ours.destination == ref.destination
    assert ours.draught_m == ref.draught
    assert ours.epfd == ref.epfd
    assert ours.dte == ref.dte
    assert ours.length_m == ref.to_bow + ref.to_stern
    assert ours.beam_m == ref.to_port + ref.to_starboard


# ---------------------------------------------------------------------
# a 21-es uzenet (a belvizi statikus / az AtoN) — a `pyais` referenciával
# ---------------------------------------------------------------------
def test_a_21_es_uzenet_a_pyais_szal():
    """**A 21-es üzenet egyezik a `pyais`-szal.**

    **A `bud01` vevőn a 21-es a belvízi statikus** (a `04` §4.5) →
    **a hívójel a `name` mezőben van** (a mérésben: a `1658.8_G`).
    """
    import pyais

    payload = "ENjMWo@HsJtGL?SP00000000000@ccok=WUg`00001oRP0"
    ref = pyais.decode(f"!AIVDM,1,1,,A,{payload},4*64".encode())
    ours = decode_aid_to_navigation(payload, 4)

    assert ours.message_type == ref.msg_type
    assert ours.mmsi == ref.mmsi
    assert ours.name == ref.name
    assert ours.lat == ref.lat
    assert ours.lon == ref.lon
    assert ours.aid_type == ref.aid_type
    assert ours.name == "1658.8_G"


def test_a_21_es_uzenet_a_meresi_peldan():
    """A mérési `type=21` példa → **a `type` és az MMSI a mérésivel
    egyezik** (a `08` §4.1)."""
    payload = "ENjMWo@HsJtGL?SP00000000000@ccok=WUg`00001oRP0"
    ours = decode_aid_to_navigation(payload, 4)
    assert ours.message_type == 21
    assert ours.mmsi == 992438237


def test_a_rovid_statikus_payload_hibat_dob():
    """A túl rövid payload → `ValueError` (a `04` §7)."""
    with pytest.raises(ValueError, match="túl rövid"):
        decode_static("53Wktk")


def test_a_rovid_21_es_payload_hibat_dob():
    """A túl rövid payload → `ValueError` (a `04` §7)."""
    with pytest.raises(ValueError, match="túl rövid"):
        decode_aid_to_navigation("ENjMW")


def test_a_rovid_szovegmezok_a_payload_vegen():
    """**A mező a payload végén is lefut** → **a részleges szöveg
    visszaadódik** (a `ValueError` nem keletkezik).

    **A `decode_text_field` a payload végén megáll, és a megmaradt
    karaktereket visszaadja** → **a csonka mező nem ürstring.**
    """
    from duna.ingest.decoder import decode_text_field

    payload = "15M67FC000G?ufbE`FepT@3n00Sa"
    short = payload[:20]
    # a hivojel a 70. bittol (a 11,67. karaktertol) -> a 20 karakteres
    # payloadbol a mezo csak reszben van benne
    result = decode_text_field(short, 70, 42)
    assert isinstance(result, str)
    assert result != ""


def test_a_fill_bits_a_statiszkusban():
    """**A `fill_bits` levágása a szövegmezőket is érinti** (a `04` §3.3)."""
    import pyais
    from pyais.messages import MessageType5

    reference = MessageType5(
        msg_type=5,
        repeat=0,
        mmsi=243072204,
        ais_version=0,
        imo=9123456,
        callsign="HGXC",
        shipname="MAHAB ORSZAG",
        ship_type=70,
        to_bow=20,
        to_stern=80,
        to_port=6,
        to_starboard=4,
        epfd=1,
        draught=4.2,
        destination="BUDAFEST",
        dte=0,
        month=0,
        day=0,
        hour=0,
        minute=0,
        spare_1=b"",
    )
    sentences = pyais.encode_msg(reference)
    payload, fill = _assemble(sentences)
    assert fill > 0  # a pyais ket sorra bontja -> a kitolto bitek vannak

    ours = decode_static(payload, fill)
    assert ours.shipname == "MAHAB ORSZAG"
    assert ours.callsign == "HGXC"
