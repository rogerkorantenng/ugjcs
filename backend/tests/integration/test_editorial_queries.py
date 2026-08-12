from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make(sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=f"Paper {sequence}",
        abstract="Abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


async def test_the_screening_queue_holds_only_submitted_manuscripts(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    submitted = make(61)
    submitted.submit(actor_id=AUTHOR, occurred_at=NOW)
    draft = make(62)
    await repository.add(submitted)
    await repository.add(draft)
    await session.commit()

    queue = await repository.list_by_status(S.SUBMITTED)
    assert {m.id for m in queue} == {submitted.id}
