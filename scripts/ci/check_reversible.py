#!/usr/bin/env python3
"""A migráció visszafordíthatóságának ellenőrzése (a `07` §8.1 8. lépése).

**A ciklus:**
1. a `just db-migrate` → a séma létrejön;
2. a `just db-migrate-down` → a séma eldobódik (csak az
   `alembic_version` marad);
3. a `just db-migrate` újra → a séma újraépül.

**A `mmsi`/`mmsi` ellenőrzés:** a táblák száma a ciklus előtt és
után **azonos** kell lennie → **a migráció determinisztikus**.

**A `DATABASE_URL` környezeti változó kell** (a CI-ben a
PostgreSQL service adja, a `07` §4.2) → **a `DATABASE_URL` hiányában
a `just test-reversible` kihagyja a lépést** (nem hiba).

**A `psql` a `PGPGBIN` env-variából, a PATH-ból vagy a venv
`pgserver`-éből kerül** (a `db/tools/validate_ddl.py` `find_psql()`
mintája).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def find_psql() -> str | None:
    """A `psql` bináris megkeresése (a `validate_ddl.py` mintája)."""
    pgbins = os.environ.get("PGPGBIN")
    if pgbins:
        candidate = pathlib.Path(pgbins) / "psql"
        if candidate.exists():
            return str(candidate)
    found = shutil.which("psql")
    if found:
        return found
    try:
        import pgserver

        candidate = pathlib.Path(pgserver.__file__).parent / "pginstall" / "bin" / "psql"
        if candidate.exists():
            return str(candidate)
    except ModuleNotFoundError:
        pass
    return None


def psql_env() -> dict[str, str]:
    """A `psql` környezete (a `PGHOST` a `DATABASE_URL`-ből)."""
    env = dict(os.environ)
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "postgres")
    url = os.environ.get("DATABASE_URL", "")
    if "host=" in url:
        env["PGHOST"] = url.split("host=")[1].split("&")[0]
    if "port=" in url:
        env["PGPORT"] = url.split("port=")[1].split("&")[0]
    return env


def table_count(psql: str, env: dict[str, str]) -> int:
    """A `public` sémában lévő táblák száma (a `BASE TABLE` típus)."""
    result = subprocess.run(
        [
            psql,
            "-t",
            "-A",
            "-c",
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE';",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"a tabla szamanak lekérdezese nem sikerult: {result.stderr[-500:]}")
    return int(result.stdout.strip())


def run_just(recipe: str) -> None:
    """A `just` recept futtatása (a `db-migrate` / a `db-migrate-down`)."""
    just = shutil.which("just") or "/opt/data/bin/just"
    result = subprocess.run(
        [just, recipe],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"a `just {recipe}` nem sikerult (exit {result.returncode}):\n"
            f"{result.stdout[-1500:]}\n{result.stderr[-1500:]}"
        )


def main() -> int:
    """A ciklus futtatása és az ellenőrzés."""
    if not os.environ.get("DATABASE_URL"):
        print("a DATABASE_URL nincs beállítva -> a visszafordítás-ellenőrzés kihagyva")
        return 0

    psql = find_psql()
    if psql is None:
        print("a psql nem található -> a visszafordítás-ellenőrzés kihagyva")
        return 0

    env = psql_env()

    print("--- 1. a `just db-migrate` (a séma létrejön) ---")
    run_just("db-migrate")
    before = table_count(psql, env)
    print(f"    a táblák száma: {before}")
    if before < 2:
        print(f"HIBA: a séma nem jött létre (csak {before} tábla)")
        return 1

    print("--- 2. a `just db-migrate-down` (a séma eldobódik) ---")
    run_just("db-migrate-down")
    after_down = table_count(psql, env)
    print(f"    a táblák száma: {after_down}")
    if after_down >= before:
        print(f"HIBA: a visszafordítás nem dobta el a sémát ({after_down} >= {before})")
        return 1

    print("--- 3. a `just db-migrate` újra (a séma újraépül) ---")
    run_just("db-migrate")
    after_up = table_count(psql, env)
    print(f"    a táblák száma: {after_up}")
    if after_up != before:
        print(f"HIBA: a séma nem azonos (előtte {before}, utána {after_up})")
        return 1

    print(f"OK: a migráció visszafordítható ({before} tábla -> {after_down} -> {after_up})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
