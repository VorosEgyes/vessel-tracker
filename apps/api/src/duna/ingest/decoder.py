"""A 6 bites AIS karakterkódolás és az üzenetfejlécek dekódolása.

**A specifikáció:** a `04` – parser-terv §4.1 (a 6 bites
karakterkódolás), §4.2 (az üzenet fejléce), §3.3 (a `fill_bits`).

**A `duna/ingest/` réteg szabálya:** a parser **tiszta függvények** →
nincs DB, nincs hálózat → unit és property tesztelhető (a `04` §10).

**A KÖTŐDÖ FONTOS DÖNTÉS (a 2026-11-24-i mérésből):**

A `bud01` vevő (AIS-catcher v0.71) **a fizikai 6 bites értékeket
tárolja** a `nmea` oszlopban — **nem a standard AIS armor karaktereit.**
A mérés igazolja: a vevő `type` oszlopa megegyezik a `payload[0]`
karakter `ord - 48` értékével (a `B`→18, az `E`→21, a `G`→23, a `H`→24,
a `?`→15 — a standard armor ezeket 11/14/16/17/15-nek adná).

**Ezért itt KÉT kódolás van:**
- a **`decode_physical_6bit`** — a vevő formátuma (a fizikai értékek,
  a `chr(value + 48)` formában) → **ezt olvassuk a mérési adatban**;
- a **`decode_standard_6bit`** — az ITU-R M.1371 armorja (a `0-9A-Za-z@`)
  → **ez a szabványos AIS payload**.

**A bitek a karaktereken belül NEM fordítottak** (a mérés igazolja: a
`type` 3000/3000 egyezik így) — **a `04` §4.1 „a bitek fordítottak"
állítása a mérésben nem igaz.**

**A `mmsi` oszlop NEM a `nmea` payloadból jön:** a vevő NORMALIZÁLT
azonosítót tárol (a MID javított, a Class B-nél synthetic 992-es) →
**ez a `04` §5 szerinti normalizálás** → **a `nmea` payloadból a
FIZIKAI MMSI számítható, a tárolt `mmsi` nem.**
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------
# a standard AIS armor (a GPSD/pyais szerint, a 04 §4.1)
# ---------------------------------------------------------------------
# **A 6 bites érték -> a karakter:**
# - a 0–39 érték -> `chr(v + 48)` (a 0x30–0x57: a `0`–`W`);
# - a 40–63 érték -> `chr(v + 56)` (a 0x60–0x77: a `` ` ``–`w`).
#
# **Ez a `pyais` hivatalos implementációja** (`_six_bit_to_ascii`) →
# **a GPSD referencia-példát hibátlanul dekódolja** (a
# `15M67FC000G?ufbE`FepT@3n00Sa` -> az MMSI 366 053 209).
#
# **A `04` §4.1 táblázata („0–W (számok) -> 101010–111111") pontosan
# ezt írja le** → **a vevő fizikai formája és a standard armor
# AZONOS.**
def _physical_value(char: str) -> int:
    """A karakter -> a fizikai 6 bites érték (a `pyais` `_PAYLOAD_ARMOR`).

    `v = ord(c) - 48; v -= 8, ha v > 40` → **a `0`–`W` a 0–39, a
    `` ` ``–`w` a 40–63 érték.**
    """
    value = ord(char) - 48
    return value - 8 if value > 40 else value


def _standard_value_to_int(value: int) -> int:
    """A 6 bites érték -> a standard AIS karakter kódja (a GPSD szerint)."""
    return value + 48 if value < 40 else value + 56


def _standard_char_to_value(char: str) -> int:
    """A standard AIS karakter -> a 6 bites érték (a GPSD/`pyais` szerint).

    **A `pyais` `_PAYLOAD_ARMOR` képlete:**
    `v = ord(c) - 48; v -= 8, ha v > 40` → **a 0–39 érték a `0`–`W`,
    a 40–63 érték a `` ` ``–`w` karakterek.**

    **Az érvényes karaktertartomány: a 0x30–0x57 és a 0x60–0x77**
    (a `X`–`_` és a `z`–`~` ÉRVÉNYETLEN) → a `ValueError`.
    """
    code = ord(char)
    if not (48 <= code <= 87 or 96 <= code <= 119):
        raise ValueError(f"ervénytelen AIS karakter a payloadban: {char!r}")
    value = code - 48
    return value - 8 if value > 40 else value


# **A SZÖVEGMEZŐ kódolása** (a `pyais` `SIXBIT_ENCODING`):
# a karakter -> a 6 bites érték. **A szövegmező a fizikai armor
# értékeit hordozza, de a karaktere EZEKBEN az értékekben értendő**
# (a `T` a 20-as érték, nem a 28-as).
# **A FIZIKAI armor (a payload karakterei)** (a `pyais`
# `_PAYLOAD_ARMOR` / `SixBitNibleEncoder._six_bit_to_ascii`):
# a 0-39 ertek -> `chr(v+48)`, a 40-63 -> `chr(v+56)`.
PHYSICAL_VALUE_TO_CHAR: dict[int, str] = {
    _v: (chr(_v + 48) if _v < 40 else chr(_v + 56)) for _v in range(64)
}

SIX_BIT_ENCODING: dict[str, int] = {
    "@": 0,
    **{chr(ord("A") + _i): _i + 1 for _i in range(26)},  # A-Z: 1-26
    **{chr(ord("a") + _i): _i + 27 for _i in range(26)},  # a-z: 27-52
    **{
        " ": 32,
        "!": 33,
        '"': 34,
        "#": 35,
        "$": 36,
        "%": 37,
        "&": 38,
        "'": 39,
        "(": 40,
        ")": 41,
        "*": 42,
        "+": 43,
        ",": 44,
        "-": 45,
        ".": 46,
        "/": 47,
        "0": 48,
        "1": 49,
        "2": 50,
        "3": 51,
        "4": 52,
        "5": 53,
        "6": 54,
        "7": 55,
        "8": 56,
        "9": 57,
        ":": 58,
        ";": 59,
        "<": 60,
        "=": 61,
        ">": 62,
        "?": 63,
    },
}

# **A szövegérték -> a karakter** (a `SIXBIT_ENCODING` inverze)
SIX_BIT_VALUE_TO_CHAR: dict[int, str] = {v: k for k, v in SIX_BIT_ENCODING.items()}

# **A karakter -> érték és az érték -> karakter** (a `pyais`
# `_PAYLOAD_ARMOR` és `_SIXBIT_CHAR` szerint)
STANDARD_ARMOR: dict[str, int] = {chr(_standard_value_to_int(_v)): _v for _v in range(64)}

# a SZÖVEGmező karaktere: a 0–31 érték -> `chr(v+64)`, a 32–63 ->
# `chr(v)` (a `pyais` `_SIXBIT_CHAR`)
STANDARD_VALUE_TO_CHAR: dict[int, str] = {
    _v: (chr(_v + 64) if _v < 32 else chr(_v)) for _v in range(64)
}


def decode_standard_6bit(payload: str) -> list[int]:
    """A standard AIS armor -> a 6 bites értékek.

    Args:
        payload: a payload (a `*` és a checksum nélkül).

    Returns:
        A 6 bites értékek listája (0–63).

    Raises:
        ValueError: ha a payloadban érvénytelen karakter van.
    """
    return [_standard_char_to_value(ch) for ch in payload]


def encode_standard_6bit(values: list[int]) -> str:
    """A 6 bites értékek -> a standard AIS armor (a `decode_standard_6bit`
    fordítottja).
    """
    out: list[str] = []
    for value in values:
        if not 0 <= value <= 63:
            raise ValueError(f"ervénytelen 6 bites érték: {value}")
        out.append(PHYSICAL_VALUE_TO_CHAR.get(value, "\0"))
    return "".join(out)


def decode_physical_6bit(payload: str) -> list[int]:
    """A vevő fizikai 6 bites értékei -> a 6 bites értékek.

    **A `bud01` vevő (AIS-catcher v0.71) a fizikai értékeket tárolja**
    → **a mérés igazolja, hogy ez a STANDARD AIS armor** (a GPSD
    szerint: a 0–39 érték -> `chr(v+48)`, a 40–63 -> `chr(v+56)`) →
    **a `type` oszlop 8000/8000 egyezik így** (a mérési adat 8000
    üzenetén).

    **DE:** a vevő a `lat`/`lon`/`mmsi` mezőket **normalizálja**
    (a `04` §5) → **a `nmea` oszlopból csak a `type` olvasható ki
    megbízhatóan** → **a mérési adatot nem szabad nyers payloadként
    kezelni** (a `04` §11 Q8).

    **A `decode_standard_6bit` a `duna` éles parseré** → **a kettő
    ugyanaz a kódolás** → **ez a függvény a mérési adat kényelmes
    olvasására marad** (a `physical=True` jelzi a szándékot).
    """
    return decode_standard_6bit(payload)


@dataclass(frozen=True, slots=True)
class PositionReport:
    """A pozícióüzenet (a Msg 1/2/3) mezői (a `04` §4.3).

    **A standard AIS bit-sorrend (a GPSD/`pyais` szerint):**
    - 0–5: az üzenettípus;
    - 6–7: az ismétlődés;
    - 8–37: az MMSI;
    - 38–41: a navigációs állapot (4 bit);
    - 42–49: a manöverjelzés (8 bit, a ROT);
    - 50–59: a SOG (10 bit, 1/10 csomó, m/s-ra átalakítva);
    - 60: a pozíció pontossága (1 bit);
    - 61–88: a LON (28 bit, 1/10000 perc);
    - 89–115: a LAT (27 bit, 1/10000 perc);
    - 116–127: a COG (12 bit, 1/10 fok);
    - 128–136: a heading (9 bit, egész fok);
    - 137–142: az időbélyeg (6 bit);
    - 143–144: a manöver (2 bit);
    - 145–147: a tartalék (3 bit);
    - 148: a RAIM (1 bit);
    - 149–167: a rádióállapot (19 bit).

    **A `04` §4.3 táblázata a 18 bites LAT/LON-t és a 4 bites rádiót
    írja** → **a standard AIS-ben 27/28 bites LAT/LON és 19 bites
    rádió** → **a terv javítva lett** (a 2026-11-24-i implementáció).
    """

    message_type: int
    repeat: int
    mmsi: int
    nav_status: int
    lat: float | None
    lon: float | None
    sog_mps: float | None
    cog_deg: float | None
    # A true heading mező egész fokban van.
    heading_deg: float | None
    timestamp: int | None
    maneuver: int | None
    raim: bool | None
    radio: int | None

    @property
    def is_position(self) -> bool:
        """A pozíciót adó üzenettípusok (a `04` §4.3)."""
        return self.message_type in (1, 2, 3)


def _signed(value: int, bits: int) -> int:
    """Az előjeles mező (a `04` §4.3: az előjel a 17. bit).

    **A standard AIS-ben a LAT/LON 27 bites, két's komplementes**
    → a 26. bit az előjel.
    """
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        return value - (1 << bits)
    return value


def decode_position(payload: str, fill_bits: int = 0, *, physical: bool = False) -> PositionReport:
    """A pozícióüzenet dekódolása (a Msg 1/2/3).

    Args:
        payload: a NMEA payload.
        fill_bits: a kitöltő bitek száma (0–5).
        physical: a vevő oszlopát jelöli (a `bud01` mérési adata).

    Returns:
        A `PositionReport`.

    Raises:
        ValueError: ha a payload túl rövid (a pozícióhoz 148 bit kell).
    """
    bits = payload_to_bits(payload, fill_bits, physical=physical)
    if len(bits) < 168:
        raise ValueError(f"a payload túl rövid a pozícióhoz: {len(bits)} bit (168 kell)")

    # **A LAT/LON a `pyais` szerint** (a hivatalos referencia): a nyers
    # érték / 600000 (a `−90`/`−180` eltolás NEM kell) → **a GPSD
    # referencia-példán a `lat=37.802118`, a `lon=-122.341618`.**
    #
    # A "not available" sentinel: a LAT 0x3412140 (a 91°), a LON
    # 0x6791AC0 (a 181°) → **a `pyais` ezeket 0.0-ra cseréli**.
    lon_raw = _signed(bits_to_int(bits, 61, 28), 28)
    lat_raw = _signed(bits_to_int(bits, 89, 27), 27)
    # a `pyais` 6 tizedesre kerekít -> **a `round(..., 6)` a
    # bit-azonosságot is megőrzi** (a `pyais` `to_lat_lon`ja)
    lat = None if lat_raw == 0x3412140 else round(lat_raw / 600000.0, 6)
    lon = None if lon_raw == 0x6791AC0 else round(lon_raw / 600000.0, 6)

    sog_raw = bits_to_int(bits, 50, 10)
    cog_raw = bits_to_int(bits, 116, 12)
    head_raw = bits_to_int(bits, 128, 9)

    return PositionReport(
        message_type=bits_to_int(bits, 0, 6),
        repeat=bits_to_int(bits, 6, 2),
        mmsi=bits_to_int(bits, 8, 30),
        nav_status=bits_to_int(bits, 38, 4),
        lat=lat,
        lon=lon,
        sog_mps=None if sog_raw == 1023 else sog_raw / 10.0 * (1852 / 3600),
        cog_deg=None if cog_raw == 3600 else cog_raw / 10.0,
        heading_deg=None if head_raw == 511 else float(head_raw),
        timestamp=bits_to_int(bits, 137, 6),
        maneuver=bits_to_int(bits, 143, 2),
        raim=bool(bits_to_int(bits, 148, 1)),
        radio=bits_to_int(bits, 149, 19),
    )


@dataclass(frozen=True, slots=True)
class StaticReport:
    """A statikus üzenet (a Msg 5) mezői (a `04` §4.4).

    **A standard AIS bit-sorrend (a GPSD/`pyais` szerint):**
    - 0–5: az üzenettípus;
    - 6–7: az ismétlődés;
    - 8–37: az MMSI;
    - 38–39: az AIS-verzió;
    - 40–69: az IMO (30 bit);
    - **70–111: a hívójel (42 bit = 7 karakter)**;
    - **112–231: a hajónév (120 bit = 20 karakter)**;
    - 232–239: a hajótípus (8 bit);
    - 240–248: a hajó orrától a GNSS-antenna (9 bit);
    - 249–257: a hajó fartól a GNSS-antenna (9 bit);
    - 258–263: a bal oldali szélesség (6 bit);
    - 264–269: a jobb oldali szélesség (6 bit);
    - 270–273: az EPFD (4 bit);
    - 274–277: a hónap (4 bit);
    - 278–282: a nap (5 bit);
    - 283–287: az óra (5 bit);
    - 288–293: a perc (6 bit);
    - 294–301: a merülés (8 bit, 1/10 m);
    - 302–421: a célállomás (120 bit = 20 karakter);
    - 422: a DTE (1 bit);
    - 423: a tartalék (1 bit).

    **A `04` §4.4 táblázata más sorrendet és méreteket ír** (a 18
    bites LAT/LON-hoz hasonlóan) → **a terv javítva lett** (a
    2026-11-24-i implementáció, a `pyais` referenciája alapján).
    """

    message_type: int
    repeat: int
    mmsi: int
    ais_version: int
    imo: int | None
    callsign: str
    shipname: str
    ship_type: int
    to_bow: int
    to_stern: int
    to_port: int
    to_starboard: int
    epfd: int
    draught_m: float | None
    destination: str
    dte: bool

    @property
    def length_m(self) -> float | None:
        """A hajó hossza (a `to_bow` + a `to_stern`, méterben).

        **A `02` §5.1 szerint a GNSS-antenna az orrban van** → **a
        hossz = a `to_bow` + a `to_stern`.**
        """
        total = self.to_bow + self.to_stern
        return None if total == 0 else float(total)

    @property
    def beam_m(self) -> float | None:
        """A hajó szélessége (a `to_port` + a `to_starboard`, méterben)."""
        total = self.to_port + self.to_starboard
        return None if total == 0 else float(total)


def decode_text_field(payload: str, start_bit: int, length_bits: int) -> str:
    """A 6 bites szövegmező dekódolása a KARAKTEREKBBŐL.

    **Miért nem a bitekből:** egy szövegmező kezdőbitje a
    karakterhatáron BELÜL van (a `shipname` a 112. biten kezdődik =
    a 18,67. karakterben) → **a karakterenkénti bitekből nem lehet
    6-os csoportokat olvasni.**

    **A szabályok (a GPSD/`pyais` szerint):**
    1. **a karakter fizikai 6 bites értéke** (a `pyais`
       `_PAYLOAD_ARMOR`: `v = ord(c) - 48; v -= 8, ha v > 40`) → **a
       bitek ebből MSB-first jönnek** (a fizikai sorrendben);
    2. **a 6 bites érték -> a szöveg karaktere:** a 0–31 érték ->
       `chr(v+64)`, a 32–63 érték -> `chr(v)` (a `pyais`
       `_SIXBIT_CHAR`);
    3. **az `@` (64) a kitöltő** -> a szöveg vége.

    Args:
        payload: a NMEA payload.
        start_bit: a mező kezdőbitje (a payloadban).
        length_bits: a mező hossza (bit).

    Returns:
        A kitöltő nélküli, trimmelt szöveg.
    """
    chars: list[str] = []
    for i in range(length_bits // 6):
        # a 6 bite a karakter-beli bitekből, a mező kezdőpozíciójától
        value = 0
        for j in range(6):
            abs_bit = start_bit + i * 6 + j
            ci, bo = divmod(abs_bit, 6)
            if ci >= len(payload):
                break
            # **a karakter fizikai 6 bites értéke** (a `pyais`
            # `_PAYLOAD_ARMOR`: `v = ord(c) - 48; v -= 8, ha v > 40`)
            char_value = _physical_value(payload[ci])
            value = (value << 1) | ((char_value >> (5 - bo)) & 1)
        # **a 6 bites érték -> a szöveg karaktere** (a `pyais`
        # `decode_bytes_as_ascii6`: `n < 0x20 -> n += 0x40`) →
        # **az `@` (64) a kitöltő** -> a szöveg vége
        if value < 0x20:
            value += 0x40
        if value == 64:
            break
        chars.append(chr(value))
    return "".join(chars).strip()


def decode_static(payload: str, fill_bits: int = 0, *, physical: bool = False) -> StaticReport:
    """A statikus üzenet dekódolása (a Msg 5).

    Args:
        payload: a NMEA payload.
        fill_bits: a kitöltő bitek száma (0–5).
        physical: a vevő oszlopát jelöli (a `bud01` mérési adata).

    Returns:
        A `StaticReport`.

    Raises:
        ValueError: ha a payload túl rövid (a statikushoz 424 bit kell).
    """
    bits = payload_to_bits(payload, fill_bits, physical=physical)
    if len(bits) < 424:
        raise ValueError(f"a payload túl rövid a statikushoz: {len(bits)} bit (424 kell)")
    # a szovegmezok a KARAKTER-beli bitekbol olvasandoak -> a payload
    # (a fill_bits levagasa utan) kell, nem a bitek
    text_payload = payload[: len(payload) - (fill_bits // 6)] if fill_bits else payload

    imo_raw = bits_to_int(bits, 40, 30)
    draught_raw = bits_to_int(bits, 294, 8)

    return StaticReport(
        message_type=bits_to_int(bits, 0, 6),
        repeat=bits_to_int(bits, 6, 2),
        mmsi=bits_to_int(bits, 8, 30),
        ais_version=bits_to_int(bits, 38, 2),
        imo=None if imo_raw == 0 else imo_raw,
        callsign=decode_text_field(text_payload, 70, 42),
        shipname=decode_text_field(text_payload, 112, 120),
        ship_type=bits_to_int(bits, 232, 8),
        to_bow=bits_to_int(bits, 240, 9),
        to_stern=bits_to_int(bits, 249, 9),
        to_port=bits_to_int(bits, 258, 6),
        to_starboard=bits_to_int(bits, 264, 6),
        epfd=bits_to_int(bits, 270, 4),
        draught_m=None if draught_raw == 0 else draught_raw / 10.0,
        destination=decode_text_field(text_payload, 302, 120),
        dte=bool(bits_to_int(bits, 422, 1)),
    )


@dataclass(frozen=True, slots=True)
class AidToNavigationReport:
    """A 21-es üzenet (a `pyais` szerint az AtoN — a navigációs segéd).

    **A `bud01` vevő a belvízi FI 10-at is a 21-es mezőkkel dekódolja**
    (a mérésben a 93 645 `type=21` üzenet `shipname`-je a hívójel,
    pl. a `1658.8_G`) → **a 21-es üzenet a gyakorlatban a belvízi
    statikus (a `04` §4.5) vagy az AtoN** → **a hívójel a `name`
    mezőben van** (a `pyais` szerint a 43–162. bit).

    **A bit-sorrend (a GPSD/`pyais` szerint):**
    - 0–5: az üzenettípus;
    - 6–7: az ismétlődés;
    - 8–37: az MMSI;
    - 38–42: a navigációs segéd típusa (5 bit);
    - 43–162: a név (120 bit = 20 karakter);
    - 163: a pozíció pontossága;
    - 164–191: a LON (28 bit);
    - 192–218: a LAT (27 bit);
    - 219–227: a hajó orrától a GNSS-antenna (9 bit);
    - 228–236: a hajó fartól (9 bit);
    - 237–242: a bal oldali szélesség (6 bit);
    - 243–248: a jobb oldali szélesség (6 bit);
    - 249–252: az EPFD (4 bit);
    - 253–258: az időbélyeg (6 bit);
    - 259: a pozíciótól való eltérés;
    - 260–267: a tartalék (8 bit);
    - 268: a RAIM;
    - 269: a virtuális AtoN;
    - 270: a kiosztott;
    - 271: a tartalék.
    """

    message_type: int
    repeat: int
    mmsi: int
    aid_type: int
    name: str
    accuracy: bool
    lat: float | None
    lon: float | None
    to_bow: int
    to_stern: int
    to_port: int
    to_starboard: int
    epfd: int
    timestamp: int
    off_position: bool
    raim: bool


def decode_aid_to_navigation(
    payload: str, fill_bits: int = 0, *, physical: bool = False
) -> AidToNavigationReport:
    """A 21-es üzenet dekódolása (a `pyais` szerint).

    **A `bud01` vevőn a 21-es üzenet a belvízi statikus (a `04`
    §4.5) vagy az AtoN** → **a hívójel a `name` mezőben van**
    (a mérésben: a `1658.8_G`).

    Args:
        payload: a NMEA payload.
        fill_bits: a kitöltő bitek száma (0–5).
        physical: a vevő oszlopát jelöli (a `bud01` mérési adata).

    Returns:
        Az `AidToNavigationReport`.

    Raises:
        ValueError: ha a payload túl rövid (a 21-eshez 272 bit kell).
    """
    bits = payload_to_bits(payload, fill_bits, physical=physical)
    if len(bits) < 272:
        raise ValueError(f"a payload túl rövid a 21-es üzenethez: {len(bits)} bit (272 kell)")
    text_payload = payload[: len(payload) - (fill_bits // 6)] if fill_bits else payload

    lon_raw = _signed(bits_to_int(bits, 164, 28), 28)
    lat_raw = _signed(bits_to_int(bits, 192, 27), 27)

    return AidToNavigationReport(
        message_type=bits_to_int(bits, 0, 6),
        repeat=bits_to_int(bits, 6, 2),
        mmsi=bits_to_int(bits, 8, 30),
        aid_type=bits_to_int(bits, 38, 5),
        name=decode_text_field(text_payload, 43, 120),
        accuracy=bool(bits_to_int(bits, 163, 1)),
        lat=None if lat_raw == 0x3412140 else round(lat_raw / 600000.0, 6),
        lon=None if lon_raw == 0x6791AC0 else round(lon_raw / 600000.0, 6),
        to_bow=bits_to_int(bits, 219, 9),
        to_stern=bits_to_int(bits, 228, 9),
        to_port=bits_to_int(bits, 237, 6),
        to_starboard=bits_to_int(bits, 243, 6),
        epfd=bits_to_int(bits, 249, 4),
        timestamp=bits_to_int(bits, 253, 6),
        off_position=bool(bits_to_int(bits, 259, 1)),
        raim=bool(bits_to_int(bits, 268, 1)),
    )


def payload_to_bits(payload: str, fill_bits: int = 0, *, physical: bool = False) -> list[int]:
    """A payload -> a bit-listája (MSB first).

        Args:
            payload: a NMEA payload.
            fill_bits: a kitöltő bitek száma (0–5, a `04` §3.3).
            physical: a vevő fizikai értékeit használjuk-e (a `bud01`
                mérési adata) vagy a standard AIS armort — **a kettő azonos
                kódolás** (a GPSD/pyais szerint), **a flag csak a szándék
                kifejezésére marad**.

        **A `fill_bits`:** a kitöltő bitek a payload **utolsó** bitjei →
    **a dekódolás előtt el kell távolítani őket.**
    """
    if not 0 <= fill_bits <= 5:
        raise ValueError("fill_bits must be between 0 and 5")
    values = decode_physical_6bit(payload) if physical else decode_standard_6bit(payload)
    bits: list[int] = []
    for value in values:
        for shift in range(5, -1, -1):
            bits.append((value >> shift) & 1)
    if fill_bits:
        bits = bits[: len(bits) - fill_bits]
    return bits


def bits_to_int(bits: list[int], start: int, length: int) -> int:
    """A bit-listából egy `length` bites szám (MSB first)."""
    value = 0
    for offset in range(length):
        value = (value << 1) | bits[start + offset]
    return value


@dataclass(frozen=True, slots=True)
class MessageHeader:
    """Az AIS üzenet fejléce (a `04` §4.2).

    **Az első 168 bit (22 karakter):**
    - 0–5: az üzenettípus;
    - 6–7: az ismétlődés (a számozott üzenetek sorszáma);
    - 8–37: az MMSI (30 bit).
    """

    message_type: int
    repeat: int
    mmsi: int

    @property
    def is_position(self) -> bool:
        """A pozíciót adó üzenettípusok (a `04` §4.3)."""
        return self.message_type in (1, 2, 3)

    @property
    def is_static(self) -> bool:
        """A statikus üzenettípusok (a `04` §4.4: az 5, a 21)."""
        return self.message_type in (5, 21)


def decode_header(payload: str, fill_bits: int = 0, *, physical: bool = False) -> MessageHeader:
    """Az AIS üzenet fejlécének dekódolása.

    Args:
        payload: a NMEA payload.
        fill_bits: a kitöltő bitek száma (0–5).
        physical: a vevő fizikai értékeit használjuk-e (a `bud01`
            mérési adata) vagy a standard AIS armort.

    Returns:
        A `MessageHeader` (az üzenettípus, az ismétlődés, az MMSI).

    Raises:
        ValueError: ha a payload túl rövid (a fejlécnek 38 bit kell).
    """
    bits = payload_to_bits(payload, fill_bits, physical=physical)
    if len(bits) < 38:
        raise ValueError(f"a payload túl rövid a fejléchez: {len(bits)} bit (38 kell)")
    return MessageHeader(
        message_type=bits_to_int(bits, 0, 6),
        repeat=bits_to_int(bits, 6, 2),
        mmsi=bits_to_int(bits, 8, 30),
    )


def decode_message(payload: str, fill_bits: int = 0, *, physical: bool = False) -> MessageHeader:
    """Az AIS üzenet dekódolása (egyelőre csak a fejléc).

    **A teljes dekódolás (a dinamikus és a statikus mezők) a `04`
    §4.3–§4.7 szerint** — az a következő lépés.
    """
    return decode_header(payload, fill_bits, physical=physical)
