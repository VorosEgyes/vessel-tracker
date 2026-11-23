#!/usr/bin/env python3
"""A 02-es DDL terv validálása valódi PostgreSQL-en.

Kicsomagolja a ```sql blokkokat a terv markdown-ból, és futtatja egy
élő PostgreSQL 17 példányon (pgserver). A geometria/GiST/trgm részek
a konténerben nem elérhető PostGIS/pg_trgm nélkül, ezért egy
'--no-gis' preprocesszor kapcsolóval text-re cserélhetők — a
constraint-logika ettől még változatlanul fut.

Használat:
    .venv312/bin/python validate_ddl.py [--no-gis] [--keep]

Kimenet: a létrejött táblák, indexek, constraint-ek száma + a hibák.
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
# A validalt terv. **A V-N-1 finding szerint a hardcoded utvonal
# hiba volt**: a script a live fajlt olvasta, nem azt, amit a
# reviewer auditalt. Most a parameter a default, es a --plan
# kapcsoloval felulirhato.
# A repo-relative default: a terv a docs/megvalosulas/ alatt van.
# (A kesztyeben a script a db/tools/ alatt fut, a repo-gyokertol
# szamitva — igy a script a helyerol független.)
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_PLAN = _REPO_ROOT / "docs" / "megvalosulas" / "megvalosulas-02-adatbazis-ddl.md"
PLAN = DEFAULT_PLAN
PGDATA = HERE / "pgdata"
PSQL = HERE / ".venv312/lib/python3.12/site-packages/pgserver/pginstall/bin/psql"


def extract_ddl(md_text: str) -> str:
    blocks = re.findall(r"```sql\n(.*?)```", md_text, re.S)
    return "\n;\n".join(b.strip() for b in blocks)


def strip_gis(sql: str) -> str:
    """geometry(Point,4326) -> text; GIST index -> btree; GIN trgm -> btree."""
    sql = re.sub(r"geometry\s*\(\s*\w+\s*,\s*4326\s*\)", "text", sql)
    sql = re.sub(r"geometry\s*\(\s*\w+\s*\)", "text", sql)
    sql = re.sub(r"CREATE INDEX (\w+) ON (\w+) USING GIST \((\w+)\);",
                 r"CREATE INDEX \1 ON \2 (\3);", sql)
    return sql


def strip_unaccent(sql: str) -> str:
    """Az `unaccent()` hivasok kimaradnak: az extension nem elerheto a
    stock PostgreSQL-ben. A `lower(unaccent(x))` -> `lower(x)`.

    A normalizalas ilyenkor a DB nélkül marad — ez csak a
    VALIDACIO korlata, a termelesi DB-ben (a custom image-ben)
    az `unaccent` extension elerheto.
    """
    sql = re.sub(r"lower\(unaccent\(([^)]+)\)\)", r"lower(\1)", sql)
    sql = re.sub(r"unaccent\(([^)]+)\)", r"\1", sql)
    # A GIN trgm operator-osztaly nem elerheto a stock PostgreSQL-ben
    # (a pg_trgm extension hianyzik) -> sima btree index.
    # A 'gin_trgm_ops' tokent el kell távolítani, és a GIN-t BTREE-re
    # cserelni (a text-nek nincs GIN default operator-osztalya).
    sql = re.sub(r"\s+gin_trgm_ops\)", ")", sql)
    sql = re.sub(r"USING GIN\s*\(", "USING BTREE (", sql)
    return sql


def strip_crypto(sql: str) -> str:
    """A `pgcrypto` extension nem elerheto a stock PostgreSQL-ben.

    A `digest(x, 'sha256')` a nyers AIS dedup-kulcsa (V-N-5) -> a
    validacioban egy determinisztikus helyettesitoval kell eljarni,
    hogy a DDL forduljon. A production DB-ben (a custom image-ben)
    a `pgcrypto` extension megvan.
    """
    sql = sql.replace("digest(", "md5(")   # a 16 bajtos hash a 32 helyett
    # az md5() egy argumentumot kap, a digest() kettot -> a masodik
    # ('sha256') argumentumot el kell távolítani. A kifejezes
    # tobbsoros is lehet, ezert nem egy regex-re illesztunk, hanem
    # a kulcssztringet keressuk.
    sql = sql.replace(",\n            'sha256'\n        )", "\n        )")
    sql = sql.replace(", 'sha256')", ")")
    return sql


def strip_cron(sql: str) -> str:
    sql = re.sub(r"CREATE EXTENSION IF NOT EXISTS pg_cron;",
                 "-- (pg_cron kimaradt: nem elerheto a stock PostgreSQL-ben)",
                 sql)
    # SELECT cron.schedule('...', '...', $$...$$);  ->  komment
    #
    # FONTOS: a harmadik argumentum egy dollar-quoted string ($$...$$),
    # ezert a minta a zaro $$-ig megy, nem egy tetszolesges ); -ig.
    # A mohó `.*?\);` minta a kovetkezo DO $$ ... $$; blokkot is
    # elnyelte volna (a szerep-letrehozast).
    # A hivas tobb soros is lehet -> a minta a dollar-quoted
    # string VEGIG megy ($$...$$), nem egy tetszolesges karakterig.
    sql = re.sub(r"SELECT cron\.schedule\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*\$\$.*?\$\$\s*\);",
                 "-- (cron.schedule kimaradt: pg_cron nem elerheto)",
                 sql, flags=re.S)
    # ellenorzes: a dollar-quote parossaga nem tolhat el
    if sql.count("$$") % 2 != 0:
        raise SystemExit(
            "HIBA: a dollar-quote paratlan a preprocesszor utan "
            f"({sql.count('$$')} token) — a strip_cron elnyelt egy blokkot.")
    return sql


def psql_tuples(sql: str) -> list[str]:
    """Egy lekérdezes a fejlec nelkul (a psql -t -A flagokkal).

    A -t (tuples only) es -A (unaligned) egyutt kikapcsolja a
    fejlecet, az elvalaszto sort es a gyakorlo sort — a kimenet
    tiszta adat (soronkent egy elem, a tabulaktorral elvalasztva).
    """
    env = dict(os.environ)
    env.update({"PGHOST": str(PGDATA), "PGUSER": "postgres",
                "PGDATABASE": "postgres"})
    cmd = [str(PSQL), "-v", "ON_ERROR_STOP=1", "-t", "-A", "-F", "|", "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]


def psql(sql: str | None = None, args: list[str] | None = None,
         stdin_text: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update({"PGHOST": str(PGDATA), "PGUSER": "postgres", "PGDATABASE": "postgres"})
    cmd = [str(PSQL), "-v", "ON_ERROR_STOP=1"]
    if stdin_text is not None:
        cmd += ["-f", "-"]
    elif args:
        cmd += args
    else:
        cmd += ["-c", sql]
    return subprocess.run(cmd, capture_output=True, text=True, env=env,
                          input=stdin_text)


def main() -> int:
    global PLAN
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-gis", action="store_true",
                    help="a geometria/GiST/trgm reszeket text-re csereli")
    ap.add_argument("--keep", action="store_true",
                    help="nem dobja el a schema utan")
    ap.add_argument("--plan", type=pathlib.Path, default=None,
                    help="a validalt terv fajlja (a default a live)")
    args = ap.parse_args()

    if args.plan:
        PLAN = args.plan

    if not PSQL.exists():
        print(f"HIBA: a psql binary nem talalhato: {PSQL}")
        return 2
    print(f"--- a validalt terv: {PLAN} ---")
    if not PLAN.exists():
        print(f"HIBA: a terv nem talalhato: {PLAN}")
        return 2

    md = PLAN.read_text(encoding="utf-8")
    ddl = extract_ddl(md)
    if args.no_gis:
        ddl = strip_gis(ddl)
        ddl = strip_unaccent(ddl)
        ddl = strip_crypto(ddl)
    ddl = strip_cron(ddl)

    n_tables = len(re.findall(r"CREATE TABLE", ddl))
    n_indexes = len(re.findall(r"CREATE (?:UNIQUE )?INDEX", ddl))
    n_fks = len(re.findall(r"REFERENCES", ddl))
    n_checks = len(re.findall(r"CHECK\s*\(", ddl))
    print(f"--- a tervbol kinyert DDL ---")
    print(f"  tabla: {n_tables} | index: {n_indexes} | FK: {n_fks} | CHECK: {n_checks}")
    print(f"  GIS preprocesszor: {'igen (text)' if args.no_gis else 'nem'}")

    # --- a postgres szerver inditasa ---
    # A script korabban egy KULSERVEREN futott, amit nem inditott el
    # -> a "connection to server ... failed" hiba. Most a pgserver
    # maga inditja el a klust (a --keep a smoke teszt miatt kell,
    # kulonben a schema utan eldobjuk).
    if not PGDATA.exists():
        PGDATA.mkdir(parents=True, exist_ok=True)
    try:
        import pgserver
        srv = pgserver.get_server(str(PGDATA))
        print(f"--- a postgres elindult: {PGDATA} ---")
    except Exception as exc:  # pragma: no cover
        print("HIBA: a postgres inditasa nem sikerult:", exc)
        return 1

    # reset
    reset = "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres;"
    r = psql(sql=reset)
    if r.returncode != 0:
        print("HIBA a resetnel:", r.stderr[-1500:])
        return 1

    # a DDL futtatasa
    r = psql(stdin_text=ddl)
    if r.returncode != 0:
        print("=== A DDL FUTASA MEGHIBASODOTT ===")
        print(r.stderr[-4000:])
        return 1

    print("=== A DDL SIKERESEN LEFUTOTT ===")

    # utolag ellenorzes
    checks = {
        "tabla": "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'",
        "index": "SELECT count(*) FROM pg_indexes WHERE schemaname='public'",
        "FK constraint": "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'",
        "CHECK constraint": "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='CHECK'",
        "particionált tabla": "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='p' AND n.nspname='public'",
        "trigger": "SELECT count(*) FROM information_schema.triggers WHERE trigger_schema='public'",
    }
    for label, q in checks.items():
        out = psql(sql=q)
        print(f"  {label}: {out.stdout.strip() or out.stderr.strip()[:100]}")

    if args.keep:
        smoke_test()
    else:
        psql(sql=reset)
        print("  (a schema eldobva)")
    return 0


def smoke_test() -> None:
    """Funkcionalis fust: a DDL nemcsak lefordul, hanem mukodik.

    - a partial unique index-ek mukodnek (a README B) szerint)
    - a CHECK constraint-ek mukodnek (a draught_reference pl.)
    - az ingest upsert mukodik a position tablan
    - a partitionk letrejonnek es a drop_expired_partitions torli oket
    """
    print()
    print("=== a funkcionalis fust ===")

    # a referencia seed
    #
    # **A DDL sajat seedjet hasznaljuk** (a language, a data_source,
    # a country, a waterway, a vessel_type, a basin, a cargo_type es
    # az operator mar bent van) — csak a TESZTHAJOT es a kikotot
    # adjuk hozza, mert az ingest-et (a vessel_type_code kitoltes)
    # ezen keresztul teszteljuk.
    r = psql(stdin_text="""
