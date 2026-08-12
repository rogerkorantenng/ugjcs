"""A transaction boundary that rolls back unless commit is called explicitly."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.engine import session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)


def make_manuscript(sequence: int) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Congestion Control for Satellite Backhaul",
        abstract="A congestion controller for high-latency backhaul links.",
        keywords=("congestion control",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    return manuscript


async def test_work_is_visible_after_commit(engine: AsyncEngine) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    manuscript = make_manuscript(61)
    async with uow:
        await uow.manuscripts.add(manuscript)
        await uow.commit()

    async with uow:
        assert await uow.manuscripts.get(manuscript.id) is not None


async def test_work_is_discarded_without_commit(engine: AsyncEngine) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    manuscript = make_manuscript(62)
    async with uow:
        await uow.manuscripts.add(manuscript)

    async with uow:
        assert await uow.manuscripts.get(manuscript.id) is None


async def test_an_exception_rolls_the_transaction_back(engine: AsyncEngine) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    manuscript = make_manuscript(63)
    with pytest.raises(RuntimeError, match="deliberate"):
        async with uow:
            await uow.manuscripts.add(manuscript)
            raise RuntimeError("deliberate failure after a write")

    async with uow:
        assert await uow.manuscripts.get(manuscript.id) is None
