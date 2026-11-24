#!/usr/bin/env python3
# A vevo helyzetbol merheto tenyleges hatotavolsag — a BUDAPEST jelolés
# NEM a vevo, hanem egy hajo a pesti belvarosban.
import math
import sqlite3

RECEIVER = (47.5755205, 19.046013)  # a valodi vevo (a keresedből)
DB = "/var/lib/ais/ais.db"


def hav(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    # a fold atmerete (km) — a `ruff` N806 szerint a fuggvenybeli
    # valtozonak kisbetusnek kell lennie
    r_fold = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r_fold * math.asin(math.sqrt(min(1.0, x)))


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    print("=" * 70)
    print("A BUD01 VEVŐ — a valós helyzettel számolva")
    print("=" * 70)
    print(f"a vevő: {RECEIVER[0]:.7f} N, {RECEIVER[1]:.7f} E")
    print()

    rows = db.execute("""
        SELECT mmsi, shipname, lat, lon, speed, count AS uzen, imo, shiptype
        FROM ais_state WHERE lat IS NOT NULL AND lat != 0
    """).fetchall()

    # --- a navigacios lampak: a Duna vonalaja ---
    lamps = []
    for r in rows:
        nm = r["shipname"] or ""
        if "_" in nm and not nm.startswith("VIRTUAL"):
            try:
                km = float(nm.split("_")[0])
            except ValueError:
                continue
            lamps.append((r, km))

    print("--- 1. A VEVŐ TÁVOLSÁGA A DUNÁTÓL (a navigációs lámpákból) ---")
    if lamps:
        # a legkozelebbi lampak
        near = sorted(lamps, key=lambda x: hav(RECEIVER, (x[0]["lat"], x[0]["lon"])))[:6]
        print("   a legközelebbi navigációs lámpák:")
        for r, km in near:
            d = hav(RECEIVER, (r["lat"], r["lon"]))
            print(f"     {r['shipname']:<16} {km:>8.1f} Duna-km   {d:>6.2f} km-re")
        # a Duna kozepvonala: a "zold" (bal part) es a "piros" (jobb part)
        # lampak atlagpontja kozelebbre
        best = None
        for r, km in lamps:
            for r2, km2 in lamps:
                if km2 <= km:
                    continue
                # a parok a kozeli km-eknel
                if km2 - km > 3:
                    continue
                mid = ((r["lat"] + r2["lat"]) / 2, (r["lon"] + r2["lon"]) / 2)
                d = hav(RECEIVER, mid)
                if best is None or d < best[0]:
                    best = (d, r["shipname"], r2["shipname"], km, km2)
        if best:
            print()
            print(
                f"   a legkozelebbi lampapar: {best[1]} ({best[3]} km) + {best[2]} ({best[4]} km)"
            )
            print(f"   a Duna középvonalától: {best[0]:.2f} km")
    print()

    # --- a hajok a valodi vevotol ---
    print("--- 2. A HAJÓK A VALÓDI VEVŐTŐL ---")
    vessels = []
    for r in rows:
        nm = (r["shipname"] or "").strip()
        if not nm or "_" in nm:
            continue
        d = hav(RECEIVER, (r["lat"], r["lon"]))
        vessels.append((d, r))
    vessels.sort(key=lambda x: x[0])

    print("   a legközelebbi 15:")
    for d, r in vessels[:15]:
        print(
            f"     {(r['shipname'] or '(névtelen)'):<22} {d:>6.2f} km   "
            f"{r['uzen']:>4} üzenet  {r['speed'] or 0:>5.1f} kn"
        )
    print()
    print("   a legtávolabbi 10:")
    for d, r in vessels[-10:][::-1]:
        print(f"     {(r['shipname'] or '(névtelen)'):<22} {d:>6.2f} km   {r['uzen']:>4} üzenet")

    # --- a csoportok a valodi vevotol ---
    print()
    print("--- 3. A HAJÓCSOPORTOK (a valódi vevőtől mérve) ---")
    groups = {}
    for d, r in vessels:
        m = r["mmsi"]
        if 992000000 <= m <= 992999999:
            g = "belső (dunai navigáció)"
        elif 243000000 <= m <= 243999999:
            g = "magyar hajó"
        else:
            g = "nemzetközi hajó"
        gg = groups.setdefault(g, {"n": 0, "u": 0, "km": []})
        gg["n"] += 1
        gg["u"] += r["uzen"]
        gg["km"].append(d)
    for g, v in sorted(groups.items(), key=lambda x: -x[1]["u"]):
        km = sorted(v["km"])
        print(
            f"   {g:<26} {v['n']:>3} hajó  {v['u']:>6} üzenet  "
            f"{km[0]:.1f}–{km[-1]:.1f} km  (átlag {sum(km) / len(km):.1f})"
        )

    # --- a jelerosseg: a Fi 10 (a belso forgalmi adat) forrasai ---
    print()
    print("--- 4. A FI 10 (ENI-adat) ÜZENETEK FORRÁSAI ---")
    for r in db.execute("""
        SELECT m.mmsi, s.shipname, s.lat, s.lon, count(*) AS n
        FROM ais_message m JOIN ais_state s ON s.mmsi = m.mmsi
        WHERE m.type IN (6,8) GROUP BY m.mmsi ORDER BY n DESC LIMIT 8
    """):
        nm = (r["shipname"] or "(névtelen)").strip()
        d = f"{hav(RECEIVER, (r['lat'], r['lon'])):6.2f} km" if r["lat"] else "     ? km"
        print(f"     {nm:<22} {r['n']:>3} FI 10 üzenet   {d}")


if __name__ == "__main__":
    main()
