"""Add manuscript document storage keys.

Revision ID: 0004
Revises: 0003

The task naming this migration called for revision id "0003", but that id was already
taken by `0003_review_assignments.py` by the time this work started. "0004" is the next
free slot in the existing `0001 -> 0002 -> 0003` chain.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "manuscripts", sa.Column("original_document_key", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "manuscripts", sa.Column("anonymised_document_key", sa.String(length=512), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("manuscripts", "anonymised_document_key")
    op.drop_column("manuscripts", "original_document_key")
