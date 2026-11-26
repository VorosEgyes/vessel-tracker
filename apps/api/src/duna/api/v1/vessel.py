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
from duna.repositories.vessel_repo import VesselFilters
from duna.schemas.common import Data, ObjectMeta, Page, PageMeta
from duna.schemas.vessel import (
    FieldOrigin,
    OwnershipPeriod,
    VesselAlias,
    VesselCertDetail,
    VesselDetail,
    VesselIdentifierDetail,
    VesselListItem,
)
from duna.services import vessel_service

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
    items, total = await vessel_service.list_catalog(session, filters)
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
    detail = await vessel_service.get_detail(session, vessel_id, lang)
    if detail is None:
        raise HTTPException(status_code=404, detail="a hajo nem talalhato")
    return Data[VesselDetail](data=detail, meta=ObjectMeta(total=1))


@router.get("/{vessel_id}/aliases", response_model=Page[VesselAlias])
async def get_vessel_aliases(
    vessel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[VesselAlias]:
    """A hajó **történeti** nevei (a F-DET-05).

    **A LEZÁRTak** (`valid_to IS NOT NULL`) → **a jelenlegi név a
    `vessel_i18n`-ből jön** (a `03` §3.1) → **nem duplikálódik.**
    """
    items = await vessel_service.get_aliases(session, vessel_id)
    return Page[VesselAlias](
        data=items,
        meta=PageMeta(total=len(items), page=1, per_page=len(items), has_more=False),
    )


@router.get("/{vessel_id}/ownership", response_model=Page[OwnershipPeriod])
async def get_vessel_ownership(
    vessel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    lang: Annotated[str, Query(description="a nyelv kódja")] = "hu",
) -> Page[OwnershipPeriod]:
    """A **tulajdonosváltások** (a F-DET-05) → **a dátumtartománnyal**
    → **a legújabb elöl.**
    """
    items = await vessel_service.get_ownership(session, vessel_id, lang)
    return Page[OwnershipPeriod](
        data=items,
        meta=PageMeta(total=len(items), page=1, per_page=len(items), has_more=False),
    )


@router.get("/{vessel_id}/certificates", response_model=Page[VesselCertDetail])
async def get_vessel_certificates(
    vessel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[VesselCertDetail]:
    """A hajó engedélyei (a F-DET-02).

    **Szűrés NÉLKÜL** (a `03` §3.1) → **az aktív + a lezárt
    engedélyek egyaránt.**
    """
    items = await vessel_service.get_certificates(session, vessel_id)
    return Page[VesselCertDetail](
        data=items,
        meta=PageMeta(total=len(items), page=1, per_page=len(items), has_more=False),
    )


@router.get("/{vessel_id}/identifiers", response_model=Page[VesselIdentifierDetail])
async def get_vessel_identifiers(
    vessel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[VesselIdentifierDetail]:
    """Az összes azonosító + eredet (a F-DET-02, a F-DET-15).

    **Szűrés NÉLKÜL** (a `03` §3.1) → **az aktív + a lezárt
    azonosítók egyaránt** → **a `valid_to` megmutatja, melyik aktív.**
    """
    items = await vessel_service.get_identifiers(session, vessel_id)
    return Page[VesselIdentifierDetail](
        data=items,
        meta=PageMeta(total=len(items), page=1, per_page=len(items), has_more=False),
    )


@router.get("/{vessel_id}/data-origin", response_model=Page[FieldOrigin])
async def get_vessel_data_origin(
    vessel_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[FieldOrigin]:
    """A mezőnkénti eredet (a F-DET-15).

    **Csak az aktuális források** (`is_current`) → **a történeti
    források a `vessel_data_origin`-ban maradnak, de nem jelennek meg.**
    """
    items = await vessel_service.get_origins(session, vessel_id)
    return Page[FieldOrigin](
        data=items,
        meta=PageMeta(total=len(items), page=1, per_page=len(items), has_more=False),
    )
