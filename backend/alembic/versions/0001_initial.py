"""Initial schema with an append-only editorial event log.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

APPEND_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION ugjcs_reject_event_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'editorial_events is append-only; % rejected', TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

APPEND_ONLY_TRIGGER = """
CREATE TRIGGER editorial_events_append_only
    BEFORE UPDATE OR DELETE ON editorial_events
    FOR EACH ROW EXECUTE FUNCTION ugjcs_reject_event_mutation();
"""

# PostgreSQL never fires row-level triggers on TRUNCATE, so the row-level trigger above
# leaves the whole log deletable by a single statement. A statement-level trigger is the
# only thing that closes it.
NO_TRUNCATE_TRIGGER = """
CREATE TRIGGER editorial_events_no_truncate
    BEFORE TRUNCATE ON editorial_events
    FOR EACH STATEMENT EXECUTE FUNCTION ugjcs_reject_event_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "manuscripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tracking_code", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("corresponding_author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("minimum_reviews", sa.Integer(), nullable=False),
        sa.Column("submitted_reviews", sa.Integer(), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.CheckConstraint("submitted_reviews >= 0", name="reviews_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_manuscripts"),
    )
    # `unique=True, index=True` on the column compiles to ONE unique index, not a separate
    # UniqueConstraint. The migration must create the same object, or Task 8's parity test fails.
    op.create_index("ix_manuscripts_tracking_code", "manuscripts", ["tracking_code"], unique=True)
    op.create_index("ix_manuscripts_status", "manuscripts", ["status"])

    op.create_table(
        "manuscript_authors",
        sa.Column("manuscript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["manuscript_id"],
            ["manuscripts.id"],
            name="fk_manuscript_authors_manuscript_id_manuscripts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("manuscript_id", "author_id", name="pk_manuscript_authors"),
        sa.UniqueConstraint("manuscript_id", "position", name="author_position_unique"),
    )

    op.create_table(
        "editorial_events",
        sa.Column("manuscript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint("sequence >= 1", name="sequence_positive"),
        sa.ForeignKeyConstraint(
            ["manuscript_id"],
            ["manuscripts.id"],
            name="fk_editorial_events_manuscript_id_manuscripts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("manuscript_id", "sequence", name="pk_editorial_events"),
        sa.UniqueConstraint("manuscript_id", "event_hash", name="event_hash_unique"),
    )
    op.create_index(
        "ix_editorial_events_manuscript_sequence",
        "editorial_events",
        ["manuscript_id", "sequence"],
    )

    op.execute(APPEND_ONLY_FUNCTION)
    op.execute(APPEND_ONLY_TRIGGER)
    op.execute(NO_TRUNCATE_TRIGGER)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS editorial_events_no_truncate ON editorial_events")
    op.execute("DROP TRIGGER IF EXISTS editorial_events_append_only ON editorial_events")
    op.execute("DROP FUNCTION IF EXISTS ugjcs_reject_event_mutation()")
    op.drop_table("editorial_events")
    op.drop_table("manuscript_authors")
    op.drop_table("manuscripts")
