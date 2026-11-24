#!/usr/bin/env python3
"""A `shiptype` → magyar hajótípus-név CASE lista generálása.

A `report_vessels.sh` a mérési SQLite-adatbázisra fut (a Pi-on), és
abban **nincs** a `vessel_type` / `vessel_type_i18n` tábla (az a
PostgreSQL-ben van, a `02` – DDL-terv seedje szerint) → **a típusnevek
a seedből jönnek**.

**A CASE lista a `02` – DDL-tervből generálódik**, hogy a riport és a
DB **mindig egyezzen** (a seed 88 típusa + a magyar nevek).

Használat (a repó gyökeréből):
    python3 scripts/ais-receiver/make_type_case.py            # kiírja a stdout-ra
    python3 scripts/ais-receiver/make_type_case.py --check    # ellenőrzi a riportot

A `--check` a `report_vessels.sh`-ben lévő CASE-t hasonlítja a
generált listához → **a CI-ban futtatható** (a `07` §8.1 szerint a
séma-drift ellenőrzés mellett).
"""

import argparse
import pathlib
import re
import sys

# a 02 – DDL-terv (a repo gyökerében)
DEFAULT_PLAN = pathlib.Path("docs/megvalosulas/megvalosulas-02-adatbazis-ddl.md")
DEFAULT_REPORT = pathlib.Path("scripts/ais-receiver/report_vessels.sh")


def parse_seed(plan: pathlib.Path) -> dict[int, str]:
    """A `vessel_type` + `vessel_type_i18n` seedből: ais_type_code → magyar név."""
    text = plan.read_text(encoding="utf-8")

    # a vessel_type seed: ('ERI_8444', 8444, 'passenger', true, 'duna')
    i = text.find("INSERT INTO vessel_type")
    j = text.find(";", i)
    if i == -1 or j == -1:
        raise SystemExit(f"HIBA: a vessel_type seed nem talalhato a {plan}-ben")
    codes: dict[str, int] = {}
    for m in re.finditer(r"\('((?:ERI|SOLAS)_\d+)',\s*(NULL|\d+),\s*(?:NULL|'[a-z]+')", text[i:j]):
        if m.group(2) != "NULL":
            codes[m.group(1)] = int(m.group(2))

    # a magyar nevek: ('ERI_8444', 'hu', 'személyhajó szállás nélkül', ...)
    i = text.find("INSERT INTO vessel_type_i18n")
    j = text.find(";", i)
    if i == -1 or j == -1:
        raise SystemExit(f"HIBA: a vessel_type_i18n seed nem talalhato a {plan}-ben")
    names: dict[str, str] = {}
    for m in re.finditer(r"\('((?:ERI|SOLAS)_\d+)',\s*'hu',\s*'([^']*)'", text[i:j]):
        names[m.group(1)] = m.group(2)

    missing = [c for c in codes if c not in names]
    if missing:
        raise SystemExit(f"HIBA: {len(missing)} tipusnak nincs magyar neve: {missing[:5]}")
    return {ais: names[code] for code, ais in codes.items()}


def build_case(types: dict[int, str]) -> str:
    """A CASE lista (a riportbeli formátumban)."""
    rows = []
    for ais in sorted(types):
        name = types[ais].replace("'", "''")
        rows.append(f"    WHEN {ais} THEN '{name}'")
    return "CASE shiptype\n" + "\n".join(rows) + "\n  END"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--plan", type=pathlib.Path, default=DEFAULT_PLAN, help="a 02-es DDL-terv (a seed forrasa)"
    )
    ap.add_argument(
        "--report", type=pathlib.Path, default=DEFAULT_REPORT, help="a report_vessels.sh (a cel)"
    )
    ap.add_argument(
        "--check", action="store_true", help="ellenorizd a riportot a generalt listaval"
    )
    args = ap.parse_args()

    if not args.plan.exists():
        raise SystemExit(
            f"HIBA: a terv nem ltezik: {args.plan}\n"
            f"(a repo gyokereben futtasd: python3 scripts/ais-receiver/{pathlib.Path(__file__).name})"
        )

    types = parse_seed(args.plan)
    case = build_case(types)

    if not args.check:
        print(case)
        return 0

    # --- a --check: a riportban a CASE egyezik-e ---
    if not args.report.exists():
        raise SystemExit(f"HIBA: a riport nem ltezik: {args.report}")
    text = args.report.read_text(encoding="utf-8")
    m = re.search(r"CASE shiptype\n(?:.*\n)*?  END", text)
    if not m:
        raise SystemExit(f"HIBA: a CASE lista nem talalhato a {args.report}-ben")
    actual = m.group(0)

    if actual != case:
        n_actual = actual.count("WHEN")
        n_want = case.count("WHEN")
        raise SystemExit(
            f"HIBA: a CASE lista elter a seedtol!\n"
            f"  a riportban: {n_actual} tipus\n"
            f"  a seedbol:  {n_want} tipus\n"
            f"  -> a riportot frissiteni kell: "
            f"python3 scripts/ais-receiver/{pathlib.Path(__file__).name} > /tmp/case.txt\n"
            f"     majd a CASE blokkot a /tmp/case.txt tartalmaval kell cserelni"
        )

    print(f"OK: a CASE lista egyezik a seeddel ({case.count('WHEN')} tipus)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