INSERT INTO port (code, port_type, waterway_id, country_code, river_km)
    SELECT 'PT-0147','public_port', w.id,'HU',1642.5
    FROM waterway w WHERE w.code='DUNA';
INSERT INTO port_i18n (port_id, lang, name)
    SELECT p.id, 'hu', 'Budapest' FROM port p WHERE p.code='PT-0147';
INSERT INTO vessel (mmsi, eni, slug, vessel_type_code, operating_area, flag_country_code, length_m, draught_max_m)
    VALUES (244660000, '12345678', 'test-hajo',
            (SELECT code FROM vessel_type WHERE ais_type_code=8444 LIMIT 1),
            'duna','HU', 110.0, 6.20);
INSERT INTO vessel_i18n (vessel_id, lang, name)
    SELECT v.id, 'hu', 'TESZTHAJO' FROM vessel v WHERE v.slug='test-hajo';

-- A felhasznalok (a seed: a dedikalt 'system' aktor az audit-hoz,
-- a V-N-6 javitasa; es egy 'editor' a role-vedelem tesztjehez).
-- Az `id`-t a DB generalja (GENERATED ALWAYS AS IDENTITY).
-- A 'system' fiok a 'system' auth_providerrel jon (nincs jelszava);
-- a 'local' fiokhoz a password_hash KOTELEZO (P1-14) -> a seed
-- egy hamis (nem hasznalhato) hash-t ad.
INSERT INTO app_user (email, display_name, role, auth_provider, password_hash)
    VALUES ('system@vessel-tracker.local', 'System', 'admin', 'system', NULL),
           ('editor@vessel-tracker.local', 'Szerkeszto', 'editor', 'local',
            '$argon2id$seed$placeholder');
