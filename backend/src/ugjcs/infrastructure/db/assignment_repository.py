"""PostgreSQL implementation of the review-assignment read model.

There is no aggregate here to protect an invariant, by design — see Plan 4's scope
decision. This repository is thinner than `SqlAlchemyManuscriptRepository` on purpose.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import REVIEW_PERIOD, ReviewAssignmentRecord
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.infrastructure.db.mappers import assignment_row_to_record
from ugjcs.infrastructure.db.models import ReviewAssignmentRow


class SqlAlchemyReviewAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(
        self, manuscript_id: ManuscriptId, reviewer_id: UserId, *, occurred_at: datetime
    ) -> None:
        # `due_at` is stamped here, not defaulted in the column definition: the deadline
        # is derived from the same `occurred_at` the caller supplies for `assigned_at`,
        # and a server-side `now() + interval` default would let the two drift apart for
        # any caller (the seed, a test) that assigns with a non-wall-clock timestamp.
        self._session.add(
            ReviewAssignmentRow(
                id=uuid4(),
                manuscript_id=manuscript_id,
                reviewer_id=reviewer_id,
                status="assigned",
                assigned_at=occurred_at,
                due_at=occurred_at + REVIEW_PERIOD,
            )
        )
        # Flushed rather than left buffered: the uniqueness violation a duplicate
        # assignment raises must surface from this call, not from an unrelated later
        # `session.commit()` — otherwise a test (or a caller) asserting on `assign()`
        # would be asserting the wrong thing raised it.
        await self._session.flush()

    async def list_for_reviewer(self, reviewer_id: UserId) -> list[ReviewAssignmentRecord]:
        result = await self._session.execute(
            select(ReviewAssignmentRow).where(ReviewAssignmentRow.reviewer_id == reviewer_id)
        )
        return [assignment_row_to_record(row) for row in result.scalars()]

    async def list_for_manuscript(
        self, manuscript_id: ManuscriptId
    ) -> list[ReviewAssignmentRecord]:
        result = await self._session.execute(
            select(ReviewAssignmentRow).where(ReviewAssignmentRow.manuscript_id == manuscript_id)
        )
        return [assignment_row_to_record(row) for row in result.scalars()]

    async def list_all(self) -> list[ReviewAssignmentRecord]:
        """A deliberate full-table scan — see the port's docstring for why no filter.

        Ordered by `assigned_at` only so the result is deterministic; the analytics
        consumer aggregates and never depends on the order."""
        result = await self._session.execute(
            select(ReviewAssignmentRow).order_by(ReviewAssignmentRow.assigned_at)
        )
        return [assignment_row_to_record(row) for row in result.scalars()]

    async def mark_submitted(
        self,
        manuscript_id: ManuscriptId,
        reviewer_id: UserId,
        *,
        recommendation: str,
        originality_score: int,
        rigour_score: int,
        clarity_score: int,
        significance_score: int,
        comments_to_author: str,
        confidential_comments_to_editor: str,
        occurred_at: datetime,
    ) -> None:
        result = await self._session.execute(
            select(ReviewAssignmentRow).where(
                ReviewAssignmentRow.manuscript_id == manuscript_id,
                ReviewAssignmentRow.reviewer_id == reviewer_id,
            )
        )
        row = result.scalar_one()
        row.status = "submitted"
        row.recommendation = recommendation
        row.originality_score = originality_score
        row.rigour_score = rigour_score
        row.clarity_score = clarity_score
        row.significance_score = significance_score
        row.comments_to_author = comments_to_author
        row.confidential_comments_to_editor = confidential_comments_to_editor
        row.submitted_at = occurred_at
