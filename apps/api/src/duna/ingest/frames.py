"""Az NMEA 0183 frame-szintű validáció (a 04 §3).

**A SZABALYOK (a 04 §3.1):**
- a mondat `$` (vagy `!`) karakterrel kezdodik;
- a mezok vesszoyel elvalasztottak;
- a `*` utan 2 hex karakter a checksum -> **az XOR** a `$`/`!` es a
  `*` közötti karaktereken;
- az `n` (sorok szama) 1-9 -> **a 0 erteken ervénytelen**;
- az `r` (sorszam) 1..n -> **az `r` nem lehet nagyobb, mint az `n`**.

**A SZAMOZOTT SOROK OSSZEFUZESE (a 04 §3.2):**
1. az `1/n` sor kezdi az üzenetet;
2. az `r/n` sorok **rendben** jonnek;
3. a `payload` reszeket **osszefuzzuk**;
4. az utolso sor `fill_bits` mezője a payload kitolto biteinek szama (0-5).

**Hiba eseten** (a `r` nem folytonos, a `payload` > 82 karakter, a
checksum hibas) -> **az üzenet ELDOBANDO** -> **a `data_quality_event`
irasa** (a `reason = 'parser_error'`).

**A `physical` flag** (a 04 §4.2): **a `bud01` vevo a FIZIKAI 6 bites
formajat hasznalja** (a `ord-48` mapping) -> **a dekoder
`physical=True` kapcsolattal hívja** -> **a frame-e szinten nem
dönt el, mert a fizikai es a standard forma a frame-ből nem
megallapithato** -> **a hivas oldalon kerdunk ra** (a `04` §4.2).
"""

from __future__ import annotations

from dataclasses import dataclass


# **a `!`/`$` es a `*` közötti XOR** (a 04 §3.1)
def compute_checksum(body: str) -> int:
    """A NMEA checksum (az XOR a `!`/`$` es a `*` között)."""
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    return checksum


@dataclass(frozen=True, slots=True)
class AisFrame:
    """Egy összefűzött AIS-frame (a 04 §3.2)."""

    payload: str
    """**A teljes payload** (a sorok reszeinek osszefuzese)."""

    fill_bits: int
    """**A kitolto bitek szama** (0-5) -> **a dekolo elott el kell
    tavolitani** (a 04 §3.3)."""

    talker: str
    """**A talker** (a `AIVDM` -> `AI`)."""

    message_type: str
    """**A message type** (a `AIVDM` -> `VDM`)."""

    source: str | None = None
    """**A radio / a forras** (az NMEA 5. mezője, a `A` hosszú)."""

    channel: str | None = None
    """**A csatorna** (a `A`/`B`)."""

    raw: str = ""
    """**Az eredeti nyers sor** (a hibakereseshez)."""


class FrameError(ValueError):
    """**A frame hibaja** (a 04 §3.2: az üzenet eldobandó + a
    `data_quality_event`)."""


def parse_sentence(sentence: str) -> AisFrame | None:
    """Egy NMEA sor elemzése.

    **`None`, ha a sor nem egy AIS-sor** (nem `!AIVDM`/`!AIVDO`) →
    **a hívó eldobja** (nem hiba, csak nem AIS).

    **`FrameError`, ha AIS-sor, de hibás** (a checksum, a sorszám, a
    mezőszám) → **a hívó `data_quality_event`-et ír**.

    **A TÖBBSOROS üzenetEK** (`n > 1`) -> **egy `AisFrame` csak az
    `1/n` sort adja** (a többi sort a `assemble_frames` fűzi
    össze).
    """
    text = sentence.strip()
    if not text:
        return None
    if not text.startswith(("!AIVDM", "!AIVDO", "$AIVDM", "$AIVDO")):
        return None

    # **a `*` utan a checksum** -> **a `*` utani 2 hex karakter**
    star = text.rfind("*")
    if star < 0:
        raise FrameError("a mondatbol hiányzik a checksum")
    body = text[1:star]
    checksum_text = text[star + 1 :].strip()
    if len(checksum_text) < 2:
        raise FrameError("a checksum nem 2 hex karakter")
    try:
        expected = int(checksum_text[:2], 16)
    except ValueError as exc:
        raise FrameError(f"a checksum nem hex: {checksum_text[:2]!r}") from exc
    if compute_checksum(body) != expected:
        raise FrameError(
            f"a checksum hibás: a számított {compute_checksum(body):02X}, a megadott {expected:02X}"
        )

    fields = _sentence_fields(text)
    # **`!AIVDM,1,1,,A,payload,0*hh`** -> **8 mező a `*` előtt**
    if len(fields) < 6:
        raise FrameError(f"a mondatban {len(fields)} mező van, legalább 6 kell")
    talker_type = fields[0]
    if len(talker_type) != 5:
        raise FrameError(f"a talker+type hibás: {talker_type!r}")
    talker, message_type = talker_type[:2], talker_type[2:]

    try:
        count = int(fields[1])
        number = int(fields[2])
    except ValueError as exc:
        raise FrameError("a sorok száma vagy sorszáma nem szám") from exc
    if count < 1 or count > 9:
        raise FrameError(f"a sorok száma érvénytelen: {count}")
    if number < 1 or number > count:
        raise FrameError(f"a sorszám ({number}) nem lehet nagyobb, mint a sorok száma ({count})")

    channel = fields[3] or None
    source = fields[4] or None
    payload = fields[5]

    # **a kitöltő bitek** -> **a 6. mező** (a `0` = nincs)
    fill_bits = 0
    if len(fields) > 6 and fields[6]:
        try:
            fill_bits = int(fields[6])
        except ValueError as exc:
            raise FrameError(f"a fill_bits nem szám: {fields[6]!r}") from exc
    if fill_bits < 0 or fill_bits > 5:
        raise FrameError(f"a fill_bits érvénytelen: {fill_bits}")

    # **a payload hossza** -> **max. 82 karakter soronként** (a 04 §3.1)
    if len(payload) > 82:
        raise FrameError(f"a payload {len(payload)} karakter (max. 82)")

    return AisFrame(
        payload=payload,
        fill_bits=fill_bits,
        talker=talker,
        message_type=message_type,
        source=source,
        channel=channel,
        raw=text,
    )


