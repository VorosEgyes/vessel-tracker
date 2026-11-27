"""Retention behavior against the migrated PostgreSQL function."""

import os
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from psycopg import sql

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is not configured"
)


@pytest.fixture
def db():
    url = (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )
    with psycopg.connect(url) as conn:
        yield conn
        conn.rollback()


def test_retention_uses_actual_bounds_and_cleans_default(db):
    now = datetime.now(UTC).replace(microsecond=0)
    db.execute("CREATE TEMP TABLE retention_test (ts timestamptz NOT NULL) PARTITION BY RANGE (ts)")
    for name, start, end in [
        ("old_month", -120, -100),
        ("straddling_month", -100, -80),
        ("recent_day", -70, -69),
    ]:
        db.execute(
            sql.SQL(
                "CREATE TEMP TABLE {} PARTITION OF retention_test FOR VALUES FROM ({}) TO ({})"
            ).format(
                sql.Identifier(name),
                sql.Literal(now + timedelta(days=start)),
                sql.Literal(now + timedelta(days=end)),
            )
        )
    db.execute(
        sql.SQL(
            "CREATE TEMP TABLE open_ended PARTITION OF retention_test "
            "FOR VALUES FROM ({}) TO (MAXVALUE)"
        ).format(sql.Literal(now + timedelta(days=1)))
    )
    db.execute("CREATE TEMP TABLE retention_default PARTITION OF retention_test DEFAULT")
    for days in (-110, -95, -85, -70, -150, -30, 2):
        db.execute("INSERT INTO retention_test VALUES (%s)", (now + timedelta(days=days),))

    assert db.execute("SELECT public.drop_expired_partitions('retention_test', 90)").fetchone() == (
        1,
    )
    remaining = db.execute("SELECT ts FROM retention_test ORDER BY ts").fetchall()
    assert remaining == [(now + timedelta(days=days),) for days in (-95, -85, -70, -30, 2)]
    assert db.execute("SELECT count(*) FROM retention_default").fetchone() == (1,)
    assert db.execute("SELECT to_regclass('old_month')").fetchone() == (None,)
    assert db.execute("SELECT to_regclass('straddling_month') IS NOT NULL").fetchone() == (True,)
    assert db.execute("SELECT public.drop_expired_partitions('retention_test', 90)").fetchone() == (
        0,
    )


def test_retention_cutoff_is_inclusive_for_partition_end_but_not_rows(db):
    now = db.execute("SELECT now()").fetchone()[0]
    cutoff = now - timedelta(days=90)
    db.execute("CREATE TEMP TABLE retention_boundary (ts timestamptz) PARTITION BY RANGE (ts)")
    db.execute(
        sql.SQL(
            "CREATE TEMP TABLE boundary_old PARTITION OF retention_boundary "
            "FOR VALUES FROM ({}) TO ({})"
        ).format(sql.Literal(cutoff - timedelta(days=2)), sql.Literal(cutoff))
    )
    db.execute("CREATE TEMP TABLE boundary_default PARTITION OF retention_boundary DEFAULT")
    db.execute(
        "INSERT INTO retention_boundary VALUES (%s), (%s)", (cutoff, cutoff - timedelta(days=3))
    )
    assert db.execute(
        "SELECT public.drop_expired_partitions('retention_boundary', 90)"
    ).fetchone() == (1,)
    assert db.execute("SELECT ts FROM retention_boundary").fetchall() == [(cutoff,)]


@pytest.mark.parametrize("table,days", [("missing_table", 90), ("retention_invalid", -1)])
def test_retention_rejects_invalid_input(db, table, days):
    db.execute("CREATE TEMP TABLE retention_invalid (ts timestamptz) PARTITION BY RANGE (ts)")
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("SELECT public.drop_expired_partitions(%s, %s)", (table, days))
    db.rollback()
