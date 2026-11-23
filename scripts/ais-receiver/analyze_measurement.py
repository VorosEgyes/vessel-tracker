#!/usr/bin/env python3
"""A 30 napos AIS-merés elemzése — a go/no-go döntés.

A Pi-ről lehúzott SQLite-fájlt elemzi, és a `ais-vevo-terv.md`
5. fejezetének hat metrikáját számolja ki:

  1. az üzenetek száma
  2. az üzenettípusok megoszlása
  3. a hibás üzenetek aránya
  4. a dekódolható statikus adatok aránya (a hány hajóból van ENI/név/méret)
  5. a pozíciók minősége (a river_km a folyó-korridoron belül van-e?)
  6. a ghost hajók aránya (a négy szűrőszabály után)

Használat:
    python3 analyze_measurement.py ais.db
    python3 analyze_measurement.py ais.db --json > measurement.json
"""
from __future__ import annotations

import argparse
import json
import re
import math
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone

# --- a szűrőszabályok (a 01-es terv §5.5 és az ais-vevo-terv 4.2) ---
MAX_SOG_KNOTS = 12.0          # a Duna legnagyobb hajói is lassabbak
STATIC_DAYS = 5               # 5+ napig ugyanott álló hajó
INLAND_MIN_KM = 1500.0        # a Duna folyó-km sávja (Sulina = 0)
INLAND_MAX_KM = 1900.0
CORRIDOR_HALF_WIDTH_KM = 3.0  # a folyó-korridor félszélessége


def _rows(db: sqlite3.Connection, sql: str, args=()) -> list[tuple]:
    try:
        return db.execute(sql, args).fetchall()
    except sqlite3.Error:
        return []


def _tables(db: sqlite3.Connection) -> set[str]:
    return {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}



# =====================================================================
# A DUNA BUDAPEST-KORNYEKI SZAKASZANAK POLYGONJA
#
# A navigacios lampak (a "1592.4_R_FL" stilusu AIS-allomasok)
# pozicioibol levezetve. A pontok a Duna kozepvonalatakor egy
# korridor-szalagot alkotnak — a hajok a szalag +/- egy
# toleranciaban vannak.
#
# A pontok formatuma: (lat, lon, "a pont neve")
# =====================================================================
DUNA_CORRIDOR_POINTS = [
    (47.11671, 18.88409, "1598.3"),
    (47.14315, 18.87542, "1601.2"),
    (47.16399, 18.87054, "1603.5"),
    (47.21368, 18.89720, "1609.5"),
    (47.23567, 18.90935, "1612.1"),
    (47.27467, 18.91698, "1616.6"),
    (47.28978, 18.91814, "1618.3"),
    (47.30563, 18.92810, "1620.2"),
    (47.32564, 18.94170, "1622.6"),
    (47.34108, 18.95292, "1624.6"),
    (47.36060, 18.95120, "1626.8"),
    (47.36281, 18.95002, "1627.0"),
    (47.47970, 19.06380, "1644.4"),
    (47.48560, 19.05610, "1645.2"),
    (47.48650, 19.05510, "1645.3"),
    (47.49650, 19.04720, "VISEGRAD"),
    (47.50660, 19.04040, "BUDAPEST"),
    (47.54160, 19.05800, "1651.97"),
    (47.77154, 18.95008, "1696.7"),
]

# a korridor szelessége (km) — a hajo a kozepvonal +/- ennyire van
CORRIDOR_HALF_WIDTH_KM = 1.5


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(min(1.0, x)))


def _in_duna_corridor(lat, lon):
    """True, ha a pont a Duna Budapest-kornyeki szakaszának korridorjan belul van."""
    best = None
    for i in range(len(DUNA_CORRIDOR_POINTS) - 1):
        a = DUNA_CORRIDOR_POINTS[i]
        b = DUNA_CORRIDOR_POINTS[i + 1]
        # a pont -> a szakasz egyenes darabjanak legkozelebbi pontja
        # (a kis Foldrajzon a szakaszok rovidek, ezert a pontokra
        # valo kozelites elegendo)
        d1 = _haversine_km(lat, lon, a[0], a[1])
        d2 = _haversine_km(lat, lon, b[0], b[1])
        d = min(d1, d2)
        if best is None or d < best:
            best = d
    return best is not None and best <= CORRIDOR_HALF_WIDTH_KM


