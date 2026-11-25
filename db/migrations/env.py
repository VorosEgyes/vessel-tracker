"""Az Alembic környezet (a `01` – stack-terv §3.2).

**A `DATABASE_URL`-t a környezeti változókból olvassuk** (a `07`
§2.3: a `.env` a `pydantic-settings`-en keresztül jön → **a
migrációkhoz a közvetlen `os.environ` is elég**, és **így az
Alembic nem függ a `duna` csomagtól** → **a `duna/config.py` még
hiányozhat**).

**A szinkron (nem async) motor:** az Alembic a szinkron SQLAlchemy
motort használja → **a `postgresql+asyncpg://` URL-t
`postgresql://`-ra cseréljük** (a `psycopg` driverrel).

**A `pg_cron` és a `postgis` extension:** a `schema-v1.1.sql` a
`CREATE EXTENSION pg_cron`-t tartalmazza → **a custom PostgreSQL
image kell hozzá** (a `07` §3.2) → **a `public` sémában a
`pg_cron` extension-t a `postgres` szerepkör telepíti.**
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# az Alembic konfig betöltése (a `alembic.ini`-ből)
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    """A szinkron DB-URL (a `DATABASE_URL` környezeti változóból).

    **A `postgresql+asyncpg://` -> `postgresql://`** (a szinkron
    Alembic a `psycopg` drivert használja).
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "a DATABASE_URL nincs beállítva! "
            "A példa: postgresql://postgres:postgres@localhost:5432/duna"
        )
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg")
    return url


def run_migrations_offline() -> None:
    """A migrációk SQL-nek kiírása (a `alembic upgrade head --sql`)."""
    context.configure(
        url=_database_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """A migrációk futtatása egy valódi DB-n."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
