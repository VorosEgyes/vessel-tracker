"""Connection settings used by the initial migration's psql process."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

MIGRATION = (
    Path(__file__).resolve().parents[4] / "db/migrations/versions/20241124_0001_initial_schema.py"
)
spec = importlib.util.spec_from_file_location("initial_schema", MIGRATION)
assert spec is not None and spec.loader is not None
initial_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initial_schema)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "postgresql+asyncpg://user:pass%40word@/test_db?host=%2Ftmp%2Fpg&port=5433",
            {
                "PGHOST": "/tmp/pg",
                "PGPORT": "5433",
                "PGUSER": "user",
                "PGPASSWORD": "pass@word",
                "PGDATABASE": "test_db",
            },
        ),
        (
            "postgresql+psycopg://user:pass@localhost:5434/test_db",
            {
                "PGHOST": "localhost",
                "PGPORT": "5434",
                "PGUSER": "user",
                "PGPASSWORD": "pass",
                "PGDATABASE": "test_db",
            },
        ),
    ],
)
def test_psql_receives_database_url_settings(url, expected):
    env = {"DATABASE_URL": url, "PGDATABASE": "postgres"}
    initial_schema._apply_db_url_to_env(env)
    assert {key: env[key] for key in expected} == expected


def test_psql_binary_resolves_pgbin_directory(monkeypatch, tmp_path):
    psql = tmp_path / "psql"
    psql.touch()
    monkeypatch.setenv("PGPGBIN", str(tmp_path))
    assert initial_schema._psql() == str(psql)


def test_initial_schema_snapshot_is_unchanged():
    assert MIGRATION.with_suffix(".sql") == initial_schema.SCHEMA_SQL
    digest = hashlib.sha256(initial_schema.SCHEMA_SQL.read_bytes()).hexdigest()
    assert digest == "cc12dfe5c8ad9031ba92a3a923b7e560d634ca8f5ca458ba61bd7e594110458a"


@pytest.mark.parametrize("extensions_available", [True, False])
def test_upgrade_uses_snapshot_and_frozen_transforms(monkeypatch, extensions_available):
    executed = []
    monkeypatch.setattr(initial_schema, "_run_sql", executed.append)
    monkeypatch.setattr(initial_schema, "_has_extension", lambda _: extensions_available)

    initial_schema.upgrade()

    expected = initial_schema.SCHEMA_SQL.read_text(encoding="utf-8")
    if not extensions_available:
        expected = initial_schema._strip_crypto(
            initial_schema._strip_unaccent(initial_schema._strip_gis(expected))
        )
    assert executed[-1] == initial_schema._strip_cron(expected)
    assert "CREATE TABLE vessel (" in executed[-1]
    assert ("geometry(Point,4326)" in executed[-1]) is extensions_available


def test_frozen_transforms_preserve_original_validator_behavior():
    validator_spec = importlib.util.spec_from_file_location(
        "validator", MIGRATION.parents[2] / "tools" / "validate_ddl.py"
    )
    assert validator_spec is not None and validator_spec.loader is not None
    validator = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(validator)

    original = initial_schema.SCHEMA_SQL.read_text(encoding="utf-8")
    for migration_transform, validator_transform in (
        (initial_schema._strip_gis, validator.strip_gis),
        (initial_schema._strip_unaccent, validator.strip_unaccent),
        (initial_schema._strip_crypto, validator.strip_crypto),
    ):
        assert migration_transform(original) == validator_transform(original)