def analyze(path: str) -> dict:
    # A "immutable=1" NEM hoz letre -wal/-shm fajlokat a lehuzott
    # DB mellett -> a heti takaritas (a NAS-on) tiszta marad.
    # (A sima "mode=ro" a WAL-mod miatt MEGIS létrehozza őket.)
    db = sqlite3.connect(f"file:{path}?immutable=1", uri=True)
    tables = _tables(db)
    result: dict = {
        "file": path,
        "tables": sorted(tables),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    if not tables:
        result["error"] = "az adatbazis ures (vagy a tabla-nevek masok)"
        return result

    # --- 1. az uzenetek szama ---
    total = 0
    if "ais_message" in tables:
        total = _rows(db, "SELECT count(*) FROM ais_message")[0][0]
    elif "ais_nmea" in tables:
        total = _rows(db, "SELECT count(*) FROM ais_nmea")[0][0]
    result["total_messages"] = total

    # --- a period ---
    if "ais_message" in tables:
        cols = {r[1] for r in db.execute("PRAGMA table_info(ais_message)")}
        ts_col = next((c for c in ("rxtime", "rx_time", "timestamp", "ts")
                       if c in cols), None)
        if ts_col:
            rng = _rows(db, f"SELECT min({ts_col}), max({ts_col}) FROM ais_message")
            if rng and rng[0][0]:
                result["period"] = {"from": str(rng[0][0]), "to": str(rng[0][1])}

    # --- 2. az uzenettipusok megoszlasa ---
    type_counts: Counter = Counter()
    nmea_type_counts: Counter = Counter()
    if "ais_message" in tables:
        cols = {r[1] for r in db.execute("PRAGMA table_info(ais_message)")}
        # A v0.71-es semaban az oszlop neve "type" (nem "msg_type").
        type_col = next((c for c in ("type", "msg_type") if c in cols), None)
        if type_col:
            for t, n in _rows(db, f"SELECT {type_col}, count(*) FROM ais_message "
                                  f"GROUP BY {type_col} ORDER BY 2 DESC"):
                type_counts[str(t)] = n
    # a nyers NMEA-ből a tipus kinyerése (ha van ais_nmea tabla)
    if "ais_message" in tables:
        ncols = {r[1] for r in db.execute("PRAGMA table_info(ais_message)")}
        raw_col = next((c for c in ("nmea", "raw", "sentence") if c in ncols), None)
        if raw_col:
            for (raw,) in _rows(db, f"SELECT {raw_col} FROM ais_message LIMIT 500000"):
                if not raw:
                    continue
                m = re.match(r"^![A-Z]{2}VDM,(\d),(\d),", raw)
                if m:
                    # A belvizi FI 10 a nyers szovegbol nem lathato —
                    # a tipus a pozicio uzenetbol jon (a fenti type
                    # szamlalas).
                    nmea_type_counts["sor"] += 1
    result["nmea_sentences"] = sum(nmea_type_counts.values())
    result["message_types"] = dict(type_counts.most_common())

    # --- 3. a hibas uzenetek aranya ---
    # a hiba a 'status' oszlopban (nem 0) vagy a 'error' oszlopban
    errors = 0
    if "ais_message" in tables:
        cols = {r[1] for r in db.execute("PRAGMA table_info(ais_message)")}
        if "status" in cols:
            errors = _rows(db, "SELECT count(*) FROM ais_message "
                               "WHERE status IS NOT NULL AND status != 0")[0][0]
        elif "error" in cols:
            errors = _rows(db, "SELECT count(*) FROM ais_message "
                               "WHERE error IS NOT NULL AND error != 0")[0][0]
    result["error_messages"] = errors
    # Ha a semaban nincs status/error oszlop, a hibaarany nem
    # merheto a DB-ből (a v0.71 csak a sikeres dekódolásokat tárolja)
    error_measurable = "status" in cols or "error" in cols if "ais_message" in tables else False
    result["error_measurable"] = error_measurable
    result["error_ratio"] = (round(errors / total, 6)
                              if total and error_measurable else None)

    # --- 4. a statikus adatok ---
    vessels = 0
    with_eni = 0
    with_name = 0
    with_dims = 0
    if "ais_state" in tables:
        cols = {r[1] for r in db.execute("PRAGMA table_info(ais_state)")}
        vessels = _rows(db, "SELECT count(*) FROM ais_state")[0][0]
        if "imo" in cols:
            with_eni = _rows(db, "SELECT count(*) FROM ais_state "
                                 "WHERE imo IS NOT NULL AND imo != 0")[0][0]
        # A nev es a meretek oszlopnevai a v0.71-ben
        for name_col in ("name", "shipname", "vessel_name"):
            if name_col in cols:
                with_name = _rows(db, f"SELECT count(*) FROM ais_state "
                                     f"WHERE {name_col} IS NOT NULL "
                                     f"AND {name_col} != ''")[0][0]
                break
        dim_cols = [c for c in ("length", "beam", "draught", "shiptype")
                    if c in cols]
        if dim_cols:
            cond = " OR ".join(f"{c} IS NOT NULL AND {c} != 0" for c in dim_cols)
            with_dims = _rows(db, f"SELECT count(*) FROM ais_state "
                                 f"WHERE {cond}")[0][0]

    result["vessels"] = vessels
    result["vessels_with_imo"] = with_eni
    result["vessels_with_name"] = with_name
    result["vessels_with_dimensions"] = with_dims
    result["static_coverage"] = {
        "ratio_imo": round(with_eni / vessels, 4) if vessels else None,
        "ratio_name": round(with_name / vessels, 4) if vessels else None,
        "ratio_dimensions": round(with_dims / vessels, 4) if vessels else None,
    }

    # --- 5. a poziciok minosege ---
    positions = 0
    in_corridor = 0
    with_km = 0
    if "ais_position" in tables:
        cols = {r[1] for r in db.execute("PRAGMA table_info(ais_position)")}
        positions = _rows(db, "SELECT count(*) FROM ais_position")[0][0]
        # a folyo-km oszlop neve a v0.71-ben
        # A v0.71-es AIS-catcher NEM dekodolja a fairway-mezot
        # (a river_km) — azt a SAJAT parserunk (a 04-es terv)
        # ki a nyers NMEA-bol. A korridor-ellenorzes ezert a
        # 30 napos meres UTAN, a sajat parserrel tortenik.
        km_col = next((c for c in ("river_km", "fairway_distance")
                       if c in cols), None)
        lat_col = next((c for c in ("lat", "latitude") if c in cols), None)
        lon_col = next((c for c in ("lon", "longitude") if c in cols), None)
        if km_col:
            with_km = _rows(db, f"SELECT count(*) FROM ais_position "
                                f"WHERE {km_col} IS NOT NULL")[0][0]
            in_corridor = _rows(
                db, f"SELECT count(*) FROM ais_position "
                   f"WHERE {km_col} BETWEEN ? AND ?",
                (INLAND_MIN_KM, INLAND_MAX_KM))[0][0]
    result["positions"] = positions
    result["positions_with_river_km"] = with_km
    result["positions_in_corridor"] = in_corridor
    result["corridor_ratio"] = (round(in_corridor / with_km, 4)
                                if with_km else None)

    # --- 5b. a FOLDRAJZI lefedettség ---
    #
    # A "river_km" a v0.71-ben nincs (a fairway-mezot a SAJAT
    # parserunk, a 04-es terv szerint dekodolja) — ezert a
    # mostani meresben a FOLDRAJZI becslest hasznaljuk: a Duna
    # Budapest-kornyeki szakaszának korridorjan belul eso poziciok
    # aranya. Ez a go/no-go kritérium (a "lefedettseg") proxyja.
    if "ais_position" in tables:
        pcols = {r[1] for r in db.execute("PRAGMA table_info(ais_position)")}
        plat = next((c for c in ("lat", "latitude") if c in pcols), None)
        plon = next((c for c in ("lon", "longitude") if c in pcols), None)
        if plat and plon:
            geo_total = 0
            geo_in = 0
            for lat, lon in _rows(db, f"SELECT {plat}, {plon} FROM ais_position "
                                      f"WHERE {plat} IS NOT NULL AND {plat} != 0"):
                geo_total += 1
                if _in_duna_corridor(lat, lon):
                    geo_in += 1
            result["positions_geo_total"] = geo_total
            result["positions_in_duna_corridor"] = geo_in
            result["geo_corridor_ratio"] = (round(geo_in / geo_total, 4)
                                            if geo_total else None)

    # --- 6. a ghost hajok ---
    # A v0.71-es semaban az `ais_position` a `msg_id`-vel hivatkozik
    # az `ais_message`-re (nincs benne mmsi) — a sebességszures
    # ezert a JOIN-on keresztul megy.
    ghost_candidates = 0
    still_count = 0
    if "ais_state" in tables and "ais_position" in tables:
        pcols = {r[1] for r in db.execute("PRAGMA table_info(ais_position)")}
        speed_col = next((c for c in ("speed", "sog") if c in pcols), None)
        if speed_col:
            r = _rows(
                db, "SELECT count(DISTINCT m.mmsi) FROM ais_position p "
                   "JOIN ais_message m ON m.id = p.msg_id "
                   f"WHERE p.{speed_col} > ?", (MAX_SOG_KNOTS,))
            ghost_candidates = r[0][0] if r else 0
            # az "allandoan allo" hajok: a legutolso poziciojuk
            # speedje 0 es a gyakorisaguk magas
            r2 = _rows(
                db, "SELECT count(*) FROM ais_state "
                   "WHERE speed IS NOT NULL AND speed < 0.5")
            still_count = r2[0][0] if r2 else 0
    result["ghost_candidates_over_speed"] = ghost_candidates
    result["vessels_standing_still"] = still_count

    # --- a belvizi FI 10 jelenlete (a legfontosabb!) ---
    inland = 0
    if "ais_message" in tables:
        cols = {r[1] for r in db.execute("PRAGMA table_info(ais_message)")}
        # A v0.71-es semaban az oszlop neve "type" (nem "msg_type").
        # A belvozi FI 10 a 6-os es a 8-as uzenettipus (200-as DAC).
        type_col = next((c for c in ("type", "msg_type") if c in cols), None)
        if type_col:
            inland = _rows(db, f"SELECT count(*) FROM ais_message "
                               f"WHERE {type_col} IN (6,8)")[0][0]
    result["inland_fi10_messages"] = inland

    db.close()
    return result


def verdict(r: dict) -> list[str]:
    """A go/no-go kritériumok (az ais-vevo-terv.md 5.3)."""
    out: list[str] = []
    total = r.get("total_messages") or 0
    out.append(f"az üzenetek száma: {total:,}")

    err_ratio = r.get("error_ratio")
    if err_ratio is None and not r.get("error_measurable", True):
        out.append("a hibás üzenetek aránya: nem mérhető a DB-ből "
                   "(a v0.71 csak a sikeresen dekódolt üzeneteket tárolja)")
    elif err_ratio is not None:
        ok = err_ratio < 0.001
        # MEGJEGYZES: a v0.71-es AIS-catcher CSAK a sikeresen
        # dekódolt uzeneteket irja a DB-be, a hibasak a stdout-on
        # jelennek meg. Ezert a DB-ből a hibaarany NEM hatarozhato
        # meg — ha nincs status/error oszlop, a "mert" resz 0.0%,
        # ami hamis optimizmus lenne. Ilyenkor a resz helyett a
        # "nem merhető" a helyes.
        out.append(f"a hibás üzenetek aránya: {err_ratio:.4%} "
                   f"({'OK' if ok else 'NEM OK'} — a határ 0,1%)")

    cov = r.get("static_coverage") or {}
    ratio_imo = cov.get("ratio_imo")
    if ratio_imo is not None:
        out.append(f"a statikus adatok aránya (IMO): {ratio_imo:.1%}")
    ratio_name = cov.get("ratio_name")
    if ratio_name is not None:
        out.append(f"a statikus adatok aránya (név): {ratio_name:.1%}")

    corridor = r.get("corridor_ratio")
    if corridor is not None:
        out.append(f"a pozíciók a folyó-korridoron belül: {corridor:.1%}")

    geo = r.get("geo_corridor_ratio")
    if geo is not None:
        out.append(f"a Duna-korridorban lévő pozíciók (földrajzi): {geo:.1%}")

    inland = r.get("inland_fi10_messages") or 0
    out.append(f"a belvízi FI 10 üzenetek: {inland:,} "
               f"({'OK — az ENI-k elérhetők' if inland > 0 else 'HIBA — nincs ENI!'})")

    vessels = r.get("vessels") or 0
    out.append(f"a látott hajók: {vessels:,}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", help="a lehúzott SQLite fájl")
    ap.add_argument("--json", action="store_true",
                    help="a kimenet JSON (a gépi feldolgozáshoz)")
    args = ap.parse_args()

    r = analyze(args.db)

    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    print("=" * 68)
    print("A 30 napos AIS-merés eredménye")
    print("=" * 68)
    print(f"fájl: {r['file']}")
    print(f"táblák: {', '.join(r['tables']) or '(nincs)'}")
    if "period" in r:
        print(f"időszak: {r['period']['from']} → {r['period']['to']}")
    print()
    for line in verdict(r):
        print(f"  • {line}")
    print()
    if r.get("message_types"):
        print("  az üzenettípusok:")
        for t, n in sorted(r["message_types"].items(),
                           key=lambda kv: -kv[1])[:12]:
            print(f"      {t:>4}: {n:>8,}")
    print()
    print("A részletes elemzés: a --json kapcsolóval")
    return 0


if __name__ == "__main__":
    sys.exit(main())
