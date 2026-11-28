"""A havi partíciók létrehozásának integrációs tesztje (a `02` §8.1).

**A `02` csak egy konkrét partíciót definiál** -> **a betöltés
előtt a havi partíciókat létre kell hozni** -> **a `default`
partícióba nem írunk** (a TTL azt üríti).

**A `position` a `ts` szerint partícionált** -> **a partíció neve
`position_pYYYYMMDD`** (a `02` §8.1 konvenciója).
"""

import os

import pytest
import sqlalchemy as sa

from duna.ingest.partitions import ensure_partitions

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="a DATABASE_URL nincs beállítva -> az integrációs teszt kihagyva",
)


@pytest.fixture(scope="module")
def conn():
    """Egy szinkron kapcsolat (a `ensure_partitions` szinkron)."""
    import sqlalchemy as sa

    from duna.config import get_settings

    engine = sa.create_engine(get_settings().sync_database_url, poolclass=sa.pool.NullPool)
    with engine.connect() as connection:
        yield connection
    engine.dispose()


def test_a_particio_letrejon(conn):
    """**A havi partíció létrejön** -> **a nézetben a helyes határ.**"""
    created = ensure_partitions(conn, "position", ["202612"])
    assert "position_p20261201" in created

    rows = conn.execute(
        sa.text(
            "SELECT pg_get_expr(c.relpartbound, c.oid) AS bound "
            "FROM pg_class c WHERE c.relname = 'position_p20261201'"
        )
    ).all()
    assert rows
    assert "2026-12-01" in rows[0].bound


def test_a_mar_letezo_particio_nem_ujul_kul(conn):
    """**A már létező partíció** -> **nem hozzuk újra** (a `CREATE
    TABLE` elbukna a „already exists" hibával)."""
    ensure_partitions(conn, "position", ["202612"])
    created = ensure_partitions(conn, "position", ["202612"])
    assert "position_p20261201" not in created


def test_a_pozicio_bekerul_a_particioba(conn):
    """**A pozíció a konkrét havi partícióba kerül** (nem a
    `default`-ba) -> **a TTL nem törli.**"""

    ensure_partitions(conn, "position", ["202612"])

    vessel_id = conn.execute(
        sa.text(
            "INSERT INTO vessel (slug, sort_name, vessel_type_code, "
            "operating_area, flag_country_code, status, verification_level) "
            "SELECT 'particio-teszt', 'particio teszt', "
            "(SELECT code FROM vessel_type LIMIT 1), 'duna', "
            "(SELECT code FROM country LIMIT 1), 'active', 'name_only' "
            "ON CONFLICT (slug) DO NOTHING RETURNING id"
        )
    ).first()
    if vessel_id is None:
        vessel_id = conn.execute(
            sa.text("SELECT id FROM vessel WHERE slug = 'particio-teszt'")
        ).first()
    vessel_id = vessel_id[0]

    conn.execute(
        sa.text(
            "INSERT INTO position (vessel_id, ts, msg_type, lat_e7, lon_e7) "
            "VALUES (:vessel_id, '2026-12-15 12:00:00+00', 3, 475525050, 190686700) "
            "ON CONFLICT (vessel_id, ts) DO NOTHING"
        ),
        {"vessel_id": vessel_id},
    )

    where = conn.execute(
        sa.text(
            "SELECT tableoid::regclass::text AS part FROM position "
            "WHERE vessel_id = :vessel_id AND ts = '2026-12-15 12:00:00+00'"
        ),
        {"vessel_id": vessel_id},
    ).first()
    assert where
    assert "position_p20261201" in where.part
