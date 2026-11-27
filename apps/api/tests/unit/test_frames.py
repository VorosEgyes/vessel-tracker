"""Az NMEA frame-validáció unit tesztje (a 04 §3).

**A tesztsorok a `bud01` vevő VALÓS mérési adatai** (a
`ais-20261127-0905.db` -> `ais_message.nmea`) -> **a fizikai 6 bites
forma** (a `04` §4.2) -> **a frame-szinten ez nem latszik**.

**A SZABALYOK (a 04 §3.1):** a `$`/`!` kezdet, a vesszok, az XOR
checksum, az `n` 1-9, az `r` 1..n.
"""

from duna.ingest.frames import (
    FrameError,
    assemble_frames,
    compute_checksum,
    parse_sentence,
)

# **a valós meresbol (a bud01 vevo)**
VALID_1 = "!AIVDM,1,1,,A,13Wj:chP00QG<RdK;CG>4?wT2<1?,0*06"
VALID_2 = "!AIVDM,1,1,,A,23aI8fhP001G=8PK<?Pf4?wN0D2u,0*35"
VALID_3 = "!AIVDM,1,1,,B,33Wkn;PP00QGBQTK=K;jKgwN22rS,0*45"


def _with_checksum(body: str) -> str:
    """**A NMEA mondat a helyes checksum-mel** (a `*` után)."""
    return f"!{body}*{compute_checksum(body):02X}"


# **a tobbsoros (a 2/2) uzenet a 5-ös tipus peldaja**
MULTI = "\n".join(
    (
        _with_checksum("AIVDM,2,1,0,A,53Wktk400000PMH@001HU<DM84@000000000000t0hQ16vim02hUA0D1,0"),
        _with_checksum("AIVDM,2,2,0,A,Dm000000,0"),
    )
)
# **az ATON tipus (a 0)**
ATON = "!AIVDM,1,1,,B,,0*25"
# **a 21-es tipus (a Class B)**
CLASS_B = "!AIVDM,1,1,,A,ENjMWo@HsJtGL?SP00000000000@ccok=WUg`00001oRP0,4*64"


def test_a_valid_mondat_feldolgozodik():
    """**A valid NMEA sor** -> **a frame adatai."""
    frame = parse_sentence(VALID_2)
    assert frame is not None
    assert frame.payload == "23aI8fhP001G=8PK<?Pf4?wN0D2u"
    assert frame.fill_bits == 0
    assert frame.talker == "AI"
    assert frame.message_type == "VDM"
    assert frame.source == "A"
    assert frame.channel is None


def test_a_rossz_checksum_eldobandó():
    """**A hibás checksum** -> **`FrameError`** (a 04 §3.2: az
    üzenet eldobandó + a `data_quality_event`)."""
    broken = VALID_2.replace("*35", "*36")
    try:
        parse_sentence(broken)
    except FrameError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("a hibás checksumot el kellett volna dobni")


def test_a_checksum_osszeadás():
    """**Az XOR** a `$`/`!` es a `*` között (a 04 §3.1)."""
    assert compute_checksum("AIVDM,1,1,,A,23aI8fhP001G=8PK<?Pf4?wN0D2u,0") == 0x35


def test_a_nem_ais_mondat_figyelmen_kimarul():
    """**A nem AIS-sor** (pl. a GPGGA) -> **`None`** (nem hiba)."""
    assert (
        parse_sentence("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47") is None
    )
    assert parse_sentence("") is None


def test_a_hibas_sorszam_eldobandó():
    """**Az `r` nem lehet nagyobb, mint az `n`** (a 04 §3.1)."""
    try:
        parse_sentence(_with_checksum("AIVDM,1,2,,A,13Wj:chP00QG<RdK,0"))
    except FrameError as exc:
        assert "sorszám" in str(exc)
    else:
        raise AssertionError("a hibás sorszámot el kellett volna dobni")


def test_a_hibas_fill_bits_eldobando():
    """**A `fill_bits` 0-5** (a 04 §3.1) -> **a 6 érvénytelen**."""
    sentence = "!AIVDM,1,1,,A,13Wj:chP00QG<RdK,6*00"
    # **a checksumot a szabaly szerint kiszamitjuk**
    body = "AIVDM,1,1,,A,13Wj:chP00QG<RdK,6"
    sentence = f"!{body}*{compute_checksum(body):02X}"
    try:
        parse_sentence(sentence)
    except FrameError as exc:
        assert "fill_bits" in str(exc)
    else:
        raise AssertionError("a hibás fill_bits-t el kellett volna dobni")


def test_a_tobb_soros_uzenet_osszefuzodik():
    """**A számozott sorok összefűzése** (a 04 §3.2) -> **a teljes
    payload** -> **a `fill_bits` az UTOLSÓ sorból**."""
    frame, invalid = assemble_frames(MULTI.split("\n"))
    assert frame is not None
    assert invalid == []
    assert frame.payload == "53Wktk400000PMH@001HU<DM84@000000000000t0hQ16vim02hUA0D1Dm000000"
    assert frame.fill_bits == 0
    assert frame.talker == "AI"


def test_a_hibas_sor_a_gyujtoreset_kiugrik():
    """**A hibás sor a sorozatban** -> **a `data_quality_event`**
    (a `invalid` listában) -> **a többi sor feldolgozható**."""
    # **a hibás checksum** (a `*41` helyett a helyes kellene)
    broken = _with_checksum("AIVDM,2,2,0,A,Dm000000,0").replace(
        f"*{compute_checksum('AIVDM,2,2,0,A,Dm000000,0'):02X}", "*41"
    )
    _frame, invalid = assemble_frames([MULTI.split("\n")[0], broken])
    assert invalid == [broken]


def test_a_aton_tipus_ures_payload():
    """**Az ATON (a 0-s tipus)** üres payload-dal jön -> **a frame
    megvan** (a decoder dönti el, hogy nem hajó-e)."""
    frame = parse_sentence(ATON)
    assert frame is not None
    assert frame.payload == ""


def test_a_class_b_fill_bits():
    """**A 21-es tipus (a Class B)** -> **a `fill_bits` 4** -> **a
    dekódolás előtt 4 bitet le kell venni** (a 04 §3.3)."""
    frame = parse_sentence(CLASS_B)
    assert frame is not None
    assert frame.fill_bits == 4


def test_a_tul_hosszu_payload_eldobandó():
    """**A payload max. 82 karakter** (a 04 §3.1) -> **a hosszabb
    eldobandó**."""
    payload = "A" * 90
    body = f"AIVDM,1,1,,A,{payload},0"
    sentence = f"!{body}*{compute_checksum(body):02X}"
    try:
        parse_sentence(sentence)
    except FrameError as exc:
        assert "82" in str(exc)
    else:
        raise AssertionError("a túl hosszú payloadot el kellett volna dobni")
