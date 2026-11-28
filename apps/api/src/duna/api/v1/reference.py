"""Reference catalog endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.schemas.common import Data, Page
from duna.schemas.reference import (
    Basin,
    CargoType,
    Lock,
    LockDetail,
    Operator,
    Port,
    PortDetail,
    RiverSection,
    Route,
    VesselType,
    Waterway,
)
from duna.services import reference_service


def reject_unknown_query_parameters(request: Request) -> None:
    route = request.scope["route"]
    allowed = {param.alias for param in route.dependant.query_params}
    unknown = set(request.query_params) - allowed
    if unknown:
        raise HTTPException(
            status_code=422, detail=f"nem tamogatott parameterek: {', '.join(sorted(unknown))}"
        )


router = APIRouter(tags=["reference"], dependencies=[Depends(reject_unknown_query_parameters)])
Session = Annotated[AsyncSession, Depends(get_session)]
Language = Annotated[str, Query(min_length=2, max_length=2)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=200)]


@router.get("/ports", response_model=Page[Port])
async def ports(
    session: Session,
    lang: Language = "hu",
    page: PageNumber = 1,
    per_page: PageSize = 50,
    waterway_id: Annotated[int | None, Query(ge=1)] = None,
    port_type: str | None = None,
    country_code: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    q: Annotated[str | None, Query(min_length=1)] = None,
) -> Page[Port]:
    if q is not None and not q.strip():
        raise HTTPException(status_code=422, detail="a keresoszoveg nem lehet ures")
    filters = {
        k: v
        for k, v in {
            "waterway_id": waterway_id,
            "port_type": port_type,
            "country_code": country_code,
            "q": q,
        }.items()
        if v is not None
    }
    return await reference_service.list_items(
        session, "ports", Port, lang, page, per_page, filters=filters
    )


@router.get("/ports/{id}", response_model=Data[PortDetail])
async def port_detail(
    session: Session, lang: Language = "hu", port_id: int = Path(alias="id")
) -> Data[PortDetail]:
    result = await reference_service.get_item(session, "ports", PortDetail, port_id, lang)
    if result is None:
        raise HTTPException(status_code=404, detail="a kikoto nem talalhato")
    return result


@router.get("/locks", response_model=Page[Lock])
async def locks(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[Lock]:
    return await reference_service.list_items(session, "locks", Lock, lang, page, per_page)


@router.get("/locks/{id}", response_model=Data[LockDetail])
async def lock_detail(
    session: Session, lang: Language = "hu", lock_id: int = Path(alias="id")
) -> Data[LockDetail]:
    result = await reference_service.get_item(session, "locks", LockDetail, lock_id, lang)
    if result is None:
        raise HTTPException(status_code=404, detail="a zsilip nem talalhato")
    return result


@router.get("/waterways", response_model=Page[Waterway])
async def waterways(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[Waterway]:
    return await reference_service.list_items(session, "waterways", Waterway, lang, page, per_page)


@router.get("/river-sections", response_model=Page[RiverSection])
async def river_sections(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[RiverSection]:
    return await reference_service.list_items(
        session, "river-sections", RiverSection, lang, page, per_page
    )


@router.get("/basins", response_model=Page[Basin])
async def basins(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[Basin]:
    return await reference_service.list_items(session, "basins", Basin, lang, page, per_page)


@router.get("/vessel-types", response_model=Page[VesselType])
async def vessel_types(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[VesselType]:
    return await reference_service.list_items(
        session, "vessel-types", VesselType, lang, page, per_page
    )


@router.get("/operators", response_model=Page[Operator])
async def operators(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[Operator]:
    return await reference_service.list_items(session, "operators", Operator, lang, page, per_page)


@router.get("/routes", response_model=Page[Route])
async def routes(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[Route]:
    return await reference_service.list_items(session, "routes", Route, lang, page, per_page)


@router.get("/cargo-types", response_model=Page[CargoType])
async def cargo_types(
    session: Session, lang: Language = "hu", page: PageNumber = 1, per_page: PageSize = 50
) -> Page[CargoType]:
    return await reference_service.list_items(
        session, "cargo-types", CargoType, lang, page, per_page
    )
