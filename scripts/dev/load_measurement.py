#!/usr/bin/env python3
"""A mérési SQLite betöltése a PostgreSQL-be (a 04 §8.2 — a backfill).

**A mérési adat** (a Pi-n, hetente a NAS-ra lehúzva) **nyers AIS
üzeneteket** tartalmaz (`ais_message`) → **a parser dekódolja** →
**a normalizált rekordok** (a `04` §5) → **a PostgreSQL**.

**A `bud01` vevő (AIS-catcher v0.71) a `nmea` oszlopban a FIZIKAI
6 bites formát tárolja** (a `04` §4.2) → **a `decoder.py`
`physical=True` kapcsolóval olvassa** → **a hajónév, a hívójell és a
hajótípus olvasható.**

**DE:** a vevő a `mmsi`/`lat`/`lon` mezőket **normalizálja** (a
`04` §11 Q8) → **a `nmea`-ból az MMSI NEM olvasható** → **az MMSI-t
a `ais_message.mmsi` oszlopból vesszük** (a vevő ezt megbízhatóan
tartja).

**A BETÖLTÖTT TÁBLÁK:**
- a `vessel` (a `slug`, a `sort_name`, a `vessel_type_code`, az
  `operating_area`, a `flag_country_code`, a `status`, a
  `verification_level`);
- a `vessel_i18n` (a `name` — a hivatalos latin név);
- a `vessel_identifier` (az `mmsi` + a hívójell, az `origin='ais'`);
- a `vessel_alias` (a régi nevek, ha van).

**A `vessel_type_code`:** **a `shiptype` → az `ais_type_code` → a
`vessel_type.code`** (a `make_type_case.py` `parse_seed` mappingje a
`02` tervből) → **a hajótípus nélküli hajók az ismeretlen típust
kapják** (a `02` seedben van egy `unknown`/8000 típus).

**A `slug` és a `sort_name`:** **az alkalmazás generálja** (a
`duna.domain.slug` + a `duna.domain.text`) → **a `sort_name` a
NORMALIZÁLT alak** (a `02` v1.12: az alkalmazás írja).

Hasznalat:
    uv run python scripts/dev/load_measurement.py --db /path/to/ais.db
    uv run python scripts/dev/load_measurement.py --db ... --limit 100
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sqlite3
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_DB_DIR = pathlib.Path("/opt/data/martin/work/ais-data")


def parse_seed(plan: pathlib.Path) -> dict[int, str]:
    """**A `shiptype` → a magyar hajótípus-név mapping** (a `02` tervből).

    **Ugyanaz a logika**, mint a `scripts/ais-receiver/make_type_case.py`
    `parse_seed` függvényében → **a DB és a riport mindig egyezik.**
    """
    text = plan.read_text(encoding="utf-8")
    i = text.find("INSERT INTO vessel_type")
    j = text.find(";", i)
    if i == -1 or j == -1:
        raise SystemExit(f"HIBA: a vessel_type seed nem található a {plan}-ben")
    codes: dict[int, str] = {}
    for row in re.findall(r"\(\s*'([^']+)'\s*,\s*(\d+)\s*,", text[i:j]):
        codes[int(row[1])] = row[0]
    if not codes:
        raise SystemExit(f"HIBA: a vessel_type seed üres a {plan}-ben")
    return codes


# **Az ismeretlen hajótípus** (a `02` seedben az `ERI_8000`, az
# `ais_type_code` = 8000) -> **a hajótípus nélküli hajók ezt kapják**
UNKNOWN_TYPE = "ERI_8000"


def load_measurement(
    db_path: pathlib.Path,
    database_url: str,
    limit: int | None = None,
) -> int:
    """A mérési adat betöltése a PostgreSQL-be.

    **A visszatérés:** a betöltött hajók száma.
    """
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api" / "src"))
    import sqlalchemy as sa

    from duna.domain.slug import generate_slug
    from duna.domain.text import normalize_search_text

    # **a `shiptype` -> a `vessel_type.code`** (a 02 seedből)
    plan = REPO_ROOT / "docs" / "megvalosulas" / "megvalosulas-02-adatbazis-ddl.md"
    type_by_ais_code = parse_seed(plan)

    # **a hajók a legfrissebb `ais_state`-ből** (a vevő összesített
    # állapota MMSI-nként) + **a `ais_static`-ból a név/hívójell/típus**
    # **A NEVET A `nmea`-BOL DEKODOLJUK** (a `04` §4.2: a vevo a
    # FIZIKAI 6 bites formát tárolja -> **a `ais_state.shipname` a
    # fizikai érték**, pl. `1592.4_R_FL` -> **a `decode_static` a
    # valódi nevet adja**, pl. `KISFALUDY`).
    #
    # **A `type 5` (a statikus) uzenet hordozza a nevet, a hivojelet
    # es a tipust** -> **a `nmea` oszlopbol kell** -> **a
    # `ais_state` csak az MMSI-t ad (a normalizalt lat/lon/mmsi
    # miatt, a 04 §11 Q8).**
    sql = """
        SELECT s.mmsi,
               m.nmea,
               s.shiptype,
               s.imo,
               s.destination,
               s.draught,
               s.lat,
               s.lon
          FROM ais_state s
          JOIN ais_message m ON m.mmsi = s.mmsi AND m.type = 5
         WHERE s.mmsi IS NOT NULL
    """
    if limit:
        sql += f" LIMIT {int(limit)}"

    from duna.ingest.decoder import decode_static
    from duna.ingest.frames import assemble_frames

    con = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    raw_rows = con.execute(sql).fetchall()
    con.close()
    if not raw_rows:
        print("a mérési adatban nincs statikus üzenet")
        return 0

    # **a dekódolás** (a `nmea` -> a frame -> a statikus rekord)
    decoded: list[dict[str, object]] = []
    seen: set[int] = set()
    for row in raw_rows:
        mmsi = int(row["mmsi"])
        if mmsi in seen:
            continue
        frame, _invalid = assemble_frames((row["nmea"] or "").split("\n"))
        if frame is None:
            continue
        try:
            report = decode_static(frame.payload, frame.fill_bits, physical=True)
        except ValueError:
            continue
        name = report.shipname.strip()
        if not name:
            continue
        seen.add(mmsi)
        decoded.append(
            {
                "mmsi": mmsi,
                "name": name,
                "callsign": report.callsign.strip() or None,
                "ship_type": report.ship_type,
                "imo": report.imo,
                "destination": report.destination.strip() or None,
                "draught_m": report.draught_m,
            }
        )
        if limit and len(decoded) >= limit:
            break

    rows = decoded

    engine = sa.create_engine(database_url.replace("+asyncpg", "+psycopg"))
    loaded = 0
    with engine.begin() as conn:
        for row in rows:
            mmsi = int(row["mmsi"])
            name = str(row["name"])
            callsign = row["callsign"]
            shiptype = row["ship_type"]
            ais_code = int(shiptype) if shiptype is not None else None
            # **a `shiptype` -> az `ais_type_code` -> a `vessel_type.code`**
            # (a `02` seed mappingje) -> **a hajótípus nélküli hajók az
            # `ERI_8000`-at (az ismeretlen típus) kapják**
            type_code = (
                type_by_ais_code.get(ais_code, UNKNOWN_TYPE)
                if ais_code is not None
                else UNKNOWN_TYPE
            )
            slug = generate_slug(name, mmsi)

            conn.execute(
                sa.text(
                    """
                    INSERT INTO vessel (mmsi, slug, sort_name, vessel_type_code,
                                        operating_area, flag_country_code,
                                        status, verification_level)
                    VALUES (:mmsi, :slug, :sort_name, :type_code, 'duna',
                            (SELECT code FROM country ORDER BY code LIMIT 1),
                            'active', 'ais_partial')
                    ON CONFLICT (slug) DO NOTHING
                    """
                ),
                {
                    "mmsi": mmsi,
                    "slug": slug,
                    "sort_name": normalize_search_text(name),
                    "type_code": type_code,
                },
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO vessel_i18n (vessel_id, lang, name, description)
                    SELECT id, 'hu', :name, NULL FROM vessel WHERE slug = :slug
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"name": name, "slug": slug},
            )
            # **a MMSI azonosito** (a F-SRCH-02: a pontos azonosito-egyezes)
            conn.execute(
                sa.text(
                    """
                    INSERT INTO vessel_identifier (vessel_id, identifier_type, value,
                                                 is_primary, origin, source_id)
                    SELECT id, 'mmsi', :mmsi, true, 'ais',
                           (SELECT id FROM data_source ORDER BY id LIMIT 1)
                      FROM vessel WHERE slug = :slug
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"mmsi": str(mmsi), "slug": slug},
            )
            if callsign:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO vessel_identifier (vessel_id, identifier_type, value,
                                                     is_primary, origin, source_id)
                        SELECT id, 'callsign', :callsign, false, 'ais',
                               (SELECT id FROM data_source ORDER BY id LIMIT 1)
                          FROM vessel WHERE slug = :slug
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"callsign": callsign, "slug": slug},
                )
            loaded += 1

    print(f"a betöltött hajók: {loaded}")
    loaded_positions = load_positions(engine, db_path, limit)
    print(f"a betöltött pozíciók: {loaded_positions}")
    return loaded


