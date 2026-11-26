"""A szövegnormalizálás (a F-SRCH-03: ékezet- és kis-nagybetű-független keresés).

**A probléma:** a PostgreSQL `unaccent` extensionje **nem érhető el
mindenhol** → **a fejlesztői `pgserver`ben nincs** → **a keresési
kifejezést az alkalmazás oldalán kell normalizálni.**

**A `sort_name` a triggerben `lower(unaccent(name))`** (a
`sync_vessel_sort_name`, a `02` §8.1a) → **a triggerben az `unaccent`
NEM kell IMMUTABLE-nak lennie** (a `02` v1.10 javítása) → **a
`sort_name` a DB-ben már ékezetmentes.**

**A két oldalnak egyeznie kell:**
- a DB: `lower(unaccent(name))` → **a `sort_name`**;
- az alkalmazás: `normalize_search_text(q)` → **ugyanez a forma.**

**A magyar ékezetek kézi mappingje** → **a `unicodedata` NFKD
normalizálás önmagában nem bontja az `ő`-t és az `ű`-t** (a magyar
`ő`/`ű` nem a `ő`/`ű` + kombinációs jel, hanem **külön Unicode
karakter** → **a `unicodedata.decomposition()` üres) → **ezért kell a
kézi tábla.

**A `sort_name` a magyar (`hu`) nyelvre van** (a trigger
`IF NEW.lang = 'hu'`) → **a normálítás a magyarra koncentrál.**
"""

from __future__ import annotations

# **A magyar ékezetek -> a latin alapbetű** (a `02` §8.1a
# `lower(unaccent(name))` szabványos alakja) → **a `unaccent`
# extensionének a magyar mappingje.**
#
# **A `NFKD` önmagában nem elég:** az `ő`/`ű`/`ő`/`ű` nem
# bomlik (külön Unicode karakter), és a `ő`/`ű` helyett a
# hosszú `o`/`u` kell → **a `double acute` (a `ő`) a `ő`-re** →
# **a kézi táblában a hosszú ő és a dupla akcentus is `o`/`u`**.
_ACCENT_MAP = str.maketrans(
    {
        "á": "a",
        "à": "a",
        "â": "a",
        "ä": "a",
        "ã": "a",
        "å": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "ô": "o",
        "ö": "o",
        "õ": "o",
        "ő": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ű": "u",
        "ý": "y",
        "ÿ": "y",
        "ç": "c",
        "ć": "c",
        "č": "c",
        "š": "s",
        "ś": "s",
        "ž": "z",
        "ź": "z",
        "ż": "z",
        "ł": "l",
        "đ": "d",
        "ð": "d",
        "þ": "th",
        "ß": "ss",
        "æ": "ae",
        "œ": "oe",
        "ø": "o",
        "ñ": "n",
    }
)


def normalize_search_text(value: str) -> str:
    """A keresési szöveg normalizálása (a `sort_name` alakja).

    **A `lower(unaccent(...))` szabványos alakja** → **a DB
    `sort_name`-ével egyezik** → **a trigram-index használható.**

    **A lépések:**
    1. a `str.casefold()` (a `lower` erősebb változata, a `ß` → `ss`);
    2. a kézi magyar ékezet-mapping;
    3. a nem betű/nem szám karakterek **szóközre** cserélése
       (a normalizálás után a `%` és a `_` nem kereshető).
    """
    folded = value.casefold()
    # **a `casefold` után is maradhat ékezet** (a magyar `ő`/`ű` a
    # `casefold`-ban is megvan) -> **a mapping utan** a `unicodedata`
    # a maradékot is kezeli (a `ø`->`o` a mappingben van)
    unaccented = folded.translate(_ACCENT_MAP)
    # **a maradék kombinacios jelek** (a `NFKD` a `ő`-t nem bontja, de
    # a más nyelvekét igen) -> **a `unicodedata` a `combining()`-gel
    # szűri ki** -> **a tisztán kis-nagybetu-kezeletlen szöveg.**
    import unicodedata

    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", unaccented) if not unicodedata.combining(ch)
    )
    # **a nem betu/nem szam -> szokoz** (a keresés a szokozre is
    # illeszkodik)
    return "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in stripped).strip()


def is_identifier_like(value: str) -> bool:
    """**A `q` azonosító-szerű?** (a F-SRCH-02: a pontos azonosító-egyezés)

    **Csak számok** (az ENI, az MMSI, az IMO) → **a hívójell
    (`HGXC`) nem az** → **a hívójell a név-egyezésre kerül.**
    """
    return bool(value) and value.isdigit()
