"""Add manuscripts.fulltext and its GIN full-text index.

Revision ID: 0008
Revises: 0007

The column holds text extracted from the published PDF (`pypdf`, see
`ugjcs.infrastructure.storage.fulltext`); the expression index makes the archive's
`@@ plainto_tsquery` search a scan of the index rather than of every paper's prose.
The index expression must match `search_published_with_snippets`' query expression
*textually* — `to_tsvector('english', coalesce(fulltext, ''))` — or the planner will
never use it; the same expression is declared on the metadata in `models.py` so the
schema the integration fixtures build agrees with this one.

Deliberately no data step: extraction needs the PDF bytes, which live in S3, and a
migration that reaches into object storage would make `alembic upgrade head` depend on
credentials and network weather. The backfill is a separate idempotent script
(`ugjcs.scripts.backfill_fulltext`) the container entrypoint runs after migrating —
so papers published before this revision gain search the moment the next deploy boots.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("manuscripts", sa.Column("fulltext", sa.Text(), nullable=True))
    op.execute(
        "CREATE INDEX ix_manuscripts_fulltext_tsv ON manuscripts "
        "USING gin (to_tsvector('english', coalesce(fulltext, '')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_manuscripts_fulltext_tsv")
    op.drop_column("manuscripts", "fulltext")
