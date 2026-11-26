"""A slug generálása (a `02` §8.1a: a slugot NEM a DB generálja).

**A DB a `NOT NULL` + a `UNIQUE` constraintet enforces** -> **ez a
garancia, hogy a mély link (a F-CAT-07) mindig egyértelmű.**

**A `slug` a hajónévből készül:**
- **a kisbetűs, ékezetmentes alak** (a `duna.domain.text`
  `normalize_search_text` -> **a `sort_name`-ével egyezik**);
- **a nem betű/nem szám karakterek kötőjellel** (a szóköz is);

**A `mmsi`/`eni` alapú slug** (a hajótípusnál nincs név) -> **a
`mmsi` a stabilabb kulcs** (a hajót átnevezik, a MMSI nem változik).
"""

from __future__ import annotations

import re

from duna.domain.text import normalize_search_text

# **a nem betu/nem szam -> kotojel** (a szokoz is)
_SEPARATOR = re.compile(r"[^a-z0-9]+")


def generate_slug(name: str | None, mmsi: int | None = None) -> str:
    """A hajó slug-je (a `02` §8.1a).

    **A sorrend:**
    1. **a név** (a `normalize_search_text` -> **a kisbetűs,
       ékezetmentes alak**) -> **a nem betű/nem szám kötőjelre**;
    2. **ha nincs név** (vagy üres) -> **az `mmsi`**;
    3. **a normalizált alap mindig alfanumerikus kezdetű** (a
       `normalize_search_text` kiszűri a nem betű/nem szám
       karaktereket) -> **nincs további prefixelés.**

    **Az üres eredmény** (név és MMSI nélkül) -> **`RuntimeError`** ->
    **a hívó felelőssége, hogy ne hívja meg ilyen adattal.**
    """
    base = ""
    if name:
        base = _SEPARATOR.sub("-", normalize_search_text(name)).strip("-")

    if not base:
        if mmsi is None:
            raise ValueError(
                "a slug generalasahoz kell a hajonev vagy az MMSI (egyik sem allt rendelkezésre)"
            )
        base = str(mmsi)

    return base
