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
# a standard AIS armor (az ITU-R M.1371, a 04 §4.1)
# ---------------------------------------------------------------------
STANDARD_ARMOR: dict[str, int] = {}
for _i in range(10):
    STANDARD_ARMOR[str(_i)] = _i
for _i in range(26):
    STANDARD_ARMOR[chr(ord("A") + _i)] = 10 + _i
for _i in range(26):
    STANDARD_ARMOR[chr(ord("a") + _i)] = 36 + _i
STANDARD_ARMOR["@"] = 62

STANDARD_VALUE_TO_CHAR: dict[int, str] = {v: k for k, v in STANDARD_ARMOR.items()}
STANDARD_VALUE_TO_CHAR[63] = "\0"


def decode_standard_6bit(payload: str) -> list[int]:
    """A standard AIS armor -> a 6 bites értékek.

    Args:
        payload: a payload (a `*` és a checksum nélkül).

    Returns:
        A 6 bites értékek listája (0–63).

    Raises:
        ValueError: ha a payloadban érvénytelen karakter van.
    """
    out: list[int] = []
    for ch in payload:
        try:
            out.append(STANDARD_ARMOR[ch])
        except KeyError:
            raise ValueError(f"ervénytelen AIS karakter a payloadban: {ch!r}") from None
    return out


def encode_standard_6bit(values: list[int]) -> str:
    """A 6 bites értékek -> a standard AIS armor (a `decode_standard_6bit`
    fordítottja).
    """
    out: list[str] = []
    for value in values:
        if not 0 <= value <= 63:
            raise ValueError(f"ervénytelen 6 bites érték: {value}")
        out.append(STANDARD_VALUE_TO_CHAR.get(value, "\0"))
    return "".join(out)


def decode_physical_6bit(payload: str) -> list[int]:
    """A vevő fizikai 6 bites értékei -> a 6 bites értékek.

    **A `bud01` vevő (AIS-catcher v0.71) a fizikai értékeket tárolja**
    (a mérés igazolja: a `type` oszlop megegyezik a `payload[0]`
    karakter `ord - 48` értékével — a `B`→18, az `E`→21, a `G`→23,
    a `H`→24) → **a dekódolás a `value = ord(ch) - 48`** (a 6 bites
    maszkolással).

    **A visszafejtés NEM egyértelmű** (a vevő egy inverz táblázattal
    alakít karakterré, nem a `chr(value + 48)`-val) → **ez a forma
    decode-only** → **a `duna` éles parseré a standard AIS-t
    dekódolja** (a `decode_standard_6bit`).
    """
    return [(ord(ch) - 48) & 0x3F for ch in payload]


def payload_to_bits(payload: str, fill_bits: int = 0, *, physical: bool = False) -> list[int]:
    """A payload -> a bit-listája (MSB first).

        Args:
            payload: a NMEA payload.
            fill_bits: a kitöltő bitek száma (0–5, a `04` §3.3).
            physical: a vevő fizikai értékeit használjuk-e (a `bud01`
                mérési adata) vagy a standard AIS armort.

        **A `fill_bits`:** a kitöltő bitek a payload **utolsó** bitjei →
    **a dekódolás előtt el kell távolítani őket.**
    """
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
