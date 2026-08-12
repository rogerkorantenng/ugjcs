"""PostgreSQL implementation of the review-assignment read model.

There is no aggregate here to protect an invariant, by design — see Plan 4's scope
decision. This repository is thinner than `SqlAlchemyManuscriptRepository` on purpose.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import ReviewAssignmentRecord
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.infrastructure.db.mappers import assignment_row_to_record
from ugjcs.infrastructure.db.models import ReviewAssignmentRow


class SqlAlchemyReviewAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(
        self, manuscript_id: ManuscriptId, reviewer_id: UserId, *, occurred_at: datetime
    ) -> None:
        self._session.add(
            ReviewAssignmentRow(
                id=uuid4(),
                manuscript_id=manuscript_id,
                reviewer_id=reviewer_id,
                status="assigned",
                assigned_at=occurred_at,
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

    async def mark_submitted(
        self,
        manuscript_id: ManuscriptId,
        reviewer_id: UserId,
        *,
        recommendation: str,
        comments: str,
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
        row.comments = comments
        row.submitted_at = occurred_at
