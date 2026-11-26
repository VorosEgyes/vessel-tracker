"""A katalógus router (a 03 §3.1).

**A `GET /api/v1/vessels`:** a katalógus listája, szűréssel és
lapozással (a F-CAT-02, a F-CAT-08, a F-CAT-10, a F-CAT-14).

**A szűrők a query stringben** (a 03 §3.1) → **a `area` KÖTELEZŐ**
(a F-CAT-01: a két katalógus elkülönül).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.repositories.vessel_detail_repo import get_vessel_detail
from duna.repositories.vessel_repo import VesselFilters, list_vessels
from duna.schemas.common import Data, ObjectMeta, Page, PageMeta
from duna.schemas.vessel import VesselDetail, VesselListItem

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


@router.get("/{vessel_id}", response_model=Data[VesselDetail])
async def get_vessel_endpoint(
    vessel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    lang: Annotated[str, Query(description="a nyelv kódja")] = "hu",
) -> Data[VesselDetail]:
    """A hajó adatlapja (a F-DET-01…16).

    **A `meta.total` `None`** (egy objektum nincs lapozva) → **a
    `Data[T]` burkoló a `03` §5.5 szerint** (a `Page[T]` csak
    listához való).

    **A `404`, ha nincs ilyen hajó.**
    """
    detail = await get_vessel_detail(session, vessel_id, lang)
    if detail is None:
        raise HTTPException(status_code=404, detail="a hajo nem talalhato")
    return Data[VesselDetail](data=detail, meta=ObjectMeta(total=1))
