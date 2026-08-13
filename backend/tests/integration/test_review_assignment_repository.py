from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import REVIEW_PERIOD
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.assignment_repository import SqlAlchemyReviewAssignmentRepository
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
REVIEWER = UserId(uuid4())
OTHER_REVIEWER = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


async def stored_manuscript(session: AsyncSession, sequence: int = 51) -> ManuscriptId:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Paper",
        abstract="Abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()
    return manuscript.id


async def test_an_assignment_is_visible_to_both_parties(session: AsyncSession) -> None:
    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    for_reviewer = await repository.list_for_reviewer(REVIEWER)
    for_manuscript = await repository.list_for_manuscript(manuscript_id)
    assert [a.manuscript_id for a in for_reviewer] == [manuscript_id]
    assert [a.reviewer_id for a in for_manuscript] == [REVIEWER]
    assert for_reviewer[0].status == "assigned"
    assert for_reviewer[0].recommendation is None
    assert for_reviewer[0].submitted_at is None


async def test_a_new_assignment_is_due_twenty_one_days_after_assignment(
    session: AsyncSession,
) -> None:
    """The adapter stamps `due_at` from the same `occurred_at` it writes into
    `assigned_at` — see `SqlAlchemyReviewAssignmentRepository.assign` — so the two can
    never drift, and the interval is `REVIEW_PERIOD`, the one constant the fake and the
    Alembic backfill share."""
    manuscript_id = await stored_manuscript(session, sequence=54)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    [record] = await repository.list_for_reviewer(REVIEWER)
    assert record.due_at == NOW + REVIEW_PERIOD
    assert record.due_at == record.assigned_at + REVIEW_PERIOD


async def test_list_all_returns_every_assignment_across_manuscripts(
    session: AsyncSession,
) -> None:
    first = await stored_manuscript(session, sequence=55)
    second = await stored_manuscript(session, sequence=56)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(first, REVIEWER, occurred_at=NOW)
    await repository.assign(second, OTHER_REVIEWER, occurred_at=NOW)
    await session.commit()

    everything = await repository.list_all()
    assert {(a.manuscript_id, a.reviewer_id) for a in everything} == {
        (first, REVIEWER),
        (second, OTHER_REVIEWER),
    }


async def test_assigning_the_same_reviewer_twice_is_rejected(session: AsyncSession) -> None:
    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)


async def test_two_different_reviewers_can_be_assigned_to_the_same_manuscript(
    session: AsyncSession,
) -> None:
    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await repository.assign(manuscript_id, OTHER_REVIEWER, occurred_at=NOW)
    await session.commit()

    for_manuscript = await repository.list_for_manuscript(manuscript_id)
    assert {a.reviewer_id for a in for_manuscript} == {REVIEWER, OTHER_REVIEWER}


async def test_marking_submitted_records_the_review_content(session: AsyncSession) -> None:
    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    await repository.mark_submitted(
        manuscript_id,
        REVIEWER,
        recommendation="accept",
        originality_score=5,
        rigour_score=4,
        clarity_score=4,
        significance_score=5,
        comments_to_author="Solid work.",
        confidential_comments_to_editor="No concerns.",
        occurred_at=NOW,
    )
    await session.commit()

    [record] = await repository.list_for_reviewer(REVIEWER)
    assert record.status == "submitted"
    assert record.recommendation == "accept"
    assert record.originality_score == 5
    assert record.rigour_score == 4
    assert record.clarity_score == 4
    assert record.significance_score == 5
    assert record.comments_to_author == "Solid work."
    assert record.confidential_comments_to_editor == "No concerns."
    assert record.submitted_at == NOW


async def test_list_for_reviewer_is_empty_for_a_reviewer_with_no_assignments(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyReviewAssignmentRepository(session)
    assert await repository.list_for_reviewer(UserId(uuid4())) == []
