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
EDITOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 10, 0, tzinfo=UTC)


def make_manuscript(sequence: int = 1) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Adaptive Bitrate Selection over Intermittent Links",
        abstract="A controller for video delivery under bandwidth collapse.",
        keywords=("networking", "video"),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


async def test_a_stored_manuscript_can_be_read_back(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    assert loaded.tracking_code == manuscript.tracking_code
    assert loaded.status is S.SUBMITTED
    assert loaded.author_ids == (AUTHOR,)


async def test_a_missing_manuscript_reads_back_as_none(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    assert await repository.get(ManuscriptId(uuid4())) is None


async def test_lookup_by_tracking_code(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript(sequence=44)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get_by_tracking_code(TrackingCode.mint(2026, 44))
    assert loaded is not None
    assert loaded.id == manuscript.id


async def test_saving_an_unpersisted_manuscript_is_refused(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    with pytest.raises(LookupError, match="never been persisted"):
        await repository.save(make_manuscript())


async def test_state_changes_survive_a_round_trip(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript(sequence=7)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    await repository.save(loaded)
    await session.commit()

    reloaded = await repository.get(manuscript.id)
    assert reloaded is not None
    assert reloaded.status is S.UNDER_SCREENING


async def test_document_keys_attached_on_submission_survive_a_round_trip(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript(sequence=51)
    manuscript.submit(
        actor_id=AUTHOR,
        occurred_at=NOW,
        original_document_key=f"manuscripts/{manuscript.id}/v1/original.pdf",
        anonymised_document_key=f"manuscripts/{manuscript.id}/v1/anonymised.pdf",
    )
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    assert loaded.original_document_key == f"manuscripts/{manuscript.id}/v1/original.pdf"
    assert loaded.anonymised_document_key == f"manuscripts/{manuscript.id}/v1/anonymised.pdf"


async def test_document_keys_attached_by_save_persist_too(session: AsyncSession) -> None:
    """`save()` sets `row.original_document_key`/`anonymised_document_key` explicitly,
    unlike `add()` which gets them for free from `to_row`. This proves that write path too."""
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript(sequence=52)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.original_document_key = f"manuscripts/{loaded.id}/v2/original.pdf"
    loaded.anonymised_document_key = f"manuscripts/{loaded.id}/v2/anonymised.pdf"
    await repository.save(loaded)
    await session.commit()

    reloaded = await repository.get(manuscript.id)
    assert reloaded is not None
    assert reloaded.original_document_key == f"manuscripts/{manuscript.id}/v2/original.pdf"
    assert reloaded.anonymised_document_key == f"manuscripts/{manuscript.id}/v2/anonymised.pdf"
