"""The database must refuse to rewrite the audit log, not merely decline to offer an API."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)


async def stored_manuscript(session: AsyncSession) -> Manuscript:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 21),
        title="Edge Caching for Campus Networks",
        abstract="A cache placement strategy for constrained campus links.",
        keywords=("caching",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()
    return manuscript


async def test_updating_an_event_is_rejected_by_the_database(session: AsyncSession) -> None:
    manuscript = await stored_manuscript(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(
            text("UPDATE editorial_events SET event_type = 'forged' WHERE manuscript_id = :id"),
            {"id": manuscript.id},
        )


async def test_deleting_an_event_is_rejected_by_the_database(session: AsyncSession) -> None:
    manuscript = await stored_manuscript(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(
            text("DELETE FROM editorial_events WHERE manuscript_id = :id"),
            {"id": manuscript.id},
        )


async def test_deleting_a_manuscript_with_events_is_refused(session: AsyncSession) -> None:
    """ondelete=RESTRICT: an audit trail that vanishes with its subject is not a trail."""
    manuscript = await stored_manuscript(session)
    with pytest.raises(DBAPIError):
        await session.execute(text("DELETE FROM manuscripts WHERE id = :id"), {"id": manuscript.id})
