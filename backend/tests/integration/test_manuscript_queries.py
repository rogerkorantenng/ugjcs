from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR_A = UserId(uuid4())
AUTHOR_B = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make(author: UserId, sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=f"Paper {sequence}",
        abstract="An abstract.",
        keywords=("networking",),
        author_ids=(author,),
        corresponding_author_id=author,
    )


async def test_list_by_author_returns_only_that_authors_manuscripts(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    mine = make(AUTHOR_A, 1)
    mine.submit(actor_id=AUTHOR_A, occurred_at=NOW)
    theirs = make(AUTHOR_B, 2)
    theirs.submit(actor_id=AUTHOR_B, occurred_at=NOW)
    await repository.add(mine)
    await repository.add(theirs)
    await session.commit()

    results = await repository.list_by_author(AUTHOR_A)
    assert {m.id for m in results} == {mine.id}


async def test_list_by_author_is_empty_for_an_author_with_nothing_submitted(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    assert await repository.list_by_author(UserId(uuid4())) == []


async def test_list_by_author_includes_manuscripts_where_the_user_is_a_co_author(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    co_authored = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 3),
        title="Joint Paper",
        abstract="An abstract.",
        keywords=(),
        author_ids=(AUTHOR_A, AUTHOR_B),
        corresponding_author_id=AUTHOR_A,
    )
    co_authored.submit(actor_id=AUTHOR_A, occurred_at=NOW)
    await repository.add(co_authored)
    await session.commit()

    results = await repository.list_by_author(AUTHOR_B)
    assert {m.id for m in results} == {co_authored.id}
