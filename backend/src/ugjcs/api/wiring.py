"""Dependency wiring: turns configuration into the services routes consume.

Kept apart from `deps.py` so authorisation logic stays readable without scrolling past
engine and session-factory construction.

TODO(Plan 3): `get_identity_service` and `get_session_service` — wiring
`ugjcs.application.identity.IdentityService`/`SessionService` from the unit of work and
`JwtTokenService` — are deliberately not implemented here. Authentication (Plan 3) is
being written concurrently in another worktree: `SessionService` and the
`UnitOfWork.refresh_tokens` port it depends on do not exist in this one yet. Add them
here, alongside a `_tokens()` helper building `JwtTokenService`, once Plan 3 lands and
`deps.py`'s stubs are wired for real.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ugjcs.application.ports import UnitOfWork
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork


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
