"""A havi partíciók létrehozása (a `02` §8.1 — a hiányzó bootstrap).

**A PROBLEMÁK:** a `02` csak **egy** konkrét partíciót definiál
(`position_p20261101`) + **a `default` partíciót** -> **a `pg_cron`
jobok CSAK a TTL-törlést ütemezik** (a `02` §8.1) -> **a havi
partíciókat SENKI nem hozza létre** -> **a betöltés a `default`
partícióba kerülne** -> **a TTL törölné azokat** (a `0002` migráció
a `default` partíciót `DELETE`-szel üríti, nem dobja el) -> **a
régi adatok elvesznek.

**A MEGOLDÁS:** **a `ensure_partitions()`** a betöltés előtt
létrehozza a szükséges havi partíciókat.

**A KONVENCIÓ (a `02` §8.1):** `<tabla>_pYYYYMMDD` (a havi
partíció a hónap 1-jén kezdődik) -> **a határ: `FROM '<hónap 1.>'
TO '<köv hónap 1.>'`**.

**A `default` partíció a tartalék:** **a nem ide tartozó
(`NULL`/`Infinity`) sorok oda kerülnek** -> **a PostgreSQL
partition-ellenőrzése miatt** -> **a betöltés a konkrét havi
partícióba ír** (a `default` csak a hibás `ts`-ű soroké).

**A `position` a `ts` szerint, az `ais_message_raw` a `received_at`
szerint, a `water_level` a `ts` szerint** partícionált (a `02` §5.1).
"""

from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import Connection, text

# **a partícionált táblák és a particiok oszlopa** (a 02 §5.1)
PARTITIONED_TABLES = {
    "position": "ts",
    "ais_message_raw": "received_at",
    "water_level": "ts",
}

# **a konkrét particiok a `02`-ben** (a `position_p20261101` a
# `2026-11-01` -> `2026-12-01` hatarral) -> **a `default` mellett
# ezek maradnak**
_NAME_RE = re.compile(r"^(?P<table>\w+)_p(?P<ym>\d{6})$")


def _month_bounds(ym: str) -> tuple[str, str]:
    """**A `YYYYMM` -> a hatarok** (a `FROM`/`TO` szovege).

    **A hónap eleje és a következő hónap eleje** (a PostgreSQL
    `FOR VALUES FROM ... TO ...` a hatar FELZART, a kezdet nyilt).
    """
    year = int(ym[:4])
    month = int(ym[4:])
    start = dt.date(year, month, 1)
    end = dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def ensure_partitions(
    conn: Connection,
    table: str,
    months: list[str],
    *,
    schema: str = "public",
) -> list[str]:
    """**A havi partíciók létrehozása** (ha még nincsenek).

    **A visszatérés:** a létrehozott partíciók neve.

    **A `DEFAULT` partíció mellett** a PostgreSQL megengedi a további
    `FOR VALUES FROM ... TO ...` partíciókat -> **a `default` az
    utolsó, a `NULL`/`Infinity` soroké marad.**
    """
    if table not in PARTITIONED_TABLES:
        raise ValueError(f"nem particionalt tabla: {table}")

    created: list[str] = []
    for ym in sorted(set(months)):
        # **A KONVENCIÓ `pYYYYMMDD`** (a `02` §8.1: a `position_p20261101`
        # a `2026-11-01` -> `2026-12-01` hatarral) -> **a havi
        # particio a HONAP 1-JEN kezdodik** -> **a `p20261101` a
        # konvencio szerint NEV, nem egy kivetel**
        name = f"{table}_p{ym}01"
        start, end = _month_bounds(ym)
        # **a mar letezo -> nem hozzuk ujra**
        exists = conn.execute(
            text("SELECT 1 FROM pg_class WHERE relname = :name"),
            {"name": name},
        ).first()
        if exists:
            continue
        # **A HATAROK LITERALIS** (a PostgreSQL a `CREATE TABLE ...
        # PARTITION OF` hataraiban NEM enged parametrert) ->
        # **a `ym` a belso adat** (a datumbol jott) -> **nem a
        # felhasznaloi bemenet** -> **a behelyettesites biztonsagos**
        # (a `ym` a `_month_bounds` utan csak 6 számjegy lehet).
        conn.execute(
            text(
                f'CREATE TABLE "{schema}"."{name}" PARTITION OF "{schema}"."{table}" '
                f"FOR VALUES FROM ('{start}') TO ('{end}')"
            )
        )
        created.append(name)
    return created


def months_between(start: dt.datetime, end: dt.datetime) -> list[str]:
    """**A `start` és az `end` közötti hónapok** (`YYYYMM`).

    **A `position` a `ts` (a GNSS-idő) szerint partícionált** → **a
    hónap a `ts` alapján kell** (nem a betöltés ideje szerint).
    """
    months: list[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(f"{year:04d}{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return months
