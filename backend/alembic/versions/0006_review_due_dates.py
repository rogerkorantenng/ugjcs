"""Add a review deadline (`due_at`) to review assignments.

Revision ID: 0006
Revises: 0005

`due_at` is nullable and carries no server default, deliberately: the deadline is
application policy (`ugjcs.application.ports.REVIEW_PERIOD`, 21 days), stamped by
`SqlAlchemyReviewAssignmentRepository.assign` from the same `occurred_at` it writes into
`assigned_at`. A column default of `now() + interval` would compute the deadline from a
different clock than the assignment timestamp and let the two drift for any caller that
assigns with a non-wall-clock time (the seed script does exactly that).

Existing rows are backfilled to `assigned_at + 21 days` — the same interval new
assignments get — because `assigned_at` is NOT NULL on every row this table has ever
held (it has been required since `0003_review_assignments`), so there is always an
honest anchor to compute from and no row is left deadline-less.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_assignments",
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )
    # `WHERE due_at IS NULL` keeps the backfill idempotent in spirit: a re-run (or a
    # merge race that already populated some rows) never overwrites a deadline an editor
    # may later have come to rely on.
    op.execute(
        "UPDATE review_assignments "
        "SET due_at = assigned_at + INTERVAL '21 days' "
        "WHERE due_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("review_assignments", "due_at")
