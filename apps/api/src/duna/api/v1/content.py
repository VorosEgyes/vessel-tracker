"""A tartalom router (a 03 §3.4 — a F-NF-01…15).

**A `GET /api/v1/content/{key}`** → **a tartalmi kulcs fordítása** →
**a fallback-lánc szerint** (a `03` §6.3) → **a `meta.translation_fallback`
jelzi, ha nem a kért nyelven jött.**

**A `status='published'` a KAPU** (a `03` §6.2a, a C-5 finding) →
**a nem publikált fordítás nem látható** → **a kulcs, amelynek nincs
publikált fordítása → **a 404 `not-found`** (nem 403 → **a publikus
API nem árulja el, hogy a kulcs létezik-e csak a szerkesztőknek**).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.session import get_session
from duna.schemas.common import Data, ObjectMeta, TranslationFallback
from duna.services import content_service

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/{key}", response_model=Data[dict[str, str | None]])
async def get_content(
    session: Annotated[AsyncSession, Depends(get_session)],
    lang: Annotated[str, Query(description="a nyelv kódja")] = "hu",
    content_key: str = Path(alias="key"),
) -> Data[dict[str, str | None]]:
    """Egy tartalmi kulcs fordítása (a F-NF-01…15).

    **A `meta.translation_fallback`** → **a `requested`, a `used` és
    a `fallback` flag** (a `03` §6.3).

    **A 404**, ha a kulcsnak nincs publikált fordítása (a `03` §6.2a).
    """
    result = await content_service.resolve_content(session, content_key, lang)
    if result is None or result.missing:
        raise HTTPException(status_code=404, detail="a tartalom nem talalhato")

    return Data[dict[str, str | None]](
        data={"text": result.text},
        meta=ObjectMeta(
            total=1,
            translation_fallback={
                "text": TranslationFallback(
                    requested=result.requested,
                    used=result.used_lang,
                    fallback=result.fallback,
                    missing=result.missing,
                )
            },
        ),
    )
