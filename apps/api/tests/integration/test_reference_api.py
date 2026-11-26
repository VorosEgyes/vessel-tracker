"""Reference endpoints against the migrated PostgreSQL schema."""

import os

import pytest
from fastapi.testclient import TestClient

from duna.main import app

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is not configured"
)


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
def test_reference_endpoints_postgresql(path):
    with TestClient(app) as client:
        response = client.get(f"/api/v1/{path}", params={"lang": "en", "per_page": 2})
        assert response.status_code == 200
        assert response.json()["meta"]["total"] >= len(response.json()["data"])


def test_reference_filters_and_missing_details_postgresql():
    with TestClient(app) as client:
        response = client.get("/api/v1/ports", params={"q": "%", "country_code": "HU"})
        assert response.status_code == 200
        assert client.get("/api/v1/ports/999999999").status_code == 404
        assert client.get("/api/v1/locks/999999999").status_code == 404
