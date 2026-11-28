"""A normalizált AIS-rekord unit tesztje (a `04` §5 — a szerződés).

**A `NormalizedAisMessage` a `02` és a `04` közötti EGYETLEN
definíció** → **a `02` ebből generálja az oszlopokat** → **a
modellnek a sémával egyeznie kell.**
"""

import datetime as dt

import pytest

from duna.ingest.models import NormalizedAisMessage, PositionUpsert


def _minimal() -> dict:
    return {
        "source_code": "own-ais-budapest",
        "received_at": dt.datetime(2026, 11, 22, 18, 32, tzinfo=dt.UTC),
        "msg_hash": b"\x00" * 32,
        "mmsi": 243070510,
        "msg_type": 3,
    }


def test_a_minimalis_rekord():
    """**A minimum mezők** -> **a rekord létrejön** (a `source_code`,
    a `received_at`, a `msg_hash`, az `mmsi`, a `msg_type`)."""
    record = NormalizedAisMessage(**_minimal())
    assert record.mmsi == 243070510
    assert record.msg_type == 3
    assert record.source_kind == "ais"


def test_a_hianyzo_pozicio_mehet_null():
    """**A pozíció-mezők opcionálisak** (a statikus üzenetben nincs
    pozíció)."""
    record = NormalizedAisMessage(**_minimal())
    assert record.lat_e7 is None
    assert record.sog_mps is None
    assert record.nav_status is None
    assert record.river_km is None


def test_a_pozicios_rekord():
    """**A pozíció teljes** -> **az értékek megmaradnak.**"""
    data = _minimal()
    data.update(
        {
            "ts": dt.datetime(2026, 11, 22, 18, 30, tzinfo=dt.UTC),
            "lat_e7": 475525050,
            "lon_e7": 190686700,
            "sog_mps": 3.5,
            "cog_deg": 62.2,
            "heading_deg": 61.0,
        }
    )
    record = NormalizedAisMessage(**data)
    assert record.lat_e7 == 475525050
    assert record.sog_mps == 3.5
    assert record.cog_deg == 62.2


def test_a_msg_subtype_a_dac_fid():
    """**A `msg_subtype` a DAC/FID** (a `04` C-3 findingje: a
    `msg_type` önmagában nem eleg)."""
    data = _minimal()
    data["msg_subtype"] = 10
    record = NormalizedAisMessage(**data)
    assert record.msg_subtype == 10


def test_a_forras_kind_lehetseg():
    """**A `source_kind` három értékű** (a `02` §5.1)."""
    data = _minimal()
    data["source_kind"] = "derived"
    assert NormalizedAisMessage(**data).source_kind == "derived"
    data["source_kind"] = "invalid"
    with pytest.raises(ValueError):
        NormalizedAisMessage(**data)


def test_a_draught_reference_csak_rnw():
    """**A `draught_reference` csak `RNW`** (a `02` §5.1)."""
    data = _minimal()
    data["draught_reference"] = "RNW"
    assert NormalizedAisMessage(**data).draught_reference == "RNW"
    data["draught_reference"] = "TFW"
    with pytest.raises(ValueError):
        NormalizedAisMessage(**data)


def test_a_position_upsert_a_sema_mezői():
    """**A `PositionUpsert` a `position` tábla oszlopait tükrözi** (a
    `02` §5.1) → **a `lat_e7`/`lon_e7` integer** → **a `sog_mps` a
    m/s-ben.**"""
    upsert = PositionUpsert(
        vessel_id=1,
        ts=dt.datetime(2026, 11, 22, 18, 32, tzinfo=dt.UTC),
        msg_type=3,
        sog_mps=3.5,
        lat_e7=475525050,
        lon_e7=190686700,
    )
    assert upsert.vessel_id == 1
    assert upsert.lat_e7 == 475525050
    assert upsert.source_kind == "ais"
