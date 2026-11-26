"""A szövegnormalizálás unit tesztje (a F-SRCH-03).

**A `duna.domain.text` a keresési kifejezést a DB `sort_name`-ének
alakjára hozza** -> **a normalizálásnak pontosan a trigger
`lower(unaccent(name))` alakját kell adnia** -> **a kettő egyezése
a trigram-index használhatóságának feltétele.**

**A magyar ékezetek a `unicodedata` NFKD-val NEM bomlanak** (az
`ő`/`ű` külön Unicode karakter) -> **ezért a kézi mapping kell.**
"""

from duna.domain.text import is_identifier_like, normalize_search_text


def test_a_simla_szoveg_változatlan():
    """A sima szöveg változatlan (a `casefold` a kis-nagybetűt)."""
    assert normalize_search_text("Test Hajo") == "test hajo"


def test_a_magyar_ekezetek_lecsomagolva():
    """**A magyar ékezetek -> a latin alapbetű** (a `unaccent` alakja)."""
    assert normalize_search_text("Árvíztűrő") == "arvizturo"
    assert normalize_search_text("Ősz") == "osz"
    assert normalize_search_text("Ürökség") == "urokseg"
    assert normalize_search_text("Év") == "ev"


def test_a_hosszu_magyar_hangok():
    """**A hosszú ő/ű -> a hosszú o/u** (az `unaccent` magyar mappingje)."""
    assert normalize_search_text("KÖTŐZŐ") == "kotozo"
    assert normalize_search_text("TŰ") == "tu"


def test_a_kezdokezet_nagybetu():
    """A nagybetű -> kisbetű (a `lower` alakja)."""
    assert normalize_search_text("TESZTHAJO") == "teszthajo"


def test_a_pont_szokoz_helyettesites():
    """**A nem betű/nem szám -> szóköz** (a `%` és az `_` nem kereshető)."""
    assert normalize_search_text("Duna-Bojár") == "duna bojar"
    assert normalize_search_text("100%") == "100"
    assert normalize_search_text("a_b") == "a b"


def test_az_ures_szoveg():
    """Az üres szöveg -> üres (a `strip` után)."""
    assert normalize_search_text("   ") == ""


def test_az_azonosito_szeru():
    """**A `q` azonosító-szerű?** (a F-SRCH-02: a pontos
    azonosító-egyezés) -> **csak a számok** (az ENI, az MMSI, az IMO)
    -> **a hívójell nem az**.
    """
    assert is_identifier_like("12345678") is True
    assert is_identifier_like("87654321") is True
    assert is_identifier_like("HGXC") is False
    assert is_identifier_like("") is False
    assert is_identifier_like("12A") is False
