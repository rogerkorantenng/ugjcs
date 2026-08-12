"""Runtime configuration, read from the environment.

Secrets never have defaults. A missing DATABASE_URL must fail loudly at startup rather
than silently falling back to something that appears to work in development.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UGJCS_", env_file=".env")

    database_url: str = Field(
        description="PostgreSQL DSN using the asyncpg driver, e.g. "
        "postgresql+asyncpg://user:pass@host:5432/ugjcs",
    )
    sql_echo: bool = Field(default=False, description="Log every statement; never in production")
    jwt_secret: str = Field(description="HMAC signing key; no default, must be supplied")
    access_token_minutes: int = Field(default=15, description="Access token lifetime")
    refresh_token_days: int = Field(default=7, description="Refresh token lifetime")


@lru_cache
def get_settings() -> Settings:
    """Cached so configuration is parsed once per process."""
    return Settings()  # type: ignore[call-arg]
