"""A burkoló modellek (a 03 §5.5).

**Két típus van a `data` mezőnek** — lista-válaszon `list[T]`,
objektum-válaszon `T` → **egyetlen `Page[T]` nem elég** (a `prof`
reviewer L-4 findingje) → **két generikus burkoló.**
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AreaHint(BaseModel):
    """A terület-hint (a `bori` reviewer H-2 findingje).

    **A `not-found-in-area` hibakód KIKERÜLT** (a terület-szivárgás
    tiltása, a `release-terv` 3.5) → **az üres eredmény a `meta`-ban
    egy `area_hint`-et ad** → **a felhasználó tudja, hogy területet
    kell váltania, de NEM tudja meg, melyik hajóról van szó** (a
    darabszám szándékosan nincs).
    """

    model_config = ConfigDict(from_attributes=True)

    other_area: str = Field(description="a masik terulet: 'duna' | 'balaton'")
    has_matches: bool = Field(description="van-e talalat a masik teruleten (a darabszam nelkul)")


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
    area_hint: AreaHint | None = Field(
        default=None,
        description=(
            "a kereso eredmenye: a masik teruleten van-e talalat "
            "(a `bori` H-2 findingje — a darabszam nelkul, hogy ne "
            "legyen terulet-szivargas)"
        ),
    )


class TranslationFallback(BaseModel):
    """A fordítás-fallback jelölése (a 03 §6.3 — a F-INTL-05).

    **A `meta`-ban van**, nem a `data`-ban → **a kliens nem keveri a
    "nincs adat" és a "nincs fordítás" esetet.**

    **A `missing: true` a F-DET-16 "adat nélkül" jelölése** → **a UI
    üres helyett ezt mutatja.**
    """

    model_config = ConfigDict(from_attributes=True)

    requested: str = Field(description="a kert nyelv")
    used: str | None = Field(default=None, description="a hasznalt nyelv")
    fallback: bool = Field(default=False, description="a szoveg a kert nyelven helyett jott")
    missing: bool = Field(default=False, description="nincs forditas sem a lancban (a F-DET-16)")


class ObjectMeta(BaseModel):
    """Az objektum-válasz metaadatai (a lapozás nélkül)."""

    model_config = ConfigDict(from_attributes=True)

    total: int | None = Field(default=None)
    translation_fallback: dict[str, TranslationFallback] | None = Field(
        default=None,
        description="a mezonkenti forditas-fallback jelolese (a 03 §6.3)",
    )


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
