#!/usr/bin/env python3
"""A fejlesztői előnézet a NAS-on (a frontend + az API együtt).

**A PROBLEMÁK, amit megold:**
1. **a frontendnek kell egy API** (a `getStaticPaths` a buildkor,
   a `fetch` a böngészőben) -> **a `uvicorn` itt fut**;
2. **a DB-nek futnia kell** -> **a `pgserver` itt indul**;
3. **a hajóadatnak kell lennie** -> **a mérési SQLite betöltve**
   (a `load_measurement.py`);
4. **a CORS** -> **a web originnek benne kell lennie** (a
   `CORS_ORIGINS` env).

**A PORTOK:**
- a **frontend** (a statikus `dist/`) a `0.0.0.0:8080`-on ->
  **a Mac: `http://<a-NAS-IP>:8080/hu/duna/hajok`**;
- az **API** a `0.0.0.0:8000`-on ->
  **a `PUBLIC_API_BASE_URL=http://<a-NAS-IP>:8000`** (a buildkor).

**A `PUBLIC_API_BASE_URL` a buildkor kerul a HTML-be** (`data-api-base`)
-> **a statikus `dist/`-et a NAS-IP-vel kell buildelni** ->
**a `--public-url` opcio ezt adja.**

Hasznalat:
    uv run python scripts/dev/preview.py --public-url http://192.168.0.207:8000
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import pathlib
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WEB_DIST = REPO_ROOT / "apps" / "web" / "dist"
DEFAULT_DB_DIR = pathlib.Path("/opt/data/martin/work/ais-data")

# **a `just db-seed`/a `db-migrate` utan a `vessel` tabla a
# `load_measurement.py`-vel toltodik fel**


def _start_pgserver() -> str:
    """Egy ideiglenes PostgreSQL a `pgserver`-rel -> **a
    `DATABASE_URL`**.

    **A `pgdata` a `tempfile`ben** -> **a `cleanup_mode="stop"`
    leallitja a szervert a kilepeskor.**
    """
    import tempfile

    import pgserver

    pgdata = pathlib.Path(tempfile.mkdtemp(prefix="vt-preview-pgdata-"))
    server = pgserver.get_server(str(pgdata), cleanup_mode="stop")
    url = server.get_uri()
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def _run_migrations() -> None:
    """**Az Alembic `upgrade head`** (a `db/migrations/`)."""
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


def _load_measurement(url: str) -> None:
    """**A mérési adat betöltése** (a `load_measurement.py`)."""
    candidates = sorted(DEFAULT_DB_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("nincs mérési adat -> a katalógus üres lesz")
        return
    script = REPO_ROOT / "scripts" / "dev" / "load_measurement.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--db", str(candidates[0])],
        cwd=str(REPO_ROOT),
        env=dict(os.environ),
        capture_output=True,
        text=True,
    )
    print(proc.stdout.strip()[-300:])
    if proc.returncode != 0:
        print(f"a betöltés nem sikerült: {proc.stderr[-500:]}")


def _check_port_free(port: int) -> None:
    """**A port szabad-e?** -> **egy vilagos hiba**, ha nem.

    **A `0.0.0.0`-on figyelünk** -> **a localhoston ellenorzés
    elég** (a `SO_REUSEADDR` nélküli bind elbukik, ha a port
    foglalt).
    """
    import socket

    with socket.socket() as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError as exc:
            raise SystemExit(
                f"HIBA: a {port}. port foglalt ({exc}).\n"
                f"  a megoldas: `--api-port 8001` (vagy egy masik szabad port)"
            ) from exc


def _free_port() -> int:
    """Egy szabad TCP port."""
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout: float = 60.0) -> None:
    """**A `/health` megvarasa** -> **az API kesz.**"""
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


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """A statikus kiszolgalo (a naplo nelkul)."""

    def log_message(self, *args: object) -> None:
        """**A naplo kikapcsolva** (a `preview` nem zajos)."""

    def end_headers(self) -> None:
        """**A `no-cache`** -> **a dev ne a gyorsitotarbol szoljon."""
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class _StaticServer(socketserver.ThreadingTCPServer):
    """A statikus szerver (a `dist/` gyokereből)."""

    allow_reuse_address = True
    daemon_threads = True


def _serve_static(directory: pathlib.Path, port: int) -> _StaticServer:
    """**A statikus `dist/` kiszolgalasa** a `0.0.0.0:port`-on.

    **A port foglaltsaga** -> **egy VILAGOS hiba** (a nyers
    `OSError` nem mondja meg, hogy a NAS-on a 8080 a Zigbee2MQTT, a
    8090 a Pi-hole) -> **a `preview.py` a `--web-port` opciot
    javasolja.**
    """
    handler = functools.partial(_QuietHandler, directory=str(directory))
    try:
        return _StaticServer(("0.0.0.0", port), handler)
    except OSError as exc:
        raise SystemExit(
            f"HIBA: a {port}. port foglalt ({exc}).\n"
            f"  a NAS-on a 8080 a Zigbee2MQTT, a 8090 a Pi-hole.\n"
            f"  a megoldas: `--web-port 8931` (vagy egy masik szabad port)"
        ) from exc


def _build_frontend(public_url: str, api_port: int) -> None:
    """**A frontend újraépítése** a helyes `PUBLIC_API_BASE_URL`-lel.

    **A `data-api-base` a buildkor kerul a HTML-be** -> **a NAS-IP-vel
    kell buildelni**, hogy a bongeszo a NAS API-jat hívja.
    """
    pnpm = shutil.which("pnpm")
    if not pnpm:
        print("a pnpm nem található -> a frontend build kihagyva")
        return
    env = dict(os.environ)
    env["API_BASE_URL"] = f"http://127.0.0.1:{api_port}"
    env["PUBLIC_API_BASE_URL"] = public_url
    proc = subprocess.run(
        [pnpm, "--filter", "./apps/web", "build"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    if proc.returncode != 0:
        print("a frontend build elbukott -> a régi dist/ marad")


def main() -> int:
    """Az előnézet."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--public-url",
        help="a böngészőben használt API-cím (a buildkor a HTML-be kerül)",
    )
    ap.add_argument("--api-port", type=int, default=8000)
    # **a 8080 a Zigbee2MQTT, a 8090 a Pi-hole** (a NAS-on) ->
    # **a 8931-et hasznaljuk** (a Hermes dashboard-ja)
    ap.add_argument("--web-port", type=int, default=8931)
    ap.add_argument("--no-build", action="store_true", help="a build kihagyása")
    ap.add_argument("--no-load", action="store_true", help="a betöltés kihagyása")
    args = ap.parse_args()

    # **A PORT ELLENORZESE ELSOBB** (a 07 §3.1: ne maszkoljunk) ->
    # **a migracio (a `psql` subprocessszel) 1-2 percet tart** ->
    # **igy a hiba azonnal jön**
    _check_port_free(args.api_port)
    _check_port_free(args.web_port)

    if not os.environ.get("DATABASE_URL"):
        url = _start_pgserver()
        os.environ["DATABASE_URL"] = url
        print("a PostgreSQL elindult (a pgserver)")
    _run_migrations()

    if not args.no_load:
        _load_measurement(os.environ["DATABASE_URL"])

    api_port = args.api_port
    public_url = args.public_url or f"http://127.0.0.1:{api_port}"
    # **a CORS** -> **a web origin** -> **a `file://` nem, csak a HTTP**
    web_origins = [
        "http://localhost:4321",
        "http://127.0.0.1:4321",
        f"http://localhost:{args.web_port}",
        f"http://127.0.0.1:{args.web_port}",
        f"http://{public_url.replace('http://', '').split(':')[0]}:{args.web_port}",
    ]
    # **A `pydantic-settings` a listát JSON-ként várja** (a vesszővel
    # elválasztott string NEM JSON -> a `SettingsError`) ->
    # **a `CORS_ORIGINS` a JSON lista**
    os.environ["CORS_ORIGINS"] = json.dumps(web_origins)

    # **AZ API ES A STATIKUS SZERVER A `try` BELSEJEN** ->
    # **a hiba eseten a `finally` lezarli mindkettoet** ->
    # **nem marad orphan `uvicorn` a 8000-as porton.**
    api: subprocess.Popen[bytes] | None = None
    static: _StaticServer | None = None
    try:
        # **A PORT ELLENORZESE** (a `uvicorn` elbukna egy nyers
        # traceback-kel) -> **egy vilagos hiba**
        _check_port_free(api_port)
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "duna.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(api_port),
                "--log-level",
                "warning",
            ],
            cwd=str(REPO_ROOT),
            env=dict(os.environ),
        )
        # **A `/health` MEGVARASA** -> **az API kesz** ->
        # **UTANA jon a build** (a `getStaticPaths` a valodi API-t
        # hívja, a 05 §5.2) -> **a build a betolt katalogust generalja**
        _wait_for_health(f"http://127.0.0.1:{api_port}")
        print("az API kesz")

        if not args.no_build:
            _build_frontend(public_url, api_port)

        if not WEB_DIST.exists():
            print(f"HIBA: nincs frontend build: {WEB_DIST} (a `just build-frontend`)")
            return 2

        static = _serve_static(WEB_DIST, args.web_port)
        threading.Thread(target=static.serve_forever, daemon=True).start()

        _wait_for_health(f"http://127.0.0.1:{api_port}")
        print()
        print("=== AZ ELŐNÉZET ===")
        print(f"  a frontend:  http://127.0.0.1:{args.web_port}/hu/duna/hajok")
        print(f"  az API:      http://127.0.0.1:{api_port}/api/v1/vessels")
        print(
            f"  a böngésző:  {public_url.replace(str(api_port), str(args.web_port))}/hu/duna/hajok"
        )
        print()
        print(f"  (a NAS IP-jével: http://<a-NAS-IP>:{args.web_port}/hu/duna/hajok)")
        print("  Ctrl-C a leállításhoz")
        print()
        while True:
            time.sleep(1)
            if api is not None and api.poll() is not None:
                print("az API leállt")
                return 1
    except KeyboardInterrupt:
        print()
        print("leállítás...")
        return 0
    finally:
        if static is not None:
            static.shutdown()
        if api is not None:
            api.send_signal(signal.SIGTERM)
            try:
                api.wait(timeout=15)
            except subprocess.TimeoutExpired:
                api.kill()


if __name__ == "__main__":
    raise SystemExit(main())