def _parse_timestamp(value) -> dt.datetime:
    """**A mérési SQLite időbélyegének parse-olása**.

    **A vevő a `YYYY/MM/DD HH:MM:SS` formátumot írja** (nem ISO) →
    **a `fromisoformat` nem működik rá** → **ez a parser kezeli** →
    **a `YYYY-MM-DD HH:MM:SS` (ISO) alakot is**.
    """
    import datetime as dt

    if isinstance(value, dt.datetime):
        return value
    text_value = str(value).strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(text_value, fmt)
        except ValueError:
            continue
    raise ValueError(f"ismeretlen idoformatum: {text_value!r}")


def load_positions(engine, db_path: pathlib.Path, limit: int | None = None) -> int:
    """**A pozíciók betöltése** a `position` táblába (a `04` §8.2).

    **A FORRÁS:** a mérési SQLite `ais_position` táblája (a vevő
    már dekódolva adja a lat/lon/speed/course-t) **a
    `ais_message`-hez csatlakoztatva** (a `received_at` az időbélyeg).

    **A `ts` a GNSS-idő** -> **a `position` a `ts` szerint
    particionált** -> **a havi particiokat ELOTTE kell hozni**
    (a `duna.ingest.partitions.ensure_partitions`) -> **a `default`
    particioba nem irunk** (a TTL azt uritenne).

    **A MMSI a `vessel.mmsi`** -> **a `position.vessel_id` az
    `vessel.id`** -> **a MMSI->id leképezés a betöltés elején**.

    **A `COPY` A GYORS TOMELEGES BETOLTES** (a `psycopg`
    `copy()` -> a PostgreSQL `COPY ... FROM STDIN`) -> **a 826 508
    pozicio egyenkenti `INSERT`-tel ~7 perc, a `COPY`-val
    masodpercek.**

    **A `COPY` NEM megy direktbe a particionalt `position`
    tablaba a dedup miatt** (a `PRIMARY KEY (vessel_id, ts)`) ->
    **egy STAGING tabla** (a `COPY` ide megy) -> **azután egy
    `INSERT ... SELECT ... ON CONFLICT DO NOTHING`** (a dedup, a
    04 §6).

    **A fizikailag lehetetlen ertekek** (a lat/lon 91-180 fok, a SOG
    0-60 m/s felett, a COG/heading 360) -> **`None`** (a 04 §7) ->
    **a DB `CHECK` constraintjei nem buktathatjak el a batch-et.**
    """
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api" / "src"))
    import sqlalchemy as sa

    from duna.ingest.partitions import ensure_partitions, months_between

    # --- a hajo id-k ---
    with engine.connect() as conn:
        vessel_ids = dict(
            conn.execute(sa.text("SELECT mmsi, id FROM vessel WHERE mmsi IS NOT NULL")).all()
        )
    if not vessel_ids:
        return 0

    con = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    sql = """
        SELECT m.mmsi,
               m.received_at,
               m.type,
               p.lat,
               p.lon,
               p.speed,
               p.course,
               p.heading
          FROM ais_message m
          JOIN ais_position p ON p.msg_id = m.id
         WHERE m.type IN (1, 2, 3)
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = con.execute(sql).fetchall()
    con.close()
    if not rows:
        return 0

    # --- a particiok (a hónapok a `ts`/`received_at` alapjan) ---
    stamps = [_parse_timestamp(row["received_at"]) for row in rows]
    months = months_between(min(stamps), max(stamps))

    written = 0
    with engine.begin() as conn:
        created = ensure_partitions(conn, "position", months)
        if created:
            print(f"a létrehozott pozíció-partíciók: {len(created)} ({created[0]}…{created[-1]})")

        conn.execute(
            sa.text(
                """
                CREATE TEMP TABLE position_stage (
                    vessel_id bigint NOT NULL,
                    ts timestamptz NOT NULL,
                    msg_type smallint,
                    sog_mps numeric(5,2),
                    cog_deg numeric(5,2),
                    heading_deg numeric(5,2),
                    lat_e7 integer,
                    lon_e7 integer
                ) ON COMMIT DROP
                """
            )
        )

        raw = conn.connection
        copy_sql = (
            "COPY position_stage "
            "(vessel_id, ts, msg_type, sog_mps, cog_deg, heading_deg, lat_e7, lon_e7) "
            "FROM STDIN"
        )
        with raw.cursor().copy(copy_sql) as copy:
            for row in rows:
                vessel_id = vessel_ids.get(int(row["mmsi"]))
                if vessel_id is None:
                    continue
                lat = row["lat"]
                lon = row["lon"]
                if lat is None or lon is None:
                    continue
                if not (-90.0 <= float(lat) <= 90.0) or not (-180.0 <= float(lon) <= 180.0):
                    continue
                copy.write_row(
                    (
                        vessel_id,
                        _parse_timestamp(row["received_at"]),
                        int(row["type"]),
                        _sanitize(row["speed"], 0.0, 60.0, inclusive_max=False),
                        _sanitize(row["course"], 0.0, 360.0),
                        _sanitize(row["heading"], 0.0, 360.0),
                        round(float(lat) * 10_000_000),
                        round(float(lon) * 10_000_000),
                    )
                )
                written += 1

        conn.execute(
            sa.text(
                """
                INSERT INTO position (vessel_id, ts, msg_type, sog_mps, cog_deg,
                                     heading_deg, lat_e7, lon_e7, source_kind)
                SELECT vessel_id, ts, msg_type, sog_mps, cog_deg, heading_deg,
                       lat_e7, lon_e7, 'ais'
                  FROM position_stage
                ON CONFLICT (vessel_id, ts) DO NOTHING
                """
            )
        )

    return written


def _sanitize(value, low: float, high: float, inclusive_max: bool = True):
    """**A fizikailag lehetetlen értékek -> `None`** (a `04` §7).

    **A DB `CHECK` constraintjei** (a `position_sog_check` stb.)
    **megérlnek** -> **a betöltés nem hagyhatja, hogy egy hibás sor
    elbuktassa a WHOLE batch-et.**
    """
    if value is None:
        return None
    number = float(value)
    ok = low <= number <= high if inclusive_max else low <= number < high
    return number if ok else None


def main() -> int:
    """A betöltő."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--db",
        type=pathlib.Path,
        help="a mérési SQLite fájl (a default: a legutóbbi a /opt/data/martin/work/ais-data/)",
    )
    ap.add_argument("--limit", type=int, help="a betöltendő hajók max. száma")
    args = ap.parse_args()

    db_path = args.db
    if db_path is None:
        candidates = sorted(
            DEFAULT_DB_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not candidates:
            print(f"HIBA: nincs mérési adat a {DEFAULT_DB_DIR}-ben")
            return 2
        db_path = candidates[0]

    if not db_path.exists():
        print(f"HIBA: a mérési adat nem létezik: {db_path}")
        return 2

    import os

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("HIBA: a DATABASE_URL nincs beállítva")
        return 2

    print(f"a mérési adat: {db_path}")
    load_measurement(db_path, url, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