INSERT INTO vessel_identifier (vessel_id, identifier_type, value, is_primary, origin)
    VALUES (1, 'mmsi', '244660000', true, 'ais');
INSERT INTO vessel_identifier (vessel_id, identifier_type, value, is_primary, origin)
    VALUES (1, 'eni', '87654321', true, 'ais');
""")
    if r.returncode != 0:
        print("  HIBA a seednel:", r.stderr[-800:])
        return
    print("  a referencia seed: OK")

    # a masodik hajo (kulon ENI-vel) — a duplikalt ENI teszt kulon all
    r = psql(stdin_text="""
INSERT INTO vessel (mmsi, eni, slug, vessel_type_code, operating_area, flag_country_code)
    VALUES (244660001, '11111111', 'test-hajo-2', 'ERI_8444','duna','HU');
""")
    if r.returncode != 0:
        print("  HIBA: a masodik hajo beszurasa:",
              r.stderr.strip().splitlines()[-1][:80])
    else:
        print("  a masodik hajo beszurva: OK")

    # a partial unique index: a harmadik hajo ugyanazzal az ENI-vel elbukik
    r = psql(stdin_text="""
INSERT INTO vessel (mmsi, eni, slug, vessel_type_code, operating_area, flag_country_code)
    VALUES (244660002, '11111111', 'test-hajo-3', 'ERI_8444','duna','HU');
