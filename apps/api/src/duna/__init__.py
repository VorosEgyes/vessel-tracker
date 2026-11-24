"""A `duna` alkalmazáscsomag (a 01 – stack-terv §4.2).

**A src-layout:** a `duna` a `apps/api/src/duna/` alatt van, és a
`pyproject.toml` `src = ["apps/api/src", ...]` beállítása miatt
importálható (`from duna.domain...`).

**A rétegek** (a 01 §4.2):
- a `domain/` — a tiszta függvények (nincs DB, nincs HTTP) → **a
  unit tesztek itt futnak** (a 08 §2.1);
- a `ingest/` — az AIS parser + a pipeline (a 04);
- a `api/` — a FastAPI routerek (a 03);
- a `db/` — a session, a modellek (a 02);
- a `repositories/` — a SQLAlchemy query-k;
- a `services/` — a use-case-ek.

**Most (2026-11-24):** csak a `domain/verification.py` létezik — a
legkisebb, legjobban tesztelhető egység (a 03 §5.4, a 02 §6.2 nézet,
az 05 §8.2 badge).
"""

__version__ = "0.1.0"
