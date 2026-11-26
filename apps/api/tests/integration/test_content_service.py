"""A fordítás-fallback-lánc integrációs tesztje (a 03 §6.3 — a F-INTL-05).

**A LÁNC (a README 4.4):** `a kért nyelv -> en -> hu -> a kód`.

**A `status='published'` a KAPU** (a 03 §6.2a, a C-5 finding) -> **a
nem publikált fordítás NEM látható** a publikus API-n.

**A `translation_fallback` a `meta`-ban van**, nem a `data`-ban ->
**a kliens nem keveri a "nincs adat" és a "nincs fordítás" esetet.**
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from duna.main import app
from duna.services.content_service import resolve_content

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="a DATABASE_URL nincs beállítva -> az integrációs teszt kihagyva",
)


@pytest.fixture(scope="module")
def client():
    """A FastAPI kliens (a lifespan-t futtatja)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def seeded_content():
    """A tartalmi kulcsok (a `content_key` + a `content_text`)."""
    import asyncio

    async def _seed() -> None:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO content_key (key, domain, description, source_lang)"
                    " VALUES ('test.hello', 'ui', 'teszt', 'hu')"
                    " ON CONFLICT DO NOTHING"
                )
            )
            # **a magyar publikalt** (a `source_lang`)
            await conn.execute(
                text(
                    "INSERT INTO content_text (content_key, lang, text, status)"
                    " VALUES ('test.hello', 'hu', 'Szia', 'published')"
                    " ON CONFLICT DO NOTHING"
                )
            )
            # **az angol publikalt** (a koztes nyelv a lancban)
            await conn.execute(
                text(
                    "INSERT INTO content_text (content_key, lang, text, status)"
                    " VALUES ('test.hello', 'en', 'Hello', 'published')"
                    " ON CONFLICT DO NOTHING"
                )
            )
            # **a német NEM publikalt** (a draft -> nem lathato)
            await conn.execute(
                text(
                    "INSERT INTO content_text (content_key, lang, text, status)"
                    " VALUES ('test.hello', 'de', 'Hallo', 'draft')"
                    " ON CONFLICT DO NOTHING"
                )
            )
        await engine.dispose()

    asyncio.run(_seed())


def _resolve(lang: str, content_key: str = "test.hello"):
    """A service meghívása egy **saját eseménykörben** és a **saját
    session-jével**.

    **A `pytest-asyncio` `asyncio_mode = "auto"` miatt az async
    tesztek is futhatnak** → **a legegyszerűbb: a service-t egy
    szinkron helper hívja**, ami megnyitja a kapcsolatot, lefuttatja
    a hívást, és lezárja.
    """
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    async def _run():
        engine = create_async_engine(os.environ["DATABASE_URL"])
        try:
            async with engine.connect() as conn:
                session = AsyncSession(bind=conn)
                return await resolve_content(session, content_key, lang)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def test_a_kert_nyelven_van_a_forditas(seeded_content):
    """**A kért nyelven van** -> **nincs fallback**."""
    result = _resolve("hu")
    assert result is not None
    assert result.text == "Szia"
    assert result.used_lang == "hu"
    assert result.fallback is False
    assert result.missing is False


def test_a_nemet_a_keplet_nem_buzik_de_visszaesik(seeded_content):
    """**A német hiányzik** (a `draft` -> nem publikált) ->
    **a visszaesés az `en`-re** (a README 4.4 lánca: a kérés -> `en`
    -> `hu`) -> **a `prof` reviewer C-2 findingje: az `en` a `hu`
    ELŐTT jön.**
    """
    result = _resolve("de")
    assert result is not None
    assert result.text == "Hello"
    assert result.used_lang == "en"
    assert result.fallback is True
    assert result.missing is False


def test_a_meta_jeloli_a_fallbacket(seeded_content):
    """**A `meta.translation_fallback`** -> **a kért, a hasznalt
    nyelv és a `fallback` flag** (a 03 §6.3)."""
    result = _resolve("de")
    assert result is not None
    meta = result.to_meta()
    assert meta["requested"] == "de"
    assert meta["used"] == "en"
    assert meta["fallback"] is True
    assert "missing" not in meta


def test_a_nem_publikalt_forditas_nem_lathato(seeded_content):
    """**A `draft` fordítás nem látható** (a C-5 finding) -> **a
    német nyelven az `en` jön, nem a `Hallo`.**"""
    result = _resolve("de")
    assert result is not None
    assert result.text != "Hallo"


def test_a_hianyzó_kulcs_missing_jelzes():
    """**A kulcs, amelynek nincs fordítása** -> **a `missing: true`**
    (a F-DET-16 "adat nélkül" jelölése) -> **a `text` `None`.**"""
    missing = _resolve("hu", content_key="test.nincs_ilyen")
    assert missing is not None
    assert missing.text is None
    assert missing.missing is True
    assert missing.to_meta()["missing"] is True


def test_a_content_vegpont_a_kert_nyelven(client, seeded_content):
    """**A `GET /api/v1/content/{key}`** a kért nyelven adja a
    fordítást → **a `meta.translation_fallback` a `fallback: false`.**
    """
    resp = client.get("/api/v1/content/test.hello", params={"lang": "hu"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["data"]["text"] == "Szia"
    fallback = body["meta"]["translation_fallback"]["text"]
    assert fallback["requested"] == "hu"
    assert fallback["used"] == "hu"
    assert fallback["fallback"] is False


def test_a_content_vegpont_a_visszaesessel(client, seeded_content):
    """**A német nem publikált** → **az `en` jön** → **a
    `meta.translation_fallback` jelzi** (a 03 §6.3).
    """
    resp = client.get("/api/v1/content/test.hello", params={"lang": "de"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["data"]["text"] == "Hello"
    fallback = body["meta"]["translation_fallback"]["text"]
    assert fallback["requested"] == "de"
    assert fallback["used"] == "en"
    assert fallback["fallback"] is True


def test_a_content_vegpont_a_nem_letezo_kulcs_404(client):
    """**A kulcs, amelynek nincs publikált fordítása → **a 404**
    (a 03 §6.2a — **nem 403**: a publikus API nem árulja el, hogy a
    kulcs létezik-e).
    """
    resp = client.get("/api/v1/content/test.nincs_ilyen")
    assert resp.status_code == 404