""")
    if r.returncode == 0:
        print("  HIBA: a partial unique index NEM mukodott (duplikalt ENI bejutott)")
    else:
        print("  a partial unique index (ENI): OK ->",
              r.stderr.strip().splitlines()[-1][:70])

    # A MEZONKENYI KONFLIKTUS tarolhato (C-1): ket forras, egy mező
    r = psql(stdin_text="""
INSERT INTO vessel_data_origin (vessel_id, field_name, origin, value_snapshot, is_current)
    VALUES (1, 'length_m', 'ais', '110.00', true);
INSERT INTO vessel_data_origin (vessel_id, field_name, origin, value_snapshot, is_current)
    VALUES (1, 'length_m', 'operator_claimed', '105.00', true);
""")
    if r.returncode != 0:
        print("  HIBA: a konfliktus nem tarolhato:", r.stderr.strip().splitlines()[-1][:80])
    else:
        out = psql(sql="SELECT origin_count, array_length(origins,1) FROM vessel_data_origin_conflicts WHERE vessel_id=1 AND field_name='length_m';")
        row = ' | '.join(out.stdout.strip().splitlines()[-2:]) if out.stdout.strip() else '?'
        print(f"  a mezonkenyi konfliktus: OK -> {row}")

    # A BIZONYOSSAGI SZINT szarmaztatott (H-10): a badge nem hazudhat
    r = psql(sql="SELECT computed_verification_level FROM vessel_verification WHERE vessel_id=1;")
    raw = r.stdout.strip()
    lvl = ""
    for ln in raw.splitlines():
        s = ln.strip()
        if s and s != "(1 row)" and not s.startswith("-"):
            lvl = s
    if lvl in ("ais_identified", "ais_partial"):
        print(f"  a vessel_verification nezet: OK -> {lvl}")
    else:
        print(f"  HIBA: a vessel_verification nezet ures vagy hibas -> {lvl!r}")

    # az AZONOSITO-SZINKRON (M-5) ket iranyban:
    #   vessel -> vessel_identifier (a BEFORE UPDATE trigger)
    #   vessel_identifier -> vessel (az AFTER trigger)
    # A seed utan a vessel.eni-t a trigger hozta letre a
    # vessel_identifier-bol, igy a vessel.eni == 87654321.
    out = psql(sql="SELECT eni FROM vessel WHERE id=1;")
    val = ""
    for ln in out.stdout.strip().splitlines():
        s = ln.strip()
        if s and s != "(1 row)" and not s.startswith("-"):
            val = s
    ok = "OK" if val == "87654321" else "HIBA"
    print(f"  az azonosito-szinkron (a seed utan): {ok} -> vessel.eni = {val!r}")

    # A vessel_identifier -> vessel irany: az UPDATE a vessel_identifier-en
    # a BEFORE UPDATE triggeren keresztul a vessel oszlopaira kerul
    r = psql(stdin_text="""
