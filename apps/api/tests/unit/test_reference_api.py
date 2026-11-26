"""Reference API regression tests using an isolated SQL database."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    connection = engine.connect()
    statements = [
        "CREATE TABLE port (id INTEGER, code TEXT, unlocode TEXT, port_type TEXT, waterway_id INTEGER, country_code TEXT, river_km NUMERIC, is_active BOOLEAN)",
        "CREATE TABLE port_i18n (port_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE lock (id INTEGER, code TEXT, port_id INTEGER, chamber_count INTEGER, chamber_length_m NUMERIC, chamber_width_m NUMERIC, max_draft_m NUMERIC, operator_id INTEGER, avg_transit_min INTEGER, river_km NUMERIC)",
        "CREATE TABLE lock_i18n (lock_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE waterway (id INTEGER, code TEXT, waterway_type TEXT, length_km NUMERIC, is_active BOOLEAN)",
        "CREATE TABLE waterway_i18n (waterway_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE river_section (id INTEGER, code TEXT, waterway_id INTEGER, country_code TEXT, km_from NUMERIC, km_to NUMERIC, risk_level TEXT, max_draft_m NUMERIC, fairway_code TEXT)",
        "CREATE TABLE river_section_i18n (river_section_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE basin (id INTEGER, code TEXT, waterway_id INTEGER)",
        "CREATE TABLE basin_i18n (basin_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE vessel_type (code TEXT, un_code_28 TEXT, ais_type_code INTEGER, cargo_category TEXT, is_self_propelled BOOLEAN, operating_area TEXT)",
        "CREATE TABLE vessel_type_i18n (vessel_type_code TEXT, lang TEXT, name TEXT)",
        "CREATE TABLE operator (id INTEGER, legal_name TEXT, country_code TEXT, website TEXT, founded INTEGER)",
        "CREATE TABLE operator_i18n (operator_id INTEGER, lang TEXT, display_name TEXT)",
        "CREATE TABLE route (id INTEGER, code TEXT, origin_port_id INTEGER, dest_port_id INTEGER, distance_km NUMERIC, typical_duration_h NUMERIC, cargo_types TEXT)",
        "CREATE TABLE route_i18n (route_id INTEGER, lang TEXT, name TEXT)",
        "CREATE TABLE route_stop (route_id INTEGER, seq INTEGER, port_id INTEGER, typical_offset_h NUMERIC)",
        "CREATE TABLE cargo_type (code TEXT, nst_code TEXT, adn_code TEXT, imdg_code TEXT, is_bulk BOOLEAN, is_container BOOLEAN)",
        "CREATE TABLE cargo_type_i18n (cargo_type_code TEXT, lang TEXT, name TEXT)",
        "CREATE TABLE berth (id INTEGER, port_id INTEGER, code TEXT, length_m NUMERIC, depth_m NUMERIC, max_draft_m NUMERIC, unload_rate_t_h NUMERIC)",
        "CREATE TABLE terminal (id INTEGER, port_id INTEGER, operator_id INTEGER, annual_capacity_t NUMERIC, storage_capacity_t NUMERIC, rail_access BOOLEAN, gear_types TEXT)",
        "CREATE TABLE lock_status (id INTEGER, lock_id INTEGER, status TEXT, valid_from TEXT, valid_to TEXT, note TEXT, source TEXT)",
        "INSERT INTO port VALUES (1, 'BUD', 'HUBUD', 'public_port', 1, 'HU', 1642, 1), (2, 'SIO', NULL, 'marina', 2, 'HU', NULL, 1)",
        "INSERT INTO port_i18n VALUES (1, 'hu', 'Budapest'), (1, 'en', 'Budapest port'), (2, 'hu', 'Siófok')",
        "INSERT INTO lock VALUES (1, 'L1', 1, 1, 20, 10, 3, NULL, 5, 1642)",
        "INSERT INTO lock_i18n VALUES (1, 'hu', 'Zsilip')",
        "INSERT INTO waterway VALUES (1, 'DUNA', 'main', 2850, 1)",
        "INSERT INTO waterway_i18n VALUES (1, 'hu', 'Duna'), (1, 'en', 'Danube')",
        "INSERT INTO river_section VALUES (1, 'SEC', 1, 'HU', 1600, 1700, 'low', NULL, NULL)",
        "INSERT INTO basin VALUES (1, 'WEST', 1)",
        "INSERT INTO vessel_type VALUES ('SHIP', NULL, 60, NULL, 1, 'duna')",
        "INSERT INTO operator VALUES (1, 'Shipping Ltd', 'HU', NULL, NULL)",
        "INSERT INTO route VALUES (1, 'R1', 1, 2, 100, 4, NULL)",
        "INSERT INTO route_stop VALUES (1, 2, 2, 4), (1, 1, 1, 0)",
        "INSERT INTO cargo_type VALUES ('BULK', NULL, NULL, NULL, 1, 0)",
        "INSERT INTO berth VALUES (1, 1, 'B1', 20, 3, 2, NULL)",
        "INSERT INTO terminal VALUES (1, 1, NULL, NULL, NULL, 0, NULL)",
        "INSERT INTO lock_status VALUES (1, 1, 'open', '2026-01-01T10:00:00Z', NULL, NULL, 'manual'), (2, 1, 'closed', '2026-02-01T10:00:00Z', NULL, NULL, 'notice')",
    ]
    for sql in statements:
        connection.exec_driver_sql(sql)
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = connection.execute
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session)
        connection.close()
        engine.dispose()


@pytest.mark.parametrize(
    "path",
    [
        "ports",
        "locks",
        "waterways",
        "river-sections",
        "basins",
        "vessel-types",
        "operators",
        "routes",
        "cargo-types",
    ],
)
def test_reference_endpoints_and_pagination(client, path):
    response = client.get(f"/api/v1/{path}", params={"page": 1, "per_page": 1, "lang": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] >= 1
    assert len(body["data"]) == 1
    assert body["data"][0]["name"]
    assert body["data"][0]["name_fallback"] is True
    assert body["meta"]["has_more"] == (body["meta"]["total"] > 1)


def test_port_filters_fallback_and_literal_search(client):
    response = client.get(
        "/api/v1/ports",
        params={
            "lang": "de",
            "waterway_id": 1,
            "country_code": "HU",
            "port_type": "public_port",
            "q": "HUBUD",
        },
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1
    item = response.json()["data"][0]
    assert item["name"] == "Budapest port"
    assert item["name_language"] == "en"
    assert client.get("/api/v1/ports", params={"q": "%"}).json()["data"] == []
    assert client.get("/api/v1/ports", params={"q": " "}).status_code == 422
    assert client.get("/api/v1/ports", params={"per_page": 0}).status_code == 422
    assert client.get("/api/v1/ports", params={"unknown": "value"}).status_code == 422


def test_detail_children_statuses_routes_and_missing(client):
    port = client.get("/api/v1/ports/1", params={"lang": "en"}).json()["data"]
    assert port["berths"][0]["code"] == "B1"
    assert port["terminals"][0]["id"] == 1
    assert port["locks"][0]["name"] == "Zsilip"
    lock = client.get("/api/v1/locks/1").json()["data"]
    assert [status["status"] for status in lock["statuses"]] == ["closed", "open"]
    route = client.get("/api/v1/routes").json()["data"][0]
    assert [stop["seq"] for stop in route["stops"]] == [1, 2]
    assert client.get("/api/v1/ports/99").status_code == 404
    assert client.get("/api/v1/locks/99").status_code == 404
    assert "/api/v1/ports" in client.get("/openapi.json").json()["paths"]
