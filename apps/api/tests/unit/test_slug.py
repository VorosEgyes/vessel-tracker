"""A slug-generálás unit tesztje (a `02` §8.1a).

**A slugot az ALKALMAZÁS generálja** -> **a DB csak a `NOT NULL` +
a `UNIQUE` constraintet enforces** -> **a mély link (a F-CAT-07)
mindig egyértelmű.**
"""

import pytest

from duna.domain.slug import generate_slug


def test_a_simla_nev():
    """A szokoznelkulculso nevből a kotojeles slug."""
    assert generate_slug("Test Hajo") == "test-hajo"


def test_a_magyar_ekezetek_lecsomagolva():
    """**Az ékezetmentes alak** (a `normalize_search_text`) ->
    **a `sort_name`-ével egyezik**."""
    assert generate_slug("Árvíztűrő Tó") == "arvizturo-to"


def test_a_pontok_kotojelre_valnak():
    """A pont/kötőjel -> kotojel (a normalizalas utan)."""
    assert generate_slug("Duna-Bojár") == "duna-bojar"


def test_a_mmsi_alapú_slug():
    """**Név nélkül az MMSI** (a hajót átnevezik, a MMSI nem)."""
    assert generate_slug(None, 243070510) == "243070510"
    assert generate_slug("", 243070510) == "243070510"


def test_a_nev_elonyi_dominanciaja():
    """**A név elsőbbséget élvez** az MMSI felett."""
    assert generate_slug("Test Hajo", 243070510) == "test-hajo"


def test_a_ures_nev_es_mmsi_nelkül_hiba():
    """**Név és MMSI nélkül nincs slug** -> **`ValueError`** (a hívó
    felelőssége, hogy ne hívja meg ilyen adattal)."""
    with pytest.raises(ValueError):
        generate_slug(None, None)
    with pytest.raises(ValueError):
        generate_slug("   ", None)


def test_a_szammal_kezdo_nev():
    """**A számmal kezdődő név** (a `123 Hajo`) -> **a slug
    `123-hajo`** (a `~` prefix NEM kell: a normalizált alap
    alfanumerikus kezdetű)."""
    assert generate_slug("123 Hajo") == "123-hajo"
