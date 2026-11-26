"""A fordítás-fallback-lánc (a 03 §5.1, §6.3 — a F-INTL-05).

**A LÁNC (a README 4.4 szerint):**
```
a kért nyelv  ->  en  ->  hu  ->  a kód / az eredeti érték
```

**A `content_text` eseten a `status='published'` a KAPU** (a 03 §6.2a,
a C-5 finding) -> **a nem publikalt forditas NEM lathato** a publikus
API-n -> **a kulcs, amelynek nincs publikalt forditasa -> **a 404
`not-found`** (nem 403 -> **a publikus API nem arulja el, hogy a
kulcs letezik-e csak a szerkesztoknek**).

**A `translation_fallback` a `meta`-ban van**, nem a `data`-ban ->
**a kliens nem keveri a "nincs adat" es a "nincs forditas" esetet.**

**A `en` a `hu` ELOTT jön** (a `prof` reviewer C-2 findingje) ->
**a `README` 4.4 lancaja szerint az `en` a nemzetkezi visszaeses.**
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from duna.db.models import ContentText

# **A LÁNC (a README 4.4)** -> **a `?lang=` nem az elso, ez a
# visszaesesi sorrend.**
FALLBACK_CHAIN = ("en", "hu")


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """A fordítás eredménye (a tartalom + a fallback-jelölés).

    **A `missing` a F-DET-16 "adat nelkul" jelolese** -> **a UI
    ures helyett ezt mutatja.**
    """

    text: str | None
    used_lang: str | None
    fallback: bool
    missing: bool = False

    def to_meta(self) -> dict[str, object]:
        """**A `meta.translation_fallback` mezője** (a 03 §6.3)."""
        return {
            "requested": self.requested,
            "used": self.used_lang,
            "fallback": self.fallback,
            **({"missing": True} if self.missing else {}),
        }

    requested: str = "hu"


async def resolve_content(
    session: AsyncSession, content_key: str, requested_lang: str
) -> TranslationResult | None:
    """A tartalmi kulcs fordításának feloldása (a `03` §6.3).

    **A `None`, ha a kulcsnak nincs PUBLIKÁLT fordítása semmilyen
    nyelven** -> **a router 404 `not-found`-ot ad** (a `03` §6.2a).

    **A `status='published'` a szűrő** (a C-5 finding) -> **a
    `draft`/`review` fordítás nem látható.**
    """
    # --- a kert nyelv ---
    stmt = (
        select(ContentText.text, ContentText.lang)
        .where(
            (ContentText.content_key == content_key)
            & (ContentText.lang == requested_lang)
            & (ContentText.status == "published")
        )
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is not None:
        return TranslationResult(
            text=row.text,
            used_lang=row.lang,
            fallback=False,
            requested=requested_lang,
        )

    # --- a visszaesesi lanc ---
    for lang in FALLBACK_CHAIN:
        if lang == requested_lang:
            continue
        stmt = (
            select(ContentText.text, ContentText.lang)
            .where(
                (ContentText.content_key == content_key)
                & (ContentText.lang == lang)
                & (ContentText.status == "published")
            )
            .limit(1)
        )
        row = (await session.execute(stmt)).first()
        if row is not None:
            return TranslationResult(
                text=row.text,
                used_lang=row.lang,
                fallback=True,
                requested=requested_lang,
            )

    # --- nincs semmi -> a F-DET-16 "adat nelkul" jelolese ---
    return TranslationResult(
        text=None,
        used_lang=None,
        fallback=False,
        missing=True,
        requested=requested_lang,
    )
