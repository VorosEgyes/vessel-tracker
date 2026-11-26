"""A kereső router (a 03 §3.2 — a F-SRCH-01…07).

**A `GET /api/v1/search`** → **a globális kereső** → **az `area`
KÖTELEZŐ** (a `prof` reviewer M-5 findingje) → **a `q` minimális
hossza 2 karakter** (a `Query(min_length=2)` → **a 422
`validation-error`**).

**A `meta.area_hint`** (a `bori` reviewer H-2 findingje) → **az üres
eredmény mellett jelzi, hogy a másik területen van találat** → **a
darabszám nélkül** (a terület-szivárgás tiltása, a `release-terv` 3.5).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.repositories.search_repo import SearchParams, search
from duna.schemas.common import AreaHint, Page, PageMeta
from duna.schemas.vessel import VesselListItem

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=Page[VesselListItem])
async def search_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str, Query(min_length=2, description="a keresoszove")],
    area: Annotated[str, Query(description="a terulet: 'duna' | 'balaton'")],
    lang: Annotated[str, Query(description="a nyelv kódja")] = "hu",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[VesselListItem]:
    """A globális kereső (a F-SRCH-01…07).

    **A sorrend** (a 03 §3.2): **először a pontos azonosító-egyezés**
    (a `vessel_identifier`-ben) → **aztán a név-egyezés** (a
    `vessel.sort_name`-en, ékezet-független).

    **A `meta.total`** a trigram-alapú néven keresésnél `None` → **a
    pontos azonosító-egyezésnél a pontos darabszám.**
    """
    params = SearchParams(area=area, q=q, lang=lang, limit=limit)
    items, total, other_has_matches = await search(session, params)

    return Page[VesselListItem](
        data=items,
        meta=PageMeta(
            total=total,
            page=1,
            per_page=limit,
            has_more=False,
            area_hint=(
                AreaHint(
                    other_area="balaton" if area == "duna" else "duna",
                    has_matches=other_has_matches,
                )
                if not items
                else None
            ),
        ),
    )
