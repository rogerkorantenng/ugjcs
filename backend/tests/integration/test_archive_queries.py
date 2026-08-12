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


async def _seed_published(
    session: AsyncSession, title: str, sequence: int, *, abstract: str = "An abstract."
) -> Manuscript:
    # `abstract` is a keyword parameter, not hardcoded, so that search-matching tests can
    # control which field (title vs. abstract) a query actually matches on — a fixed
    # "Abstract about scheduling." for every seeded paper (as this helper's first draft
    # had it) makes every paper match a "scheduling" query via its abstract regardless
    # of title, defeating the point of `test_search_published_matches_the_title_...`.
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract=abstract,
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
    )
    await repository.add(manuscript)
    await session.commit()
    return manuscript


async def test_list_published_returns_only_published_manuscripts(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    published = await _seed_published(session, "Fair Scheduling", 101)
    draft = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 102),
        title="Unpublished Draft",
        abstract="Not yet.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    await repository.add(draft)
    await session.commit()

    results = await repository.list_published()
    assert {m.id for m in results} == {published.id}


async def test_search_published_matches_the_title_case_insensitively(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    match = await _seed_published(session, "Fair Scheduling for Shared GPU Clusters", 103)
    await _seed_published(session, "Edge Caching for Campus Networks", 104)

    results = await repository.search_published("scheduling")
    assert {m.id for m in results} == {match.id}
