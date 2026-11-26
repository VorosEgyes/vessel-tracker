"""A globális kereső (a 03 §5.1 — a F-SRCH-01…07).

**A service tartja a lekérdezést** -> **a router csak a
paramétereket validálja és a `response_model`-t adja vissza.**
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from duna.repositories.search_repo import SearchParams, search
from duna.schemas.vessel import VesselListItem


async def search_vessels(
    session: AsyncSession,
    area: str,
    q: str,
    lang: str = "hu",
    limit: int = 20,
) -> tuple[list[VesselListItem], int | None, bool]:
    """A globális kereső.

    **A visszatérés:** `(a találatok, a teljes darabszám vagy None,
    van-e találat a MÁSIK területen)` → **a `meta.area_hint`-hoz
    kell** (a `bori` reviewer H-2 findingje).
    """
    params = SearchParams(area=area, q=q, lang=lang, limit=limit)
    return await search(session, params)
