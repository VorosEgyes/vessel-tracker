"""A FastAPI alkalmazás (a 01 §4.2, a 03 §3).

**A `main.py` a belépési pont** → **az `uvicorn duna.main:app`
indítja** (a `07` §3.2: az `apps/api/Dockerfile` CMD-je).

**A `FastAPI` app:**
- a `title`/`version` a `duna.config`-ból (a 07 §2.3);
- **a `/api/v1/` prefix** a routereknek (a 03 §3.1);
- **a CORS** a web appnak (a 03 §3: a hálózaton belül van);
- **a `/health` végpont** a DB-ellenőrzéssel (a 09 §4.1 monitoring).

**A LIFESPAN:** az async engine a `app.state`-ben jön létre és a
shutdownkor eldobódik → **a pool az event loophoz kötődik, nem
kerül cross-loop hibába** (a `duna.db.session` modul docstringje).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from duna.api.v1.content import router as content_router
from duna.api.v1.search import router as search_router
from duna.api.v1.vessel import router as vessel_router
from duna.config import get_settings
from duna.db.session import create_engine, create_session_factory, healthcheck


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """**Az app startup/shutdown** → **az engine és a session-gyár
    létrehozása és eldobása.**

    **A `shutdown`kor az `engine.dispose()`** → **a connectionök
    visszakerülnek a poolba → **a process tiszta kilép.**
    """
    engine = create_engine()
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """A FastAPI alkalmazás (a `03` §3 szerint)."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=("A Duna és a Balaton hajókövető API-ja (a 03 – API-specifikáció)."),
        lifespan=lifespan,
    )

    # **a CORS** (a 03 §3: a web app a hálózaton belül van, de a
    # fejlesztői Astro a `localhost:4321`-en fut)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """A DB elérhetőségének ellenőrzése (a 09 §4.1 monitoring)."""
        return healthcheck()

    # **a `/api/v1/` routerek** (a 03 §3.1, §3.2)
    app.include_router(vessel_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(content_router, prefix="/api/v1")

    return app


app = create_app()
