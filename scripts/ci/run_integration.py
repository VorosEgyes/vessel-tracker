#!/usr/bin/env python3
"""Az integrációs tesztek futtatása a valódi PostgreSQL-lel.

**A `DATABASE_URL` nélkül a `pgserver` indít egy ideiglenes
PostgreSQL-t** -> **a `just check` DB nélkül is zold marad** ->
**a 70%-os alkalmazasreteg-coverage-kapu is merhető** (a 08 §8.1).

**A `pgserver` a dev-függőségek között van** (a `just setup` ->
`uv sync --extra dev`) -> **a `just ddl-validate` is ezt hasalja**
(a `db/tools/validate_ddl.py`).

**A `DATABASE_URL` MEGADVA** (a CI-ben a PostgreSQL service) ->
**azt hasznaljuk** -> **a service-en fut az is** (a CI-ben nincs
pgserver, de a service megvan).

**Az integrációs tesztek a `skipif` miatt kihagyjak magukat**, ha
nincs DB -> **de itt MINDIG van DB** -> **a gate mindig ervenyes.**

Hasznalat:
    uv run python scripts/ci/run_integration.py <pytest-argumentumok...>
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys


def _start_pgserver() -> str:
    """Egy ideiglenes PostgreSQL a `pgserver`-rel -> **a
    `DATABASE_URL`**.

    **A `pgdata` egy temp dirben** -> **a `cleanup_mode="stop"`
    leallitja a szervert a kilepeskor** -> **nem hagy hatterben futo
    processzt.**
    """
    import tempfile

    import pgserver

    pgdata = pathlib.Path(tempfile.mkdtemp(prefix="vt-pgdata-"))
    server = pgserver.get_server(str(pgdata), cleanup_mode="stop")

    # **a socket konyvtara** -> **a `postgresql+asyncpg://user@/db?host=...`
    url = server.get_uri()
    # **a `pgserver` a `postgresql://` formatumot adja** -> **a
    # `+asyncpg` driver kell** (a `duna/db/session.py` azt hasznalja)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def _run_migrations() -> None:
    """**A migráció futtatása** a `DATABASE_URL`-en.

    **A `pgserver` egy ÜRES DB** -> **a teszteknek kell a séma** ->
    **az Alembic `upgrade head`** (a `db/migrations/`) -> **a `just
    db-migrate` ugyanezt csinalja** (a `07` §8.1).

    **A `DATABASE_URL` a `postgresql+asyncpg://` formaban van** -> **a
    `db/migrations/env.py` atalakitja `+psycopg`-ra** -> **a migracio
    a `psql`-lel fut** (a `env.py` a `PGHOST`/`PGPORT` env-et allitja
    be) -> **a `pgserver` socketen elerheto** -> **mukodik.**
    """
    import alembic.command
    import alembic.config

    ini = pathlib.Path(__file__).resolve().parents[2] / "alembic.ini"
    config = alembic.config.Config(str(ini))
    # **a `script_location`-t a `alembic.ini` tartalmazza** (a repo
    # gyokereben van) -> **a `chdir` a repo gyokere**
    cwd = pathlib.Path.cwd()
    try:
        import os

        os.chdir(ini.parent)
        alembic.command.upgrade(config, "head")
    except Exception as exc:  # pragma: no cover
        print(f"a migracio nem futott ({exc}) -> a tesztek elbukhatnak")
    finally:
        import os

        os.chdir(cwd)


def main() -> int:
    """A `pytest` futtatása a DB-vel."""
    if not os.environ.get("DATABASE_URL"):
        try:
            url = _start_pgserver()
        except Exception as exc:  # pragma: no cover
            print(
                f"a pgserver nem indithato ({exc}) -> a DATABASE_URL nincs "
                "beallitva -> az integracios tesztek kihagyva"
            )
            return 0
        os.environ["DATABASE_URL"] = url
        print(f"a ideiglenes PostgreSQL: {url.split('@')[-1]}")
        _run_migrations()

    # **a `pytest_or_skip.py` wrapper** -> **csak a "nem gyujtott
    # teszt" esetet nyeli el** -> **a valodi hibakodok atmegyenek**
    wrapper = pathlib.Path(__file__).resolve().parent / "pytest_or_skip.py"
    proc = subprocess.run([sys.executable, str(wrapper), *sys.argv[1:]])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
