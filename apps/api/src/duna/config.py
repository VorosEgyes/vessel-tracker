"""A konfiguráció (a pydantic-settings, a 07 §2.3).

**A `DATABASE_URL` a környezeti változókból jön** (a `.env`-fájl
vagy a CI service — a 07 §4.2) → **a `duna/config.py` maga a
`pydantic-settings` `BaseSettings` osztály.**

**Az asyncpg URL a futáshoz, a psycopg a szinkron Alembichez** (a
`db/migrations/env.py`) → **a `psycopg` a runtime-függőségek között
van** → **a `postgresql+asyncpg://` a `psycopg`-re cserélés csak az
Alembic `env.py`-jában történik** (a `duna` a `+asyncpg`-t használja).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Az alkalmazás beállításai (a `.env`-ből és a környezetből)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # **az alkalmazás neve** (a FastAPI title-jában)
    app_name: str = "vessel-tracker"
    app_version: str = "0.1.0"

    # **a DB URL** (a 07 §2.3) -> **a `postgresql+asyncpg://` a
    # futáshoz, a `psycopg` az Alembichez (az env.py cseréli)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/duna"

    # **a CORS** (a 03 §3: a web app a hálózaton belül van)
    cors_origins: list[str] = ["http://localhost:4321"]

    # **a log szintje**
    log_level: str = "INFO"

    @property
    def sync_database_url(self) -> str:
        """A szinkron URL (az Alembichez) — a `+asyncpg` -> `+psycopg`."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    """A beállítások (a `lru_cache` miatt egyszer olvasódnak be)."""
    return Settings()