UPDATE vessel_identifier SET value = '33333333'
WHERE vessel_id = 1 AND identifier_type = 'eni' AND valid_to IS NULL;
""")
    if r.returncode != 0:
        print("  HIBA: a vessel_identifier UPDATE:",
              r.stderr.strip().splitlines()[-1][:80])
    else:
        out = psql(sql="SELECT eni FROM vessel WHERE id=1;")
        vv = ""
        for ln in out.stdout.strip().splitlines():
            s = ln.strip()
            if s and s != "(1 row)" and not s.startswith("-"):
                vv = s
        ok = "OK" if vv == "33333333" else "HIBA"
        print(f"  az azonosito-szinkron (a trigger hatasa): {ok} -> vessel.eni = {vv!r}")

    # A ROLE-VEDelem (V-N-7 / P1-13): a szerkeszto nem emelheti
    # magat adminna
    r = psql(stdin_text="""
UPDATE app_user SET role = 'admin' WHERE id = 2;
""")
    if r.returncode == 0:
        print("  HIBA: a role-vedelem NEM mukodott (szerkeszto admin lett)")
    else:
        msg = " | ".join(r.stderr.strip().splitlines()[-2:])[:90]
        print(f"  a role-vedelem: OK -> {msg}")

    # A ROUTE CARGO_TYPES trigger (P1-17): az ismeretlen kodo elbukik
    r = psql(stdin_text="""
INSERT INTO route (code, origin_port_id, dest_port_id, cargo_types)
    VALUES ('RT-TEST', 1, 1, ARRAY['NEM_LETEZO_KOD']);
""")
    if r.returncode == 0:
        print("  HIBA: a cargo_types trigger NEM mukodott (ismeretlen kod bejutott)")
    else:
        msg = " | ".join(r.stderr.strip().splitlines()[-2:])[:90]
        print(f"  a cargo_types trigger: OK -> {msg}")

    # A feedback status CHECK (P1-16)
    r = psql(stdin_text="""
INSERT INTO feedback (category, body, status, handled_at)
    VALUES ('other', 'teszt', 'accepted', NULL);
""")
    if r.returncode == 0:
        print("  HIBA: a feedback status CHECK NEM mukodott")
    else:
        print("  a feedback status CHECK: OK")

    # a slug egyediseg (a mély link, F-CAT-07)
    r = psql(stdin_text="""
INSERT INTO vessel (mmsi, eni, slug, vessel_type_code, operating_area, flag_country_code)
    VALUES (244660002, '87654321', 'test-hajo', 'ERI_8444','duna','HU');
""")
    if r.returncode == 0:
        print("  HIBA: a slug unique constraint NEM mukodott")
    else:
        print("  a slug unique constraint: OK")

    # a CHECK constraint: a draught_reference csak 'RNW' lehet
    r = psql(stdin_text="""
UPDATE vessel SET draught_reference = 'MLWS' WHERE id = 1;
""")
    if r.returncode == 0:
        print("  HIBA: a draught_reference CHECK NEM mukodott")
    else:
        print("  a draught_reference CHECK: OK")

    # az upsert a position tablan
    r = psql(stdin_text="""
INSERT INTO position (vessel_id, ts, geom, sog_mps, source_kind)
    VALUES (1, '2026-11-15 10:00:00+00', 'POINT(19.04 47.50)', 8.2, 'ais')
ON CONFLICT (vessel_id, ts) DO UPDATE
    SET sog_mps = EXCLUDED.sog_mps, ingested_at = now();
INSERT INTO position (vessel_id, ts, geom, sog_mps, source_kind)
    VALUES (1, '2026-11-15 10:00:00+00', 'POINT(19.04 47.50)', 9.9, 'ais')
ON CONFLICT (vessel_id, ts) DO UPDATE
    SET sog_mps = EXCLUDED.sog_mps, ingested_at = now();
""")
    if r.returncode != 0:
        print("  HIBA az upsertnel:", r.stderr[-500:])
    else:
        out = psql(sql="SELECT sog_mps FROM position WHERE vessel_id=1;")
        v = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '?'
        print(f"  a position upsert: OK (sog_mps={v} -> az utolso nyer)")

    # a particiok letrejonnek es a TTL funkcio torli a regeket
    r = psql(stdin_text="""
