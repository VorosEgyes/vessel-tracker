#!/usr/bin/env python3
"""A `db/ddl/schema-v1.1.sql` generálása a 02-es DDL-tervből.

**Miért ez a forrás:** a `02` – adatbázis-terv a kanonikus
sémaleírás (a `docs/megvalosulas/megvalosulas-02-adatbazis-ddl.md`),
**nem** egy `pg_dump` kimenete. A generált fájl a terv SQL-blokkjaival
egyezik → a `just ddl-diff` (a `07` §8.1 10b. lépése) a **valódi
séma-driftet** ellenőrzi: ha a terv változik, a generált fájl is
változik → a `git diff --exit-code` elbukik.

**A kapcsolat a validátorral:** a `db/tools/validate_ddl.py` ugyanezt
a blokk-kivonást használja (`extract_ddl`) → **a validált sémia és a
verziózott `db/ddl/` fájl garantáltan ugyanaz.**

Használat:
    uv run python db/tools/gen_ddl.py            # a fájl kiírása
    uv run python db/tools/gen_ddl.py --check    # nincs-e eltérés
    uv run python db/tools/gen_ddl.py --stdout   # a stdout-ra (a diffhez)

A `--check` a CI-ben a `just ddl-diff` mögött áll: nem ír, csak
ellenőriz → a `git diff --exit-code` a `justfile`-ban marad.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_PLAN = _REPO_ROOT / "docs" / "megvalosulas" / "megvalosulas-02-adatbazis-ddl.md"
DEFAULT_OUT = _REPO_ROOT / "db" / "ddl" / "schema-v1.1.sql"

# **A MIGRÁCIÓS SQL-pillanatkép NEM generálható!**
#
# **A `0001_initial_schema.sql` egy FAGYASZTOTT pillanatkép** (a
# 2026-11-24-i sémaállapot) -> **a `test_migration_config.py` egy
# hardcoded SHA-256 digesttel őrzi** -> **a `0002` migráció a javítása**
# (a `drop_expired_partitions` a valós partíció-határokkal) ->
# **a fagyasztott `0001` NEM változhat** (a már futott migrációk nem
# módosulhatnak).
#
# **A `db/ddl/schema-v1.1.sql` viszont a `02` tervből generált** ->
# **az a LEGFRISSEBB séma** -> **a `just ddl-diff` ezt ellenőrizi** ->
# **a `0001` + a `0002` + a `0003` együtt adja a DB tényleges
# állapotát.**
#
# **A `02` terv a `drop_expired_partitions` függvényt tartalmazza**
# -> **a terv a legfrissebb állapotot mutatja** -> **a `db/ddl` és a
# `02` egyezik** -> **a `0001` a pillanatkép** -> **a `0002` a delta**.

# **a generált fájlok listája** -> **a `--check` mindet ellenőrzi**
OUTPUTS = (DEFAULT_OUT,)

HEADER = """\
-- A vessel-tracker sémája — GENERÁLT FÁJL, NE MODDÍTSD KÉZZEL!
--
-- A forrás: docs/megvalosulas/megvalosulas-02-adatbazis-ddl.md
--            (a 02-es DDL-terv SQL-blokkjaival)
-- A generátor: db/tools/gen_ddl.py
-- A CI-ellenőrzés: a `just ddl-diff` (a 07 §8.1 10b. lépése)
--
-- **A terv módosításakor a `just ddl-generate` futtatása kötelező**,
-- különben a `git diff --exit-code` elbukik a CI-ban.

"""


def extract_ddl(md_text: str) -> str:
    """A ```sql blokkok kivonása a terv-markdown-ból.

    Ugyanaz a logika, mint a `db/tools/validate_ddl.py`
    `extract_ddl()` függvényében → **a validált sémia és a
    generált fájl mindig ugyanaz.**
    """
    blocks = re.findall(r"```sql\n(.*?)```", md_text, re.S)
    return "\n;\n".join(b.strip() for b in blocks)


def build(plan: pathlib.Path) -> str:
    """A generált SQL szövege (a headerrel együtt)."""
    if not plan.exists():
        print(f"HIBA: a terv nem található: {plan}", file=sys.stderr)
        raise SystemExit(2)
    md = plan.read_text(encoding="utf-8")
    ddl = extract_ddl(md)
    if not ddl.strip():
        print(f"HIBA: a tervben nincs ```sql blokk: {plan}", file=sys.stderr)
        raise SystemExit(2)
    n_tables = len(re.findall(r"CREATE TABLE", ddl))
    n_idx = len(re.findall(r"CREATE (?:UNIQUE )?INDEX", ddl))
    return f"{HEADER}-- a táblák: {n_tables} | az indexek: {n_idx}\n\n{ddl}\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--plan",
        type=pathlib.Path,
        default=DEFAULT_PLAN,
        help="a forrás terv (a default a 02-es DDL-terv)",
    )
    ap.add_argument(
        "--out",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help="a generált fájl (a default a db/ddl/schema-v1.1.sql)",
    )
    ap.add_argument(
        "--check", action="store_true", help="nem ír, csak ellenőrzi (a CI-ban a `just ddl-diff`)"
    )
    ap.add_argument("--stdout", action="store_true", help="a tartalom a stdout-ra (a diffhez)")
    args = ap.parse_args()

    content = build(args.plan)

    if args.stdout:
        sys.stdout.write(content)
        return 0

    # **A `--out` a kompatibilitas miatt megmarad** -> **de a
    # `--check` es az iras MINDIG a `OUTPUTS` listan megy** ->
    # **a migracios SQL-pillanatkep is ellenorizett es generalt.**
    targets = OUTPUTS if args.out == DEFAULT_OUT else (args.out,)

    if args.check:
        drift = False
        for out in targets:
            if not out.exists():
                print(f"HIBA: a generált fájl nem létezik: {out}")
                print("  a javítás: `just ddl-generate`")
                drift = True
                continue
            cur = out.read_text(encoding="utf-8")
            if cur != content:
                print(f"HIBA: a generált séma eltér a tervtől: {out}")
                print(f"  a terv:  {args.plan}")
                print("  a javítás: `just ddl-generate` (a fájl újraírása)")
                drift = True
        if drift:
            return 1
        names = ", ".join(o.name for o in targets)
        print(f"OK: a generált séma egyezik a tervvel ({names})")
        return 0

    for out in targets:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        n = len(content.splitlines())
        print(f"OK: a séma generálva: {out} ({n} sor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
