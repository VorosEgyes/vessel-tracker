#!/usr/bin/env python3
"""Az ORM modellek ellenőrzése a DB-sémához (a 03 §5.1a).

**A `03` szerint a `db/models.py` a `02`-es terv ORM-reprezentációja**,
és **a séma migrációkból generálódik** → **nincs kézi másolat.**
Egyelőre a modellek kézzel vannak megírva → **ez a script ellenőrzi,
hogy a kézi modellek megfelelnek a valós sémának.**

**Miért kell:** a kézi modellek könnyen elcsúsznak (a `country.name`
vs. `name_local`, az `operator.legal_name`, a `port` nevének a
`port_i18n`-ben való léte) → **ez a hiba a runtime-ban (a `INSERT`/
`SELECT` elbukik) jelenik meg, nem a tesztben** → **a CI-ban fut,
a `just check` részeként.**

**A forrás:** a `db/ddl/schema-v1.1.sql` (a generált séma) → **a
`CREATE TABLE` blokkokból a táblák és az oszlopok** → **a
`models.py`-ben definiált ORM-oszlopok** → **az összevetés.**

**A `just models-check` recept** → **a CI-ban a `just db-migrate`
után** → **a séma a valós PostgreSQL-en van** → **a `CREATE TABLE`
a `information_schema`-ból is olvasható** → **a DB-ből olvasunk,
nem a fájlból** → **a `pg_cron`/a preprocesszorok nem számítanak.**

Hasznalat:
    just models-check
"""

from __future__ import annotations

import os
import sys

# **az ORM modellek betöltése** (a `Base.metadata` a forrás)
from duna.db.models import Base


def db_columns() -> dict[str, dict[str, bool]]:
    """A valós DB táblái, oszlopai és a NOT NULL jellegük.

    **A DB-ből olvasunk** (nem a fájlból) → **a migráció utáni valós
    állapotot ellenőrizzük** → **a `pg_cron`/a preprocesszorok
    nem befolyásolják** (azok nem oszlopokat hoznak létre).

    **A visszatérés:** `{tabla: {oszlop: not_null}}`.
    """
    import sqlalchemy as sa

    from duna.config import get_settings

    settings = get_settings()
    engine = sa.create_engine(settings.sync_database_url, poolclass=sa.pool.NullPool)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT table_name, column_name, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "ORDER BY table_name, column_name"
                )
            ).all()
            # **a `GENERATED ALWAYS AS IDENTITY` oszlopok** -> **a
            # `information_schema` szerint nem NOT NULL** -> **a
            # `is_identity` alapján szűrjük ki a primary keyeket
            identity = {
                (t, c)
                for t, c in conn.execute(
                    sa.text(
                        "SELECT table_name, column_name "
                        "FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND is_identity = 'YES'"
                    )
                ).all()
            }
            # **a DEFAULTdal rendelkezo NOT NULL oszlopok** -> **a DB
            # tolti ki** -> **nem kell a modellben lenniuk** ->
            # **a `created_at`/`updated_at` a `DEFAULT now()` miatt
            # ilyen** (a 02 §4.3)
            with_default = {
                (t, c)
                for t, c in conn.execute(
                    sa.text(
                        "SELECT table_name, column_name "
                        "FROM information_schema.columns "
                        "WHERE table_schema = 'public' "
                        "AND column_default IS NOT NULL"
                    )
                ).all()
            }
    finally:
        engine.dispose()

    tables: dict[str, dict[str, bool]] = {}
    for table_name, column_name, is_nullable in rows:
        not_null = (
            is_nullable == "NO"
            and (table_name, column_name) not in identity
            and (table_name, column_name) not in with_default
        )
        tables.setdefault(table_name, {})[column_name] = not_null
    return tables


def model_tables() -> dict[str, dict[str, bool]]:
    """A `models.py`-ben definiált ORM-táblák és oszlopok.

    **A visszatérés:** `{tabla: {oszlop: nullable}}`.
    """
    tables: dict[str, dict[str, bool]] = {}
    for table in Base.metadata.tables.values():
        tables[table.name] = {col.name: bool(col.nullable) for col in table.columns}
    return tables


def main() -> int:
    """A modellek ellenőrzése."""
    if not os.environ.get("DATABASE_URL"):
        print("a DATABASE_URL nincs beallitva -> a models-check kihagyva")
        return 0

    db = db_columns()
    models = model_tables()

    errors: list[str] = []

    for name in sorted(models):
        if name not in db:
            errors.append(f"a modellben van, a DB-ben nincs: {name}")
            continue

        # --- 1) a modell oszlopai legyenek a DB oszlopai ---
        # (a modell egy oszlopa, ami a DB-ben nincs -> az `INSERT`/`SELECT`
        # elbukna: pl. a `country.name` vs. a `name_local`)
        missing = set(models[name]) - set(db[name])
        if missing:
            errors.append(f"a {name} modellben nincs a DB oszlop: {', '.join(sorted(missing))}")

        # --- 2) a DB NOT NULL oszlopai legyenek a modellben ---
        # (egy hiányzó NOT NULL oszlop -> az `INSERT` elbukna nullaval:
        # pl. az `operator.legal_name`)
        required = {col for col, not_null in db[name].items() if not_null}
        absent = required - set(models[name])
        if absent:
            errors.append(
                f"a {name} modellben nincs a DB NOT NULL oszlop: {', '.join(sorted(absent))}"
            )

    if errors:
        print("A MODELLEK NEM MEGFELELOEK A SEMAHoz:")
        for e in errors:
            print(f"  - {e}")
        print()
        print(
            "**A `db/models.py` a `02` DDL ORM-reprezentacioja** -> "
            "a `models.py`-ben a hianyz oszlopot hozzá kell adni "
            "(a `03` §5.1a)."
        )
        return 1

    print(
        f"a modellek megfelelnek a semanak ({len(models)} tabla, "
        f"{sum(len(c) for c in models.values())} oszlop)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
