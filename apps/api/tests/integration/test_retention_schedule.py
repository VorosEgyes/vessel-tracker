"""Verify retention scheduling against a PostgreSQL database."""

import importlib.util
import os
import time
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql as pgsql

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is not configured"
)

MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "db/migrations/versions/20261127_0003_retention_schedule.py"
)
spec = importlib.util.spec_from_file_location("retention_schedule", MIGRATION)
assert spec is not None and spec.loader is not None
schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule)


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


@pytest.fixture
def cron_db(db):
    if not db.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron')"
    ).fetchone()[0]:
        pytest.skip("pg_cron is not installed")
    return db


def test_missing_extension_warns_or_rejects_misconfiguration(db):
    installed, available = db.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'), "
        "EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron')"
    ).fetchone()
    if installed:
        pytest.skip("pg_cron is installed")
    sql = schedule.SCHEDULE_SQL.read_text(encoding="utf-8")
    if available:
        with pytest.raises(psycopg.errors.RaiseException, match="available but not installed"):
            db.execute(sql)
    else:
        notices = []
        db.add_notice_handler(lambda diagnostic: notices.append(diagnostic.message_primary))
        db.execute(sql)
        assert any("retention jobs are NOT scheduled" in notice for notice in notices)


def test_schedules_are_complete_and_idempotent(cron_db):
    sql = schedule.SCHEDULE_SQL.read_text(encoding="utf-8")
    cron_db.execute(sql)
    first = cron_db.execute(
        "SELECT jobid, jobname, schedule, command, database, username, active "
        "FROM cron.job WHERE jobname IN "
        "('drop-raw-partitions', 'drop-water-level-partitions', 'drop-position-partitions') "
        "ORDER BY jobname"
    ).fetchall()
    cron_db.execute(sql)
    second = cron_db.execute(
        "SELECT jobid, jobname, schedule, command, database, username, active "
        "FROM cron.job WHERE jobname IN "
        "('drop-raw-partitions', 'drop-water-level-partitions', 'drop-position-partitions') "
        "ORDER BY jobname"
    ).fetchall()
    assert first == second
    assert [(row[1], row[2], row[3]) for row in first] == [
        (
            "drop-position-partitions",
            "27 3 * * 1",
            "SELECT public.drop_expired_partitions('public.position', 90)",
        ),
        (
            "drop-raw-partitions",
            "17 3 * * 1",
            "SELECT public.drop_expired_partitions('public.ais_message_raw', 14)",
        ),
        (
            "drop-water-level-partitions",
            "23 3 * * 1",
            "SELECT public.drop_expired_partitions('public.water_level', 90)",
        ),
    ]
    current_db, current_user = cron_db.execute("SELECT current_database(), current_user").fetchone()
    assert all(row[4:] == (current_db, current_user, True) for row in first)


def test_conflicting_schedule_fails_without_overwriting(cron_db):
    sql = schedule.SCHEDULE_SQL.read_text(encoding="utf-8")
    cron_db.execute(sql)
    cron_db.execute("SELECT cron.schedule('drop-position-partitions', '* * * * *', 'SELECT 1')")
    with pytest.raises(psycopg.errors.RaiseException, match="Conflicting pg_cron job"):
        cron_db.execute(sql)


def test_downgrade_removes_jobs_and_upgrade_restores_them(cron_db, monkeypatch):
    cron_db.execute(schedule.SCHEDULE_SQL.read_text(encoding="utf-8"))
    monkeypatch.setattr(schedule.op, "execute", cron_db.execute)
    schedule.downgrade()
    assert cron_db.execute(
        "SELECT count(*) FROM cron.job WHERE jobname IN "
        "('drop-raw-partitions', 'drop-water-level-partitions', 'drop-position-partitions')"
    ).fetchone() == (0,)
    cron_db.execute(schedule.SCHEDULE_SQL.read_text(encoding="utf-8"))
    assert cron_db.execute(
        "SELECT count(*) FROM cron.job WHERE jobname IN "
        "('drop-raw-partitions', 'drop-water-level-partitions', 'drop-position-partitions')"
    ).fetchone() == (3,)


def test_downgrade_rejects_job_owned_by_another_user(cron_db, monkeypatch):
    cron_db.execute(schedule.SCHEDULE_SQL.read_text(encoding="utf-8"))
    cron_db.execute(
        "UPDATE cron.job SET username = 'different_retention_owner' "
        "WHERE jobname = 'drop-position-partitions'"
    )
    monkeypatch.setattr(schedule.op, "execute", cron_db.execute)
    with pytest.raises(psycopg.errors.RaiseException, match="Conflicting retention job ownership"):
        schedule.downgrade()


def test_real_cron_worker_runs_retention(cron_db):
    url = (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )
    name = f"cron_retention_test_{uuid4().hex}"
    job_id = None
    with psycopg.connect(url, autocommit=True) as conn:
        try:
            conn.execute(
                pgsql.SQL("CREATE TABLE public.{} (ts timestamptz) PARTITION BY RANGE (ts)").format(
                    pgsql.Identifier(name)
                )
            )
            conn.execute(
                pgsql.SQL("CREATE TABLE public.{} PARTITION OF public.{} DEFAULT").format(
                    pgsql.Identifier(f"{name}_default"), pgsql.Identifier(name)
                )
            )
            conn.execute(
                pgsql.SQL("INSERT INTO public.{} VALUES (now() - interval '100 days')").format(
                    pgsql.Identifier(name)
                )
            )
            command = (
                pgsql.SQL("SELECT public.drop_expired_partitions({}, 90)")
                .format(pgsql.Literal(f"public.{name}"))
                .as_string(conn)
            )
            job_id = conn.execute(
                "SELECT cron.schedule(%s, '1 second', %s)", (name, command)
            ).fetchone()[0]
            deadline = time.monotonic() + 20
            runs = []
            while time.monotonic() < deadline:
                runs = conn.execute(
                    "SELECT status, return_message FROM cron.job_run_details WHERE jobid = %s",
                    (job_id,),
                ).fetchall()
                if any(status == "succeeded" for status, _ in runs):
                    break
                time.sleep(0.25)
            assert any(status == "succeeded" for status, _ in runs), runs
            assert conn.execute(
                pgsql.SQL("SELECT count(*) FROM public.{}").format(pgsql.Identifier(name))
            ).fetchone() == (0,)
        finally:
            if job_id is not None:
                conn.execute("SELECT cron.unschedule(%s)", (job_id,))
            conn.execute(pgsql.SQL("DROP TABLE IF EXISTS public.{}").format(pgsql.Identifier(name)))
