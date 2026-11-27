"""Az első séma; a revízióhoz tartozó SQL-pillanatképet futtatja."""

from __future__ import annotations

import pathlib
import re

import sqlalchemy as sa
from alembic import op

# **Az Alembic kötelező revízió-változói** (a `07` §8.1 8. lépése:
# a migráció visszafordíthatóság)
revision = "20241124_0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = pathlib.Path(__file__).with_suffix(".sql")


def _run_sql(sql: str) -> None:
    """A SQL futtatása a `psql` subprocessként.

    **Miért nem az `op.execute`:** a séma **többszörös statement**
    (a `CREATE TABLE` + az `INSERT`-ek) → **a `psycopg` a `simple
    query` protokollban nem engedi** → **a `psql` kezeli a
    statement-eket** (a `db/tools/validate_ddl.py` mintája).

    **A `psql` elérhetősége:** a `PGPGBIN` env-variából, a PATH-ból
    vagy a venv `pgserver` példányából (a `find_psql()`-hez hasonló
    logika).
    """
    import os
    import subprocess

    psql = _psql()
    if not psql:
        raise RuntimeError("a psql nem talalhato (a PGPGBIN / a PATH / a pgserver)")

    env = dict(os.environ)
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "postgres")

    # **A `psql` a `PGHOST`/`PGPORT` env-variánsokat használja** (nem a
    # `DATABASE_URL`-t) → **a DB URL-ből ki kell nyerni őket**
    _apply_db_url_to_env(env)

    result = subprocess.run(
        [psql, "-v", "ON_ERROR_STOP=1", "-f", "-"],
        input=sql,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "a schema futtatasa nem sikerult:\n"
            f"--- a stderr (a vege) ---\n{result.stderr[-2000:]}\n"
            f"--- a stdout (a vege) ---\n{result.stdout[-1000:]}"
        )


def _apply_db_url_to_env(env: dict[str, str]) -> None:
    """A `DATABASE_URL` -> a `PGHOST`/`PGPORT` env-variánsok.

    **A `psql` nem a `DATABASE_URL`-t olvassa** → **a hosztot és a
    portot ki kell nyerni.**

    **Két forma:**
    - a socketes: `postgresql+psycopg://user@/db?host=/socket/dir` →
      a `PGHOST` a socket könyvtára;
    - a TCP-s (a CI-ben): `postgresql+psycopg://user:pass@host:port/db`
      → **a `PGHOST` a hoszt, a `PGPORT` a port.**

    **A `psycopg` (az `env.py`) a URL-t használja** → **az SQLAlchemy
    kapcsolat a TCP-n megy, de a `psql` a socketen keresne** → **ez
    a kiegyeztetés kell.**
    """
    from sqlalchemy.engine import make_url

    url = env.get("DATABASE_URL", "")
    if not url:
        return

    parsed = make_url(url)
    host = parsed.query.get("host", parsed.host)
    port = parsed.query.get("port", parsed.port)
    if isinstance(host, tuple) or isinstance(port, tuple):
        raise ValueError("a DATABASE_URL tobb host vagy port erteket tartalmaz")
    if host:
        env["PGHOST"] = host
    if port is not None:
        env["PGPORT"] = str(port)
    if parsed.username:
        env["PGUSER"] = parsed.username
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    if parsed.database:
        env["PGDATABASE"] = parsed.database


def _strip_gis(sql: str) -> str:
    sql = re.sub(r"geometry\s*\(\s*\w+\s*,\s*4326\s*\)", "text", sql)
    sql = re.sub(r"geometry\s*\(\s*\w+\s*\)", "text", sql)
    return re.sub(
        r"CREATE INDEX (\w+) ON (\w+) USING GIST \((\w+)\);", r"CREATE INDEX \1 ON \2 (\3);", sql
    )


