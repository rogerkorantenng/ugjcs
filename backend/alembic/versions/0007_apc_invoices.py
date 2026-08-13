"""Add apc_invoices: one article processing charge per accepted manuscript.

Revision ID: 0007
Revises: 0006

Opened automatically by the accept-decision path (`ugjcs.api.routers.editorial`),
settled or waived by the billing routes. `manuscript_id` is UNIQUE — one acceptance,
one charge — and `status` is a CHECK-constrained text enum ('pending'|'paid'|'waived'),
stored the same way every other closed vocabulary in this schema is (a Postgres ENUM
type would make the next status a migration instead of a code change, for no gain at
three values). `ON DELETE CASCADE` matches `review_assignments`: the entrypoint's
prune/wipe scripts delete demonstration manuscripts wholesale, and an invoice for a
manuscript that no longer exists is meaningless.

No server defaults, mirroring the metadata in `models.py`: `amount_pesewas` (15000 =
GHS 150, the test tariff) and `created_at` are always supplied by the application, and
a column default computed from the database's clock would let invoice and decision
timestamps drift — the same reasoning `0006_review_due_dates` recorded for `due_at`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "apc_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manuscript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_pesewas", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("paystack_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["manuscript_id"],
            ["manuscripts.id"],
            name="fk_apc_invoices_manuscript_id_manuscripts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_apc_invoices"),
        sa.UniqueConstraint("manuscript_id", name="uq_apc_invoices_manuscript_id"),
        # Named with the metadata's `ck_%(table_name)s_%(constraint_name)s` convention
        # spelled out (op.create_table applies no naming convention of its own), so the
        # Alembic-built schema and the metadata-built one carry identical catalogue
        # names — the drift `test_migration_parity.py` checks for.
        sa.CheckConstraint("amount_pesewas > 0", name="ck_apc_invoices_apc_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'paid', 'waived')", name="ck_apc_invoices_apc_status_vocabulary"
        ),
    )


def downgrade() -> None:
    op.drop_table("apc_invoices")
