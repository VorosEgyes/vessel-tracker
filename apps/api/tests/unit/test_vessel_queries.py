"""Regression tests for catalog, search and detail query behavior."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.main import app
from duna.repositories.search_repo import SearchParams, search
from duna.repositories.vessel_detail_repo import get_vessel_detail
from duna.repositories.vessel_repo import VesselFilters, list_vessels


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    connection = engine.connect()
    statements = [
        """CREATE TABLE vessel (
            id INTEGER PRIMARY KEY, slug TEXT, sort_name TEXT, vessel_type_code TEXT,
            operating_area TEXT, status TEXT, verification_level TEXT, operator_id INTEGER,
            home_port_id INTEGER, flag_country_code TEXT, length_m NUMERIC, updated_at TEXT,
            mmsi INTEGER, eni TEXT, imo TEXT, callsign TEXT, build_year INTEGER,
            beam_m NUMERIC, draught_max_m NUMERIC, gross_tonnage NUMERIC,
            deadweight_t NUMERIC, teu INTEGER, passenger_capacity INTEGER,
            is_passenger_certified BOOLEAN, destination TEXT
        )""",
        "CREATE TABLE vessel_i18n (vessel_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE vessel_type_i18n (vessel_type_code TEXT, lang TEXT, name TEXT)",
        "CREATE TABLE operator_i18n (operator_id INTEGER, lang TEXT, display_name TEXT)",
        "CREATE TABLE port_i18n (port_id INTEGER, lang TEXT, name TEXT)",
        """CREATE TABLE vessel_identifier (
            id INTEGER PRIMARY KEY, vessel_id INTEGER, identifier_type TEXT,
            value TEXT, is_primary BOOLEAN, valid_to TEXT
        )""",
        """CREATE TABLE vessel_verification (
            vessel_id INTEGER, computed_verification_level TEXT, is_stale BOOLEAN
        )""",
        """CREATE TABLE vessel_last_position (
            vessel_id INTEGER, ts TEXT, river_km NUMERIC, river_section_id INTEGER, basin_id INTEGER
        )""",
        "CREATE TABLE country (code TEXT, name_local TEXT)",
        """CREATE TABLE vessel_data_origin (
            vessel_id INTEGER, field_name TEXT, origin TEXT, value_snapshot TEXT,
            observed_at TEXT, confidence NUMERIC, is_current BOOLEAN, source_id INTEGER
        )""",
        "CREATE TABLE data_source (id INTEGER, name TEXT)",
        "CREATE TABLE vessel_ownership (vessel_id INTEGER, operator_id INTEGER, valid_from TEXT, valid_to TEXT)",
        "CREATE TABLE waterway_i18n (waterway_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE river_section (id INTEGER, waterway_id INTEGER)",
        "CREATE TABLE river_section_i18n (river_section_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE basin (id INTEGER, waterway_id INTEGER)",
        "CREATE TABLE basin_i18n (basin_id INTEGER, lang TEXT, name TEXT)",
        """INSERT INTO vessel (id, slug, sort_name, vessel_type_code, operating_area, status,
             verification_level, operator_id, flag_country_code, is_passenger_certified)
             VALUES (1, 'a', 'teszthajo a', 'ship', 'duna', 'active', 'name_only', 1, 'HU', 0),
                    (2, 'b', 'teszthajo b', 'ship', 'duna', 'active', 'name_only', 1, 'HU', 0),
                    (3, 'c', 'balaton', 'ship', 'balaton', 'active', 'name_only', 1, 'HU', 0)""",
        "INSERT INTO vessel_i18n VALUES (1, 'hu', 'TESZTHAJÓ A'), (2, 'hu', 'TESZTHAJÓ B'), (3, 'hu', 'BALATON')",
        "INSERT INTO vessel_type_i18n VALUES ('ship', 'hu', 'Hajó'), ('ship', 'en', 'Ship')",
        "INSERT INTO operator_i18n VALUES (1, 'hu', 'Magyar'), (1, 'en', 'English')",
        """INSERT INTO vessel_identifier VALUES
            (1, 1, 'eni', '12345678', 1, NULL), (2, 1, 'mmsi', '243000001', 1, NULL),
            (3, 3, 'eni', '87654321', 1, NULL)""",
        """INSERT INTO vessel_verification VALUES
            (1, 'name_only', 0), (2, 'name_only', 0), (3, 'name_only', 0)""",
        "INSERT INTO country VALUES ('HU', 'Magyarország')",
        "INSERT INTO vessel_last_position VALUES (1, '2026-01-01 12:00:00', 1642, 5, NULL)",
        "INSERT INTO river_section VALUES (5, 6)",
        "INSERT INTO river_section_i18n VALUES (5, 'hu', 'Szob–Budapest')",
        "INSERT INTO waterway_i18n VALUES (6, 'hu', 'Duna'), (6, 'en', 'Danube')",
    ]
    for statement in statements:
        connection.exec_driver_sql(statement)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = connection.execute
    yield mock_session
    connection.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_catalog_single_row_per_vessel_and_query_pagination(session):
    items, total, more = await list_vessels(session, VesselFilters(area="duna", lang="en"))
    assert total == 2
    assert [item.id for item in items] == [1, 2]
    assert items[0].identifier == "12345678"
    assert items[0].name == "TESZTHAJÓ A"
    assert items[0].vessel_type_name == "Ship"
    assert items[0].operator_name == "English"
    assert not more

    items, total, more = await list_vessels(
        session, VesselFilters(area="duna", q="teszthajo", per_page=1)
    )
    assert len(items) == 1
    assert total is None
    assert more
    items, _, more = await list_vessels(
        session, VesselFilters(area="duna", q="teszthajo", per_page=1, page=2)
    )
    assert len(items) == 1
    assert not more


@pytest.mark.asyncio
async def test_search_identifier_matches_non_displayed_identifier_and_other_area(session):
    items, total, _, _ = await search(session, SearchParams("duna", "243000001", "en"))
    assert [item.id for item in items] == [1]
    assert total == 1
    items, _, hint, _ = await search(session, SearchParams("duna", "87654321"))
    assert items == []
    assert hint is True
    items, _, _, more = await search(session, SearchParams("duna", "teszthajo", limit=1))
    assert len(items) == 1
    assert more


@pytest.mark.asyncio
async def test_detail_language_fallback_and_location(session):
    detail = await get_vessel_detail(session, 1, "en")
    assert detail is not None
    assert detail.name == "TESZTHAJÓ A"
    assert detail.vessel_type_name == "Ship"
    assert detail.operator_name == "English"
    assert detail.location_text == "Danube, 1642 km, Szob–Budapest"


def test_invalid_and_unsupported_filters_are_rejected():
    app.dependency_overrides[get_session] = lambda: None
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/vessels?area=invalid").status_code == 422
            assert client.get("/api/v1/vessels?area=duna&moving=true").status_code == 422
            assert client.get("/api/v1/search?area=invalid&q=test").status_code == 422
            assert client.get("/api/v1/search?area=duna&q=%20%20").status_code == 422
    finally:
        app.dependency_overrides.pop(get_session)