def assemble_frames(sentences: list[str]) -> tuple[AisFrame | None, list[str]]:
    """A számozott sorok összefűzése (a 04 §3.2).

    **A visszatérés:** `(az összefűzött frame vagy None, a hibás
    sorok)`.

    **A szabályok:**
    1. az `1/n` sor kezdi az üzenetet;
    2. az `r/n` sorok **rendben** jönnek (`r` növekvő);
    3. a `payload` részeket **összefűzzük**;
    4. az utolsó sor `fill_bits` mezője a kitöltő bitek száma.

    **A hibás sor** (a `r` nem folytonos, a `checksum` hibás) ->
    **a sor eldobandó** -> **a `data_quality_event`**.
    """
    parts: list[AisFrame] = []
    invalid: list[str] = []
    expected = 1
    total = 1

    for sentence in sentences:
        try:
            frame = parse_sentence(sentence)
        except FrameError:
            invalid.append(sentence)
            # **a sorhibakor a gyujtöreset kell** -> **a kovetkezo
            # `1/n` sor egy uj uzenetet kezd**
            parts.clear()
            expected = 2
            continue
        if frame is None:
            continue

        if frame_is_first(frame):
            # **uj uzenet** -> **a gyujtöreset** ->
            # **a KOVETKEZO varhato sorszam a 2** (az elso sor a `1/n`)
            parts = [frame]
            total = frame_count(sentence)
            expected = 2
            continue

        if not parts:
            # **a `2/n` sor egy `1/n` nelkul** -> **hibas**
            invalid.append(sentence)
            continue

        if frame_number(sentence) != expected:
            # **a `r` nem folytonos** -> **a gyujtöreset**
            invalid.append(sentence)
            parts.clear()
            expected = 2
            continue

        parts.append(frame)
        expected += 1

        if len(parts) == total:
            merged = AisFrame(
                payload="".join(p.payload for p in parts),
                fill_bits=parts[-1].fill_bits,
                talker=parts[0].talker,
                message_type=parts[0].message_type,
                source=parts[0].source,
                channel=parts[0].channel,
                raw="\n".join(p.raw for p in parts),
            )
            parts = []
            expected = 2
            return merged, invalid

    return None, invalid


def _sentence_fields(sentence: str) -> list[str]:
    """**A mondat mezői** (a `*` előtt, a `!`/`$` nélkül).

    **A `parse_sentence` ugyanezt használja** -> **egy helyen a
    mezőfelbontás** -> **a `frame_count`/`frame_number` nem foghat
    el másképp.**
    """
    text = sentence.strip()
    if not text:
        raise FrameError("az üres mondat")
    star = text.rfind("*")
    body = text[1:star] if star > 0 else text[1:]
    return body.split(",")


def frame_count(sentence: str) -> int:
    """A mondatban a sorok száma (az `n`)."""
    try:
        return int(_sentence_fields(sentence)[1])
    except (IndexError, ValueError) as exc:
        raise FrameError("a sorok száma nem olvasható") from exc


def frame_number(sentence: str) -> int:
    """A mondat sorszáma (az `r`)."""
    try:
        return int(_sentence_fields(sentence)[2])
    except (IndexError, ValueError) as exc:
        raise FrameError("a sorszám nem olvasható") from exc


def frame_is_first(frame: AisFrame) -> bool:
    """**Az `1/n` sor-e?** (a 04 §3.2: az `1/n` sor kezdi az
    üzenetet).

    **A `sorszámot` kell nézni** (az `r`), **nem a prefixet** ->
    **a `!AIVDM,2,1,...` (az `n=2`, `r=1`) is az első sor** ->
    **a prefix-alapú ellenőrzés a többsoros üzeneteket elrontaná.**
    """
    try:
        return frame_number(frame.raw) == 1
    except FrameError:
        return False
