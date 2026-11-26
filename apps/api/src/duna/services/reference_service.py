"""Reference catalog service."""

from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from duna.repositories.reference_repo import ReferenceKind, get_reference, list_reference
from duna.schemas.common import Data, ObjectMeta, Page, PageMeta


async def list_items[T: BaseModel](
    session: AsyncSession,
    kind: ReferenceKind,
    model: type[T],
    lang: str,
    page: int,
    per_page: int,
    *,
    filters: dict[str, Any] | None = None,
) -> Page[T]:
    rows, total = await list_reference(session, kind, lang, page, per_page, filters=filters)
    return Page[T](
        data=[model.model_validate(row) for row in rows],
        meta=PageMeta(total=total, page=page, per_page=per_page, has_more=page * per_page < total),
    )


async def get_item[T: BaseModel](
    session: AsyncSession,
    kind: Literal["ports", "locks"],
    model: type[T],
    object_id: int,
    lang: str,
) -> Data[T] | None:
    row = await get_reference(session, kind, object_id, lang)
    if row is None:
        return None
    return Data[T](data=model.model_validate(row), meta=ObjectMeta(total=1))
