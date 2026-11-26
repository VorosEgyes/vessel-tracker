"""A burkoló modellek (a 03 §5.5).

**Két típus van a `data` mezőnek** — lista-válaszon `list[T]`,
objektum-válaszon `T` → **egyetlen `Page[T]` nem elég** (a `prof`
reviewer L-4 findingje) → **két generikus burkoló.**
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PageMeta(BaseModel):
    """A lapozás metaadatai."""

    model_config = ConfigDict(from_attributes=True)

    total: int | None = Field(
        default=None,
        description=(
            "a szűrés UTÁNI teljes darabszám (a lapozás nélkül); "
            "a trigram-alapú q-keresésnél null (nem indexelhető)"
        ),
    )
    page: int = Field(default=1, description="az oldalszám (1-alapú)")
    per_page: int = Field(default=50, description="az oldal elemszáma")
    has_more: bool = Field(default=False, description="van-e a következő oldal")


class ObjectMeta(BaseModel):
    """Az objektum-válasz metaadatai (a lapozás nélkül)."""

    model_config = ConfigDict(from_attributes=True)

    total: int | None = Field(default=None)


class Page[T](BaseModel):
    """A lista-válasz burkolója."""

    model_config = ConfigDict(from_attributes=True)

    data: list[T]
    meta: PageMeta


class Data[T](BaseModel):
    """Az objektum-válasz burkolója."""

    model_config = ConfigDict(from_attributes=True)

    data: T
    meta: ObjectMeta
