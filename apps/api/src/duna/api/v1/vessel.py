"""A katalógus router (a 03 §3.1).

**A `GET /api/v1/vessels`:** a katalógus listája, szűréssel és
lapozással (a F-CAT-02, a F-CAT-08, a F-CAT-10, a F-CAT-14).

**A szűrők a query stringben** (a 03 §3.1) → **a `area` KÖTELEZŐ**
(a F-CAT-01: a két katalógus elkülönül).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.repositories.vessel_repo import VesselFilters, list_vessels
from duna.schemas.common import Page, PageMeta
from duna.schemas.vessel import VesselListItem

router = APIRouter(prefix="/vessels", tags=["vessels"])


@router.get("", response_model=Page[VesselListItem])
async def list_vessels_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    area: Annotated[str, Query(description="a terulet: 'duna' | 'balaton'")],
    lang: Annotated[str, Query(description="a nyelv kódja")] = "hu",
    q: Annotated[str | None, Query(description="a kereso")] = None,
    type_code: Annotated[str | None, Query(alias="type")] = None,
    operator_id: Annotated[int | None, Query(alias="operator")] = None,
    status: Annotated[str | None, Query()] = None,
    verification: Annotated[str | None, Query()] = None,
    sort: Annotated[str, Query()] = "name",
    order: Annotated[str, Query()] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[VesselListItem]:
    """A katalóguslista (a F-CAT-02).

    **A `meta.total` a szűrés utáni teljes darabszám** (a 03 §5.5) →
    **a `q` keresésnél `None`** (a trigram-alapú keresés nem
    indexelhető).
    """
    filters = VesselFilters(
        area=area,
        lang=lang,
        q=q,
        type_code=type_code,
        operator_id=operator_id,
        status=status,
        verification=verification,
        sort=sort,
        order=order,
        page=page,
        per_page=per_page,
    )
    items, total = await list_vessels(session, filters)
    return Page[VesselListItem](
        data=items,
        meta=PageMeta(
            total=total,
            page=page,
            per_page=per_page,
            has_more=total is not None and page * per_page < total,
        ),
    )