def _strip_unaccent(sql: str) -> str:
    sql = re.sub(r"lower\(unaccent\(([^)]+)\)\)", r"lower(\1)", sql)
    sql = re.sub(r"unaccent\(([^)]+)\)", r"\1", sql)
    sql = re.sub(r"\s+gin_trgm_ops\)", ")", sql)
    return re.sub(r"USING GIN\s*\(", "USING BTREE (", sql)


def _strip_crypto(sql: str) -> str:
    sql = sql.replace("digest(", "md5(")
    sql = sql.replace(",\n            'sha256'\n        )", "\n        )")
    return sql.replace(", 'sha256')", ")")


def _psql() -> str | None:
    """A `psql` bináris (a `PGPGBIN` env-variából, a PATH-ból vagy a
    venv `pgserver`-éből — a `db/tools/validate_ddl.py` `find_psql()`
    mintája)."""
    import os
    import shutil

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


def _has_extension(name: str) -> bool:
    """Van-e a megadott extension a DB-ben?

    **A CI-ben és a productionben a `postgis`, a `unaccent` és a
    `pg_trgm` is megvan** (a `07` §4.2: a PostGIS image; a `unaccent`
    és a `pg_trgm` a `postgresql-contrib` moduljai → **a migráció
    telepíti őket**, ha a superuser megteheti).

    **A fejlesztői `pgserver` DB-ben egyik sem van** → **a
    preprocesszorok kimaradnak** (a `db/tools/validate_ddl.py`
    mintája) → **a migráció ott is fut** (a `07` §8.1 8. lépése).
    """
    import os
    import subprocess

    psql = _psql()
    if not psql:
        return False
    env = dict(os.environ)
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "postgres")
    _apply_db_url_to_env(env)
    result = subprocess.run(
        [psql, "-t", "-A", "-c", f"SELECT count(*) FROM pg_extension WHERE extname='{name}';"],
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode == 0 and result.stdout.strip() not in ("", "0")


def _strip_cron(sql: str) -> str:
    """A `pg_cron` részek kivétele (a `02` §12).

    **A `pg_cron` extension csak a custom PostgreSQL image-ben van**
    (a `07` §3.2) → **a fejlesztői DB-ben (a `pgserver`) nincs**
    → **a migrációnak MINDKETT DB-ben futnia kell** → **a
    `pg_cron` hívások kimaradnak, ha nincs extension.**

    **Ugyanaz a preprocesszor, mint a `db/tools/validate_ddl.py`-ban**
    (a `strip_cron`) → **a séma azonos a validátorral.**

    **A `$$ ... $$` (dollar-quoted) stringek miatt NEM lehet `;`-vel
    vágni** → **a `DO $$ ... $$;` blokk (a szerepkör-létrehozás)
    szétbomlana** → **a minta a dollar-quote végéig megy** (a
    `validate_ddl.py` megjegyzése szerint).
    """
    sql = re.sub(
        r"CREATE EXTENSION IF NOT EXISTS pg_cron;",
        "-- (pg_cron kimaradt: nem elerheto a stock PostgreSQL-ben)",
        sql,
    )
    sql = re.sub(
        r"SELECT cron\.schedule\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*\$\$.*?\$\$\s*\);",
        "-- (cron.schedule kimaradt: pg_cron nem elerheto)",
        sql,
        flags=re.S,
    )
    # a dollar-quote parossaga nem tolhat el
    if sql.count("$$") % 2 != 0:
        raise RuntimeError(
            "a dollar-quote paratlan a preprocesszor utan "
            f"({sql.count('$$')} token) — a strip_cron elnyelt egy blokkot."
        )
    return sql


def upgrade() -> None:
    """A séma létrehozása a revízió rögzített DDL-jéből.

    **A `pg_cron` opcionális:** ha az extension nincs telepítve (a
    fejlesztői `pgserver` DB-ben), a `pg_cron` hívások kimaradnak →
    **a migráció minden DB-ben fut** (a `07` §8.1 8. lépése: a
    migráció visszafordíthatóság).
    """
    if not SCHEMA_SQL.exists():
        raise RuntimeError(f"a séma fájlja nem létezik: {SCHEMA_SQL}")
    sql = SCHEMA_SQL.read_text(encoding="utf-8")

    # **A `pg_cron` extension telepítése, ha elérhető** (a custom
    # image-ben van, a `pgserver`-ben nincs) -> **a hiba nem bukhat
    # el a migrációt**
    # **A `pg_cron` extension telepítése** (a custom image-ben van, a
    # fejlesztői `pgserver`-ben nincs) → **a hiba NEM bukhatja el a
    # migrációt** → **a `psql` subprocessként megy** (a saját
    # kapcsolatán) → **a hiba elnyelődik**.
    try:
        _run_sql("CREATE EXTENSION IF NOT EXISTS pg_cron;")
    except RuntimeError:
        print("  a pg_cron extension nem elérhető -> a pg_cron hívások kimaradnak")

    # **A séma TÖBBSZÖRÖS statement** (a `CREATE TABLE` + `INSERT`) →
    # **a `psycopg` ezt a `simple query` protokollban nem engedi** →
    # **a `psql` subprocessként futtatjuk** (a `db/tools/validate_ddl.py`
    # mintájára) → **a `psql` kezeli a statement-eket és a hibákat.**
    # **A szükséges extensionök telepítése** (a superuser megteheti):
    # a `postgis` (a geometria), a `unaccent` (a normalizálás), a
    # `pg_trgm` (a trigram indexek) → **a CI PostGIS image-ében az
    # `postgis` megvan, a másik kettő a contrib modul → **a
    # migráció telepíti őket.**
    for extension in ("postgis", "unaccent", "pg_trgm"):
        try:
            _run_sql(f"CREATE EXTENSION IF NOT EXISTS {extension};")
        except RuntimeError:
            print(f"  a {extension} extension nem telepíthető -> a használata kimarad")

    # **A GIS csak akkor marad, ha van PostGIS** (a CI-ben és a
    # productionben van; a fejlesztői `pgserver`-ben nincs)
    if not _has_extension("postgis"):
        print("  a postgis extension nem elérhető -> a GIS-részek text-re cserélve")
        sql = _strip_gis(sql)
    if not _has_extension("unaccent"):
        print("  az unaccent extension nem elérhető -> a normalizálás kimarad")
        sql = _strip_unaccent(sql)
    if not _has_extension("pgcrypto"):
        print("  a pgcrypto extension nem elérhető -> a hash kiszámítása kimarad")
        sql = _strip_crypto(sql)

    _run_sql(_strip_cron(sql))


def downgrade() -> None:
    """A séma eldobása (a teljes visszafordítás).

    **A `public` séma eldobása az `alembic_version` táblát is törli**
    → **az Alembic ezután nem tudja törölni a verziósort** → **a
    `DROP SCHEMA` UTÁN újra kell létrehozni az `alembic_version`
    táblát** (a `alembic_version` a `public` sémában van) → **így az
    Alembic szabályos `DELETE` + `DROP TABLE` lépései működnek.**

    **A visszafordítás után a séma üres** → **a `just db-migrate`
    újra felépítheti** (a `07` §8.1 8. lépése: a migráció
    visszafordíthatóság).
    """
    op.execute(sa.text("DROP SCHEMA public CASCADE"))
    op.execute(sa.text("CREATE SCHEMA public"))
    op.execute(sa.text("GRANT ALL ON SCHEMA public TO postgres"))
    # **Az `alembic_version` újra, a sorral** (a `DROP SCHEMA` törölte)
    # -> **az Alembic a `downgrade` UTÁN törli a sort** (a `DELETE`) ->
    # **a sornak léteznie kell** -> **visszaillesztjük** -> **a `DELETE`
    # egy sort talál** -> **a downgrade sikeres.**
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
    )
    op.execute(sa.text(f"INSERT INTO alembic_version (version_num) VALUES ('{revision}')"))
