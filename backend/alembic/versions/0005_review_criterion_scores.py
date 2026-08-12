"""Add FR-11's criterion scores and the author/editor comment split to review assignments.

Revision ID: 0005
Revises: 0004

`comments` is replaced by two columns (`comments_to_author`, `confidential_comments_to_editor`)
rather than kept alongside them: FR-11 requires the confidential half to never reach an
author, and a single ambiguous `comments` column sitting next to it would be exactly the
kind of trap that produces a leak later. There is no production data to migrate — this
project has never shipped FR-11 — so the rename is a straight drop-and-add, not a
data-preserving rename.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_SCORE_COLUMNS = (
    "originality_score",
    "rigour_score",
    "clarity_score",
    "significance_score",
)


def upgrade() -> None:
    for column in _SCORE_COLUMNS:
        op.add_column(
            "review_assignments", sa.Column(column, sa.Integer(), nullable=True)
        )
    op.add_column(
        "review_assignments", sa.Column("comments_to_author", sa.Text(), nullable=True)
    )
    op.add_column(
        "review_assignments",
        sa.Column("confidential_comments_to_editor", sa.Text(), nullable=True),
    )
    op.drop_column("review_assignments", "comments")

    # Bare fragment, not the expanded name — see docs/superpowers/plans/
    # 2026-08-12-ugjcs-plan-2-persistence.md: the `ck` naming-convention template already
    # contains `%(constraint_name)s`, so `op.create_check_constraint` expands it once from
    # whatever is passed here, exactly as `models.py`'s `CheckConstraint(name=...)` does.
    for column in _SCORE_COLUMNS:
        op.create_check_constraint(
            f"{column}_range",
            "review_assignments",
            f"{column} IS NULL OR {column} BETWEEN 1 AND 5",
        )


def downgrade() -> None:
    # Bare fragment here too: `op.drop_constraint` resolves its name through the same
    # naming convention `op.create_check_constraint` does (see the round-trip note
    # above), so passing the already-expanded `ck_review_assignments_...` name here
    # expands it a second time and the DROP CONSTRAINT can never find the real one.
    for column in _SCORE_COLUMNS:
        op.drop_constraint(f"{column}_range", "review_assignments", type_="check")
    op.add_column("review_assignments", sa.Column("comments", sa.Text(), nullable=True))
    op.drop_column("review_assignments", "confidential_comments_to_editor")
    op.drop_column("review_assignments", "comments_to_author")
    for column in _SCORE_COLUMNS:
        op.drop_column("review_assignments", column)
