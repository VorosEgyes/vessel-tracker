"""A havi partíciók létrehozásának unit tesztje (a `02` §8.1).

**A `02` csak EGY konkrét partíciót definiál** (a
`position_p20261101`) + **a `default` partíciót** -> **a havi
partíciókat SENKI nem hozza létre** -> **ez a modul a hiányzó
bootstrap.**

**A KONVENCIÓ `pYYYYMMDD`** (a `02` §8.1: a `position_p20261101` a
`2026-11-01` -> `2026-12-01` határral).
"""

import datetime as dt

import pytest

from duna.ingest.partitions import (
    PARTITIONED_TABLES,
    _month_bounds,
    ensure_partitions,
    months_between,
)


def test_a_havi_hatok():
    """**A hónap eleje és a következő hónap eleje.**"""
    assert _month_bounds("202611") == ("2026-11-01", "2026-12-01")
    assert _month_bounds("202612") == ("2026-12-01", "2027-01-01")


def test_a_december_evvege():
    """**A december hatara a következő év januárja.**"""
    start, end = _month_bounds("202512")
    assert start == "2025-12-01"
    assert end == "2026-01-01"


def test_a_honapok_kozt():
    """**A hónapok a start és az end között** (a `ts` alapján)."""
    months = months_between(dt.datetime(2026, 11, 22, 18, 32), dt.datetime(2026, 12, 3, 10, 0))
    assert months == ["202611", "202612"]


def test_a_egy_honap():
    """**Egy hónap esetén egy elem.**"""
    months = months_between(dt.datetime(2026, 11, 1, 0, 0), dt.datetime(2026, 11, 30, 23, 59))
    assert months == ["202611"]


def test_a_particionalt_tablak():
    """**A három partícionált tábla** (a `02` §5.1) → **a `position`
    a `ts`, az `ais_message_raw` a `received_at`, a `water_level` a
    `ts` szerint.**"""
    assert PARTITIONED_TABLES == {
        "position": "ts",
        "ais_message_raw": "received_at",
        "water_level": "ts",
    }


def test_a_ismertetlen_tabla_hibaja():
    """**A nem partícionált tábla** -> **`ValueError`** (ne írjon
    véletlenül egy másik táblába)."""
    with pytest.raises(ValueError):
        ensure_partitions(None, "vessel", ["202611"])
