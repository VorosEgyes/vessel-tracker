"""Az async DB-session (a SQLAlchemy 2.0 async, a 01 §3.2).

**Az engine a `duna.config`-ból jön** (a `DATABASE_URL`) → **a
`pgserver`/a CI service és a production ugyanaz a kód.**

**AZ ENGINE A FASTAPI LIFESPAN-BAN LÉTEZIK** (a `app.state`-ben) →
**nem globális `lru_cache`-ben.** **A `pool` az event loophoz kötődik**
→ **a `TestClient` saját loopot futtat** → **a globális engine a
teszt végén a LEZÁRT looptól felszabadítja a connectionöket** →
**a `RuntimeError: Event loop is closed`.**

**A `lifespan` a helyes megoldás:** az engine a szerver indításakor
jön létre (az első loopon) → **a `shutdown`kor eldobódik** (a
saját loopon) → **nincs leak, nincs cross-loop hiba.**
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from duna.config import get_settings


def create_engine() -> AsyncEngine:
    """Egy új async engine (a `DATABASE_URL`-ből).

    **A `pool_pre_ping`:** a `pg_cron`/a deploy után a kapcsolat
    lehet megszakadt → **a ping minden kérés előtt ellenőrzi.**
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """A session-gyár (a `AsyncSession`-höz)."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """**A FastAPI függőség** → egy session per kérés.

    **A session-gyár az `app.state`-ben van** (a lifespan hozza létre)
    → **a `finally` lezárja** → **a connection visszaadja a poolnak.**
    """
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def healthcheck() -> dict[str, Any]:
    """A DB elérhetőségének ellenőrzése (a `/health` végpont).

    **SZINKRON** (a `psycopg`-vel) → **a `pgserver`/a CI service és a
    production ugyanaz** → **nem kell async-et használni egy egysoros
    pinghez.**
    """
    import sqlalchemy as sa

    settings = get_settings()
    engine = sa.create_engine(settings.sync_database_url, poolclass=sa.pool.NullPool)
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    finally:
        engine.dispose()
