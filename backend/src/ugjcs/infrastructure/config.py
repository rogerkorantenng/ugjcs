"""Runtime configuration, read from the environment.

Secrets never have defaults. A missing DATABASE_URL must fail loudly at startup rather
than silently falling back to something that appears to work in development.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
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
    cors_allowed_origins: str = Field(
        default="",
        description="Comma-separated browser origins allowed to call the API, e.g. "
        "https://ugjcs.example.edu,http://localhost:3000. Empty means none allowed.",
    )
    s3_bucket_name: str = Field(
        default="ugjcs-manuscripts-9bdf45b0",
        description="The manuscripts bucket (see infra/s3.tf). Defaulted, not secret: "
        "the bucket blocks all public access, so knowing its name grants nothing without "
        "the instance role's credentials, and defaulting it means deploying this feature "
        "needs no change to App Runner's runtime environment configuration.",
    )
    aws_region: str = Field(default="us-east-1", description="Region the bucket lives in.")
    paystack_secret_key: str = Field(
        default="",
        # Read as bare PAYSTACK_SECRET_KEY (the name Paystack's own docs teach and every
        # deployment runbook will reach for) rather than the UGJCS_-prefixed form the
        # other settings use; the prefixed spelling is accepted too so a uniform
        # environment file still works. Empty is a meaningful value, not a
        # misconfiguration: it selects billing's documented mock mode (see
        # `ugjcs.api.routers.billing`), which is why this secret — alone among the
        # secrets here — has a default. The value must never be logged, echoed in a
        # response, or interpolated into an error message; only the Paystack adapter's
        # Authorization header may ever carry it.
        validation_alias=AliasChoices("PAYSTACK_SECRET_KEY", "UGJCS_PAYSTACK_SECRET_KEY"),
        description="Paystack secret key. Blank selects mock mode for demonstrations.",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so configuration is parsed once per process."""
    return Settings()  # type: ignore[call-arg]