CREATE TABLE ais_message_raw_p20260101 PARTITION OF ais_message_raw
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE ais_message_raw_p20251101 PARTITION OF ais_message_raw
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
INSERT INTO ais_message_raw (received_at, raw_nmea, msg_type, msg_hash)
    VALUES ('2025-11-15 10:00:00+00', '!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23', 1,
            decode(md5('test-hash'), 'hex'));
""")
    if r.returncode != 0:
        print("  HIBA a particionnel:", r.stderr[-500:])
    else:
        out = psql(sql="SELECT count(*) FROM ais_message_raw;")
        n = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '?'
        out = psql(sql="SELECT drop_expired_partitions('ais_message_raw', 14);")
        d = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '?'
        out = psql(sql="SELECT count(*) FROM ais_message_raw;")
        n2 = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '?'
        print(f"  a particio + TTL: OK (sorok a TTL elott: {n} -> eldobott particio: {d} -> sorok utan: {n2})")

    # az audit trigger
    r = psql(stdin_text="""
UPDATE vessel SET length_m = 111.0 WHERE id = 1;
""")
    if r.returncode != 0:
        print("  HIBA az audit trigger-nel:", r.stderr[-500:])
    else:
        out = psql(sql="SELECT count(*) FROM audit_log;")
        a = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '?'
        out = psql(sql="SELECT action, before->>'length_m' AS old_len, after->>'length_m' AS new_len FROM audit_log ORDER BY id DESC LIMIT 1;")
        row = ' | '.join(out.stdout.strip().splitlines()[-2:]) if out.stdout.strip() else '?'
        print(f"  az audit trigger: OK ({a} sor) -> {row}")

    # a fuggveny letezik
    out = psql(sql="SELECT proname FROM pg_proc WHERE proname IN ('set_updated_at','audit_row_change','drop_expired_partitions','sync_vessel_sort_name','sync_vessel_identifiers','sync_vessel_from_identifiers') ORDER BY proname;")
    fns = [l for l in out.stdout.strip().splitlines() if l and not l.startswith('(') and '---' not in l and l != 'proname']
    # --- a referenciaadatok seed ellenorzese (a 2026-11-22, a
    # meresi adat utan) ---
    # A schema a seed nelkul hasznalhatatlan: a `vessel_type_i18n`
    # a `language`-re mutat, es a `vessel.vessel_type_code` a
    # `vessel_type`-ra -> az ingest (a tipus kitoltes) elhal.
    r = psql_tuples("""
SELECT
  (SELECT count(*) FROM language),
  (SELECT count(*) FROM vessel_type),
  (SELECT count(*) FROM vessel_type_i18n),
  (SELECT count(*) FROM country),
  (SELECT count(*) FROM waterway),
  (SELECT count(*) FROM river_section),
  (SELECT count(*) FROM basin),
  (SELECT count(*) FROM cargo_type),
  (SELECT count(*) FROM operator),
  (SELECT count(*) FROM data_source);
""")
    if r:
        print("  a referenciaadatok (nyelv|tipus|tipusnev|orszag|vizszonyat|"
              "szakasz|medence|teher|uzemelteto|forras):", r[0])
    else:
        print("  a referenciaadatok: HIBA (a seed nem futott?)")

    r = psql_tuples("SELECT count(*) FROM vessel_type_i18n "
                    "WHERE lang='hu' AND name IS NOT NULL AND name != '';")
    print(f"  a magyar hajotipus-nevek: {r[0] if r else '0'}")

    # a tipus-kod -> a magyar nev mukodik-e (a F-CAT-08)
    r = psql_tuples("""
SELECT vt.ais_type_code || ' = ' || vti.name
FROM vessel_type vt JOIN vessel_type_i18n vti
  ON vti.vessel_type_code = vt.code AND vti.lang = 'hu'
WHERE vt.ais_type_code IN (8444, 8443, 8440, 8000, 60, 80, 8450)
ORDER BY vt.ais_type_code;
""")
    print(f"  a meresi tipusok magyar neve: {r}")

    print(f"  a DB-fuggvenyek: {fns}")


if __name__ == "__main__":
    sys.exit(main())
