"""Transactional boundary.

Rollback on exit is unconditional: it is a no-op after a successful commit, and it is the
safety net that stops a forgotten `commit()` from leaving a half-written transaction open.
"""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository


class SqlAlchemyUnitOfWork:
    manuscripts: SqlAlchemyManuscriptRepository

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self.manuscripts = SqlAlchemyManuscriptRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        await self._session.rollback()
        await self._session.close()
        self._session = None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("commit outside an active unit of work")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("rollback outside an active unit of work")
        await self._session.rollback()
