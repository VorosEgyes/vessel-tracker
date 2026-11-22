#!/usr/bin/env python3
"""A lehúzott SQLite-fájl sémájának felismerése.

Az AIS-catcher v0.71-ben a `-D sqlite:` kimenet 5 táblát ír
(ais_vessel, ais_message, ais_nmea, ais_vessel_pos, ais_vessel_static),
de az oszlopnevek a build-től függnek. Ez a script kilistázza a
tényleges sémát, hogy a mérési elemzést (analyze_measurement.py)
pontosan lehessen igazítani.

Használat:
    python3 inspect_schema.py ais.db
"""
from __future__ import annotations

import sqlite3
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("hasznalat: python3 inspect_schema.py <fajl.db>", file=sys.stderr)
        return 2

    path = sys.argv[1]
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    print("=" * 70)
    print(f"{path} — {len(tables)} tábla")
    print("=" * 70)

    for t in tables:
        try:
            cols = db.execute(f"PRAGMA table_info({t})").fetchall()
            count = db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except sqlite3.Error as exc:
            print(f"\n--- {t} --- nem olvasható: {exc}")
            continue

        print(f"\n--- {t} --- ({count:,} sor)")
        for c in cols:
            # cid | name | type | notnull | dflt_value | pk
            pk = " PK" if c[5] else ""
            nn = " NOT NULL" if c[3] else ""
            print(f"    {c[1]:<24} {c[2] or '?':<14}{pk}{nn}")

    # a mintaadat — a tipikus értékek (a szoveg-tipusok oszlopai)
    print("\n" + "=" * 70)
    print("A mintaadat (az első 2 sor minden nem üres táblából)")
    print("=" * 70)
    for t in tables:
        try:
            count = db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except sqlite3.Error:
            continue
        if count == 0:
            continue
        rows = db.execute(f"SELECT * FROM {t} LIMIT 2").fetchall()
        cols = [c[1] for c in db.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"\n--- {t} ---")
        for r in rows:
            for name, val in zip(cols, r):
                if val is None:
                    continue
                s = str(val)
                if len(s) > 120:
                    s = s[:120] + "…"
                print(f"    {name} = {s}")
            print("    " + "-" * 40)

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
