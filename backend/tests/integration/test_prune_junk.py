"""The junk prune removes only non-corpus manuscripts and leaves the guard armed.

Regression companion to the QA sweep of 2026-08-13: live verification runs left real
manuscripts in the deployed database (one of them published into the public archive),
and removing them has to work around the append-only trigger without leaving it off.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.engine import session_factory
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository
from ugjcs.scripts.prune_junk import corpus_allowlist, prune

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 13, 2, 0, tzinfo=UTC)


async def _store(engine: AsyncEngine, *, sequence: int) -> Manuscript:
    factory = session_factory(engine)
    async with factory() as session:
        repository = SqlAlchemyManuscriptRepository(session)
        manuscript = Manuscript(
            id=ManuscriptId(uuid4()),
            tracking_code=TrackingCode.mint(2026, sequence),
            title=f"Manuscript {sequence}",
            abstract="An abstract long enough to be plausible.",
            keywords=("test",),
            author_ids=(AUTHOR,),
            corresponding_author_id=AUTHOR,
        )
        manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
        await repository.add(manuscript)
        await session.commit()
        return manuscript


async def test_prune_removes_only_non_corpus_manuscripts(engine: AsyncEngine) -> None:
    corpus_sequence = int(corpus_allowlist()[0].rsplit("-", 1)[1])
    kept = await _store(engine, sequence=corpus_sequence)
    junk = await _store(engine, sequence=746109)

    removed = await prune(engine)

    assert removed == 1
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT tracking_code FROM manuscripts"))
        remaining = rows.scalars().all()
        assert remaining == [kept.tracking_code.value]
        orphaned = (
            await conn.execute(
                text("SELECT count(*) FROM editorial_events WHERE manuscript_id = :id"),
                {"id": junk.id},
            )
        ).scalar_one()
        assert orphaned == 0


async def test_prune_leaves_the_append_only_trigger_enabled(engine: AsyncEngine) -> None:
    await _store(engine, sequence=746110)
    await prune(engine)
    survivor = await _store(engine, sequence=746111)
    async with engine.connect() as conn:
        with pytest.raises(DBAPIError, match="append-only"):
            await conn.execute(
                text("DELETE FROM editorial_events WHERE manuscript_id = :id"),
                {"id": survivor.id},
            )
