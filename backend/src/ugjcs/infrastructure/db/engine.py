"""Async engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ugjcs.infrastructure.config import get_settings


def create_engine(url: str | None = None, *, echo: bool | None = None) -> AsyncEngine:
    """Build an engine, falling back to configured settings only for what was not supplied.

    Settings are read lazily and only when needed. Reading them unconditionally would make
    this function require `UGJCS_DATABASE_URL` even when the caller supplied a URL — which
    would break every integration test, since those point at a throwaway container and set
    no environment at all.

    `pool_pre_ping` costs one round trip per checkout and saves the first request after an
    idle connection is dropped by RDS or a load balancer.
    """
    if url is None or echo is None:
        settings = get_settings()
        url = url if url is not None else settings.database_url
        echo = echo if echo is not None else settings.sql_echo
    return create_async_engine(url, echo=echo, pool_pre_ping=True)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessions do not expire attributes on commit, so aggregates stay readable after."""
    return async_sessionmaker(engine, expire_on_commit=False)
