"""A katalóguslista integrációs tesztje (a 08 §4.3).

**A `DATABASE_URL` kell** (a CI-ben a PostgreSQL service adja, a
`07` §4.2) → **a `DATABASE_URL` hiányában a teszt KIHAGYJA
magát** (nem hiba).

**A `testcontainers` a `08` §4.3 szerint a komponens tesztekhez kell**
→ **az integrációs teszt a CI service-re épül** (a `07` §4.2) →
**a `pytest` a `pytest-asyncio` miatt async teszteket is futtat.**
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from duna.main import app

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="a DATABASE_URL nincs beállítva -> az integrációs teszt kihagyva",
)


@pytest.fixture(scope="module")
def client():
    """A FastAPI kliens.

    **A `with` blokk a LIFESPAN-t futtatja** → **az engine és a
    `session_factory` az `app.state`-ben lesz** → **a `get_session`
    függőség megtalálja** (a `duna.db.session` modul docstringje).
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def seeded_vessel() -> int:
    """Egy teszt-hajó a DB-be (a `vessel` + a `vessel_i18n`).

    **A `ON CONFLICT DO NOTHING`** → **a teszt idempotens** → **a
    `pytest` újrafuttatásakor nem duplikálódik.**
    """
    import asyncio

    async def _seed() -> int:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO vessel (mmsi, eni, slug, sort_name, vessel_type_code,"
                    " operating_area, flag_country_code, status, verification_level,"
                    " length_m, beam_m) VALUES (243070510, '87654321', 'test-hajo',"
                    " 'TEST HAJO', (SELECT code FROM vessel_type WHERE ais_type_code = 60 LIMIT 1),"
                    " 'duna', (SELECT code FROM country LIMIT 1), 'active', 'name_only',"
                    " 85.5, 11.2) ON CONFLICT (slug) DO NOTHING"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO vessel_i18n (vessel_id, lang, name, description)"
                    " SELECT id, 'hu', 'TESZTHAJÓ', 'a teszt hajója' FROM vessel"
                    " WHERE slug = 'test-hajo' ON CONFLICT DO NOTHING"
                )
            )
            # **a masodik hajo** (a lapozasi teszthez kell: a
            # `has_more` csak 2+ elemnél true)
            await conn.execute(
                text(
                    "INSERT INTO vessel (mmsi, eni, slug, sort_name, vessel_type_code,"
                    " operating_area, flag_country_code, status, verification_level,"
                    " length_m, beam_m) VALUES (243070511, '87654322', 'test-hajo-2',"
                    " 'TEST HAJO 2', (SELECT code FROM vessel_type WHERE ais_type_code = 60 LIMIT 1),"
                    " 'duna', (SELECT code FROM country LIMIT 1), 'active', 'ais_identified',"
                    " 42.0, 8.4) ON CONFLICT (slug) DO NOTHING"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO vessel_i18n (vessel_id, lang, name, description)"
                    " SELECT id, 'hu', 'TESZTHAJÓ 2', 'a második teszt hajója' FROM vessel"
                    " WHERE slug = 'test-hajo-2' ON CONFLICT DO NOTHING"
                )
            )
            # **A `vessel_identifier` (a `vessel_verification` nézet
            # EZEN csoportosít)** -> **az AIS-eredetű ENI** ->
            # **a számított bizonyossági szint `ais_identified`**
            # -> **az 1. hajót `name_only`-t TÁROL, de a számított
            # érték `ais_identified`** (a `stored_stale` eltérés).
            await conn.execute(
                text(
                    "INSERT INTO vessel_identifier (vessel_id, identifier_type,"
                    " value, is_primary, origin) SELECT id, 'eni', '87654321', true,"
                    " 'ais' FROM vessel WHERE slug = 'test-hajo'"
                    " ON CONFLICT DO NOTHING"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO vessel_identifier (vessel_id, identifier_type,"
                    " value, is_primary, origin) SELECT id, 'eni', '87654322', true,"
                    " 'ais' FROM vessel WHERE slug = 'test-hajo-2'"
                    " ON CONFLICT DO NOTHING"
                )
            )
            result = await conn.execute(text("SELECT id FROM vessel WHERE slug = 'test-hajo'"))
            vessel_id = result.scalar_one()
        await engine.dispose()
        return int(vessel_id)

    return asyncio.run(_seed())


def test_a_health_a_db_t_pingeli(client: TestClient):
    """A `/health` a DB elérhetőségét ellenőrzi."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}


def test_a_kataloguslista_visszaadja_a_hajot(client: TestClient, seeded_vessel: int):
    """A `GET /api/v1/vessels` a seedelt hajót visszaadja."""
    resp = client.get("/api/v1/vessels", params={"area": "duna", "per_page": 50})
    assert resp.status_code == 200
    body = resp.json()

    assert body["meta"]["total"] >= 1
    assert body["meta"]["page"] == 1

    # a seedelt hajo a listaban
    items = {item["id"]: item for item in body["data"]}
    assert seeded_vessel in items
    item = items[seeded_vessel]
    assert item["slug"] == "test-hajo"
    assert item["name"] == "TESZTHAJÓ"
    assert item["vessel_type_name"] == "utasszállító hajó"
    assert item["operating_area"] == "duna"
    assert item["status"] == "active"


def test_a_bizonyossagi_szint_szamított(client: TestClient, seeded_vessel: int):
    """**A `verification_level` a SZÁMÍTOTT érték** (a 03 §5.2) → **a
    `vessel_verification` nézetből** → **nem a tároltból**.

    **A seedelt hajó `name_only`-t tárol, de AIS-eredetű ENI-ja van**
    → **a számított érték `ais_identified`** → **a
    `verification_source` a `stored_stale`-t jelzi** (az eltérés).
    """
    resp = client.get("/api/v1/vessels", params={"area": "duna", "per_page": 50})
    body = resp.json()
    item = next(i for i in body["data"] if i["slug"] == "test-hajo")

    assert item["verification_level"] == "ais_identified"
    assert item["verification_source"] == "stored_stale"


def test_a_area_szuro_kotelezo(client: TestClient):
    """**Az `area` KÖTELEZŐ** (a 03 §3.1: a F-CAT-01) → **a 422
    FastAPI validációs hiba."""
    resp = client.get("/api/v1/vessels")
    assert resp.status_code == 422


def test_a_lapazas_bolto(client: TestClient, seeded_vessel: int):
    """**A lapozás** (a F-CAT-02) → **a `per_page=1` és a `page=2`
    más elemet ad**."""
    r1 = client.get("/api/v1/vessels", params={"area": "duna", "per_page": 1, "page": 1})
    r2 = client.get("/api/v1/vessels", params={"area": "duna", "per_page": 1, "page": 2})
    assert r1.status_code == 200
    assert r2.status_code == 200

    b1 = r1.json()
    b2 = r2.json()
    assert b1["meta"]["per_page"] == 1
    assert b1["meta"]["has_more"] is True
    assert b1["data"] and b2["data"]
    assert b1["data"][0]["id"] != b2["data"][0]["id"]

    # **a `meta.total` a szures UTANI teljes darabszam** (a 03 §5.5)
    assert b1["meta"]["total"] == b2["meta"]["total"]
    assert b1["meta"]["total"] >= 2


def test_a_verifikacio_szuro_a_tarolt_ertekre_epul(client: TestClient, seeded_vessel: int):
    """**A `verification` szűrő a TÁROLT értékre épül** (a 03 §3.1:
    a szűrő indexelt → a tárolt `vessel.verification_level`) → **a
    seedelt hajó `name_only`-t tárol** → **a `name_only` szűrő
    megtalálja, az `ais_identified` nem** (az a számított érték).
    """
    r_stored = client.get("/api/v1/vessels", params={"area": "duna", "verification": "name_only"})
    r_computed = client.get(
        "/api/v1/vessels", params={"area": "duna", "verification": "ais_identified"}
    )
    assert r_stored.status_code == 200
    assert r_computed.status_code == 200

    stored_ids = {i["id"] for i in r_stored.json()["data"]}
    computed_ids = {i["id"] for i in r_computed.json()["data"]}
    assert seeded_vessel in stored_ids
    assert seeded_vessel not in computed_ids


def test_az_openapi_sema_elkesz(client: TestClient):
    """**Az OpenAPI séma** (a 03 §5.1a) → **a specifikáció a kódból
    jön** → **a `/api/v1/vessels` a `Page[VesselListItem]` burkolót
    adja**."""
    schema = client.get("/openapi.json").json()
    assert "/api/v1/vessels" in schema["paths"]
    assert "/health" in schema["paths"]

    # a generikus burkolo a `data`/`meta` (a 03 §5.5)
    ref = schema["paths"]["/api/v1/vessels"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    name = ref.split("/")[-1]
    assert name.startswith("Page")
