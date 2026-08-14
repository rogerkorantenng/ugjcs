"""Full-text search and the entrypoint backfill, against a live PostgreSQL.

The unit suite proves the wire contract over a substring-matching fake; what only a
real database can prove lives here: `plainto_tsquery` stemming, the `@@` match against
the indexed expression, `ts_headline`'s `<b>` snippet marks, and the backfill script's
idempotence over real rows.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from tests.unit.api.fakes import FakeDocumentStore
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.engine import session_factory
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository
from ugjcs.infrastructure.storage.demo_pdf import build_demo_pdf
from ugjcs.scripts.backfill_fulltext import backfill

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)


async def _seed_published(
    session: AsyncSession,
    sequence: int,
    *,
    title: str,
    keywords: tuple[str, ...] = (),
    fulltext: str | None = None,
    document_key: str | None = None,
) -> Manuscript:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="An abstract.",
        keywords=keywords,
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
        original_document_key=document_key,
    )
    await repository.add(manuscript)
    if fulltext is not None:
        await repository.store_fulltext(manuscript.id, fulltext)
    await session.commit()
    return manuscript


async def test_a_fulltext_match_returns_a_ts_headline_snippet(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    match = await _seed_published(
        session,
        701,
        title="Community Mesh Networks",
        fulltext="Section 4 evaluates the gossip protocol under simulated packet loss.",
    )
    await _seed_published(session, 702, title="Unrelated", fulltext="Nothing relevant here.")

    hits = await repository.search_published_with_snippets("gossip protocol")
    assert [hit.manuscript.id for hit in hits] == [match.id]
    snippet = hits[0].snippet
    assert snippet is not None
    # `ts_headline` marks matched lexemes with <b>…</b> by default — the contract the
    # schema documents for clients rendering snippets.
    assert "<b>gossip</b>" in snippet
    assert "<b>protocol</b>" in snippet


async def test_fulltext_matching_stems_the_query(session: AsyncSession) -> None:
    """What ILIKE alone could never do, and the reason tsquery is here at all:
    "scheduling" must find a body that says "scheduled"."""
    repository = SqlAlchemyManuscriptRepository(session)
    match = await _seed_published(
        session,
        703,
        title="Unrelated Title",
        fulltext="Jobs are scheduled by a fairness-aware allocator.",
    )
    hits = await repository.search_published_with_snippets("scheduling")
    assert [hit.manuscript.id for hit in hits] == [match.id]
    assert hits[0].snippet is not None
    assert "<b>scheduled</b>" in hits[0].snippet


async def test_metadata_matches_carry_no_snippet(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    by_title = await _seed_published(session, 704, title="Fair Scheduling for GPU Clusters")
    by_keyword = await _seed_published(
        session, 705, title="Unrelated", keywords=("scheduling", "fairness")
    )
    hits = await repository.search_published_with_snippets("scheduling")
    assert {hit.manuscript.id for hit in hits} == {by_title.id, by_keyword.id}
    assert all(hit.snippet is None for hit in hits)


async def test_an_unpublished_manuscript_never_matches(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 706),
        title="Gossip Protocols Everywhere",
        abstract="An abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    await repository.add(manuscript)
    await repository.store_fulltext(manuscript.id, "gossip protocol gossip protocol")
    await session.commit()
    assert await repository.search_published_with_snippets("gossip") == []


# --- the entrypoint backfill ---------------------------------------------------------


async def test_backfill_indexes_published_papers_and_is_idempotent(engine: AsyncEngine) -> None:
    factory = session_factory(engine)
    store = FakeDocumentStore()
    async with factory() as session:
        indexed_one = await _seed_published(
            session, 707, title="Solar Microgrids", document_key="docs/707.pdf"
        )
        # Already indexed: must be left exactly as it is, not re-extracted.
        await _seed_published(
            session,
            708,
            title="Already Indexed",
            fulltext="previously extracted text",
            document_key="docs/708.pdf",
        )
        # Unreadable PDF: skipped with a message, never fatal (the entrypoint runs
        # under `set -eu`, so "fatal" would mean the API never boots).
        await _seed_published(session, 709, title="Corrupt Document", document_key="docs/709.pdf")
    store.objects["docs/707.pdf"] = build_demo_pdf(
        tracking_code="SDJ-2026-0707",
        title="Solar Microgrids",
        abstract="Village-level load forecasting with gradient boosting.",
        keywords=("solar",),
        author_name="Ama Mensah",
    )
    store.objects["docs/709.pdf"] = b"%PDF-1.7 but not really a pdf"

    assert await backfill(engine, store) == 1

    async with engine.connect() as conn:
        rows = (await conn.execute(text("SELECT tracking_code, fulltext FROM manuscripts"))).all()
    by_code = {row.tracking_code: row.fulltext for row in rows}
    assert "gradient boosting" in by_code[indexed_one.tracking_code.value]
    assert by_code["SDJ-2026-0708"] == "previously extracted text"
    assert by_code["SDJ-2026-0709"] is None  # left for the next boot to retry

    # Second run: everything indexable is indexed; only the corrupt PDF is revisited
    # (and skipped again), and nothing is overwritten.
    assert await backfill(engine, store) == 0
