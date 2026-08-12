"""Dependency wiring: turns configuration into the services routes consume.

Kept apart from `deps.py` so authorisation logic stays readable without scrolling past
engine and session-factory construction.
"""

from collections.abc import AsyncIterator
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ugjcs.application.identity import IdentityService, SessionService
from ugjcs.application.ports import DocumentStore, UnitOfWork
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import JwtTokenService, SystemClock
from ugjcs.infrastructure.storage.s3_store import S3DocumentStore


@lru_cache
def _engine() -> AsyncEngine:
    settings = get_settings()
    return create_engine(settings.database_url, echo=settings.sql_echo)


@lru_cache
def _sessions() -> async_sessionmaker[AsyncSession]:
    return session_factory(_engine())


# Annotated with the concrete class, not the `UnitOfWork` port, deliberately: `UnitOfWork`
# declares `manuscripts`/`accounts` as plain (mutable) attributes, and mypy strict checks
# protocol attribute compatibility invariantly rather than covariantly — the same rule
# that stops you assigning a `list[Cat]` where a `list[Animal]` is expected. Annotating
# this as `AsyncIterator[UnitOfWork]` fails mypy even though `SqlAlchemyUnitOfWork`
# genuinely satisfies every method the port requires. Route handlers still depend on the
# abstract `UnitOfWork` in their own parameter (`uow: UnitOfWork = Depends(get_uow)`),
# which type-checks cleanly because FastAPI's `Depends()` is typed to return `Any`.
async def get_uow() -> AsyncIterator[SqlAlchemyUnitOfWork]:
    async with SqlAlchemyUnitOfWork(_sessions()) as uow:
        yield uow


# A route parameter written `uow: UowDep` gets a `UnitOfWork` via `get_uow`, and mypy
# treats it as one — `Annotated` strips the `Depends(...)` metadata for type-checking
# purposes, leaving the first argument as the effective type. Routes depend on this
# alias, not a bare `uow: UnitOfWork = Depends(get_uow)` default, because ruff's
# bugbear B008 (function-call-in-default-argument, part of this project's selected "B"
# rule set) flags `Depends(...)` used as a default value; only the alias form has no
# default to flag, since the call now lives in a module-level assignment instead of a
# function signature.
UowDep = Annotated[UnitOfWork, Depends(get_uow)]


@lru_cache
def _tokens() -> JwtTokenService:
    settings = get_settings()
    return JwtTokenService(
        secret=settings.jwt_secret,
        clock=SystemClock(),
        access_ttl=timedelta(minutes=settings.access_token_minutes),
        refresh_ttl=timedelta(days=settings.refresh_token_days),
    )


async def get_identity_service(uow: UowDep) -> IdentityService:
    return IdentityService(uow.accounts, _tokens())


async def get_session_service(uow: UowDep) -> SessionService:
    return SessionService(
        uow.accounts, uow.refresh_tokens, _tokens(), Argon2PasswordHasher(), SystemClock()
    )


@lru_cache
def _document_store() -> S3DocumentStore:
    settings = get_settings()
    return S3DocumentStore(bucket=settings.s3_bucket_name, region=settings.aws_region)


async def get_document_store() -> DocumentStore:
    return _document_store()


# See `UowDep`'s note: routes depend on this alias, not a bare `Depends(...)` default,
# because ruff's B008 forbids a function call as a default argument value.
DocumentStoreDep = Annotated[DocumentStore, Depends(get_document_store)]
