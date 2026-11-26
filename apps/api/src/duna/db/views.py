"""A DB nézetek (a `02` §6.2, §6.3a) — a SQLAlchemy `Table`-ek.

**A nézetek NEM ORM-modellek** → **a `Table`-ek a `Base.metadata`-ba
kerülnek** (a `extend_existing=True` nélkül) → **egy modulban
 definiálva**, hogy két repository ne duplikálja a definíciót (a
SQLAlchemy `InvalidRequestError`-t dobna).

**A nézetek:**
- a `vessel_verification` (a `02` §6.2) → **a számított
  bizonyossági szint + az `is_stale` eltérés jelzése**;
- a `vessel_last_position` (a `02` §6.3a) → **a legfrissebb pozíció
  hajónként** (a `DISTINCT ON (vessel_id)`).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Numeric, String, Table

from duna.db.models import Base

# **a `vessel_verification` nézet** (a 02 §6.2)
VESSEL_VERIFICATION = Table(
    "vessel_verification",
    Base.metadata,
    Column("vessel_id", BigInteger, primary_key=True),
    Column("computed_verification_level", String),
    Column("is_stale", Boolean),
    extend_existing=True,
)

# **a `vessel_last_position` nézet** (a 02 §6.3a) -> **a legfrissebb
# pozíció hajónként** (a `river_km`, a `river_section_id`, a `ts`)
VESSEL_LAST_POSITION = Table(
    "vessel_last_position",
    Base.metadata,
    Column("vessel_id", BigInteger, primary_key=True),
    Column("ts", DateTime(timezone=True)),
    Column("river_km", Numeric(8, 2)),
    Column("river_section_id", BigInteger),
    Column("basin_id", BigInteger),
    extend_existing=True,
)
