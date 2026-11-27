#!/usr/bin/env python3
"""A frontend statikus buildje a valódi API-val (a 05 §5.2).

**A `hajok.astro` a `getStaticPaths`-ben TÖLTI A KATALOGUST** ->
**a buildhez futnia kell egy API-nak** -> **a `API_BASE_URL` a build
kornyezeti valtozoja** (a `05` §5.1).

**A `API_BASE_URL` nelkul a build elbukik:**
```
API_BASE_URL is required to build the catalogue
```
-> **a `just build-frontend` a `DATABASE_URL`-t es a `PUBLIC_API_BASE_URL`-t
is beallitja** -> **a build a valodi katalogust generalja.**

**A LEPESEK:**
1. **a `pgserver` inditasa** (a dev-fugosegek kozott van) -> **a DB**;
2. **a migracio** (`alembic upgrade head`) -> **a sema**;
3. **az API inditasa** (`uvicorn duna.main:app`) egy porton ->
   **a `getStaticPaths` ehhez csatlakozik**;
4. **a `/health` megvarasa** -> **az API kesz**;
5. **a `pnpm build`** az `API_BASE_URL`-lel;
6. **az API leallitasa** (a `finally` blokkban).

**A `PUBLIC_API_BASE_URL`** (a `05` §5.1) -> **a BÖNGÉSZŐ hívza az
API-t** -> **a buildben a localhost nem elerheto a kliensbol** ->
**a buildkor a nyilvanos URL kell** (a `05` szerint) -> **ha nincs
megadva, a `http://127.0.0.1:<port>` (a dev-modeszer) -> **a
productionben a `PUBLIC_API_BASE_URL` env var megadandó.**

Hasznalat:
    uv run python scripts/ci/build_frontend.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "apps" / "web"


def _start_pgserver() -> str:
    """Egy ideiglenes PostgreSQL a `pgserver`-rel -> **a
    `DATABASE_URL`**.

    **A `pgdata` egy temp dirben** -> **a `cleanup_mode="stop"`
    leallitja a szervert a kilepeskor.**
    """
    import tempfile

    import pgserver

    pgdata = pathlib.Path(tempfile.mkdtemp(prefix="vt-web-pgdata-"))
    server = pgserver.get_server(str(pgdata), cleanup_mode="stop")
    url = server.get_uri()
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def _run_migrations() -> None:
    """**Az Alembic `upgrade head`** (a `db/migrations/`).

    **A `DATABASE_URL` env-ben van** -> **a `db/migrations/env.py` azt
    hasznalja** (a `+asyncpg` -> `+psycopg` konverzioval).
    """
    import alembic.command
    import alembic.config

    ini = REPO_ROOT / "alembic.ini"
    config = alembic.config.Config(str(ini))
    cwd = pathlib.Path.cwd()
    try:
        os.chdir(ini.parent)
        alembic.command.upgrade(config, "head")
    finally:
        os.chdir(cwd)


def _free_port() -> int:
    """Egy szabad TCP port (a `socket`-hez)."""
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout: float = 60.0) -> None:
    """**A `/health` megvarasa** -> **az API kesz.**

    **A hiba nem nyeli el a build hibajat** -> **a `timeout` utan
    `RuntimeError`** -> **a build elbukik, nem egy rossz oldallal
    megy tovább.**
    """
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError) as exc:
            last = exc
        time.sleep(0.5)
    raise RuntimeError(f"az API nem indult el ({base_url}/health): {last}")


def main() -> int:
    """A frontend buildje a valódi API-val."""
    pnpm = shutil.which("pnpm")
    if not pnpm:
        print("a pnpm nem talalhato -> a frontend build kihagyva")
        return 0

    if not os.environ.get("DATABASE_URL"):
        try:
            url = _start_pgserver()
        except Exception as exc:  # pragma: no cover
            print(f"a pgserver nem indithato ({exc}) -> a frontend build kihagyva")
            return 0
        os.environ["DATABASE_URL"] = url
        print("a ideiglenes PostgreSQL elindult")

    _run_migrations()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    # **a `PUBLIC_API_BASE_URL`** (a 05 §5.1) -> **a bongeszo altal
    # latott URL** -> **ha nincs megadva, a dev-modeszer** (a build
    # a localhostot hasznalja)
    public_url = os.environ.get("PUBLIC_API_BASE_URL", base_url)

    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "duna.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO_ROOT),
        env=dict(os.environ),
    )
    try:
        _wait_for_health(base_url)
        print(f"az API fut: {base_url}")

        build_env = dict(os.environ)
        build_env["API_BASE_URL"] = base_url
        build_env["PUBLIC_API_BASE_URL"] = public_url

        proc = subprocess.run(
            [pnpm, "--filter", "./apps/web", "build"],
            cwd=str(REPO_ROOT),
            env=build_env,
        )
        return proc.returncode
    finally:
        api.send_signal(signal.SIGTERM)
        try:
            api.wait(timeout=15)
        except subprocess.TimeoutExpired:  # pragma: no cover
            api.kill()


if __name__ == "__main__":
    raise SystemExit(main())
