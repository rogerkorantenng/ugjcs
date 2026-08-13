"""ORM rows. These are storage records, not domain objects.

They are deliberately separate from the aggregates in `ugjcs.domain`: the domain classes
are `slots=True` dataclasses that SQLAlchemy cannot instrument, and keeping them ignorant
of persistence is what the layers contract exists to protect.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ugjcs.infrastructure.db.base import Base


class ManuscriptRow(Base):
    __tablename__ = "manuscripts"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    tracking_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(postgresql.ARRAY(Text), default=list)
    corresponding_author_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    minimum_reviews: Mapped[int] = mapped_column(Integer, default=2)
    submitted_reviews: Mapped[int] = mapped_column(Integer, default=0)
    issue_id: Mapped[UUID | None] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True)
    original_document_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    anonymised_document_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fulltext: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Text extracted from the published PDF at publish time (or by the entrypoint
    backfill), for the archive's full-text search. NULL means "not extracted" — the
    manuscript is unpublished, pre-dates the feature, or its PDF yielded no text —
    and search treats it as an empty document, never as an error."""

    authors: Mapped[list["ManuscriptAuthorRow"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan",
        order_by="ManuscriptAuthorRow.position",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("submitted_reviews >= 0", name="reviews_non_negative"),
        # A GIN index over the same expression `search_published_with_snippets` queries
        # with — the expression must match the query's textually for the planner to use
        # it. Declared here as well as in migration 0008 so the metadata-built schema the
        # integration fixtures create agrees with the Alembic-built one, the parity
        # `test_migration_parity.py` exists to keep.
        Index(
            "ix_manuscripts_fulltext_tsv",
            text("to_tsvector('english', coalesce(fulltext, ''))"),
            postgresql_using="gin",
        ),
    )


class ManuscriptAuthorRow(Base):
    __tablename__ = "manuscript_authors"

    manuscript_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("manuscripts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    author_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)

    manuscript: Mapped[ManuscriptRow] = relationship(back_populates="authors")

    # Byline order is meaningful on a paper, and `order_by` alone resolves ties arbitrarily.
    __table_args__ = (UniqueConstraint("manuscript_id", "position", name="author_position_unique"),)


class EditorialEventRow(Base):
    """Append-only. A database trigger added in Task 3 rejects UPDATE and DELETE."""

    __tablename__ = "editorial_events"

    manuscript_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("manuscripts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    actor_id: Mapped[UUID | None] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("manuscript_id", "event_hash", name="event_hash_unique"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        Index("ix_editorial_events_manuscript_sequence", "manuscript_id", "sequence"),
    )


class ReviewAssignmentRow(Base):
    """A record that an editor asked a reviewer to review a manuscript, and what came back.

    Deliberately not a domain aggregate: see Plan 4's scope decision. There is no
    invitation/accept/decline lifecycle, no conflict-of-interest check, and no capacity
    limit enforced anywhere in this table's existence — an editor's assignment is final
    the moment it is recorded. `status` only ever takes the values `"assigned"` and
    `"submitted"`, a deliberate subset of `ugjcs.domain.enums.AssignmentStatus` that
    skips `INVITED`/`ACCEPTED`/`DECLINED`/`EXPIRED` because nothing here offers a
    reviewer the choice those states represent.
    """

    __tablename__ = "review_assignments"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    manuscript_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("manuscripts.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(16), default="assigned")
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # FR-11's four criterion scores, 1-5, and the author/editor comment split. All five
    # stay NULL until `mark_submitted` fills them in — an "assigned" row never has them.
    originality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rigour_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    significance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments_to_author: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidential_comments_to_editor: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Never serialised to an author — see `ugjcs.api.schemas.ReviewOut`."""
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    """When the review is expected back — `assigned_at + REVIEW_PERIOD` (21 days, see
    `ugjcs.application.ports.REVIEW_PERIOD`) for every assignment recorded since
    `0006_review_due_dates`, which also backfilled older rows from their `assigned_at`.
    Nullable because a deadline is bookkeeping, not an invariant: a NULL here means "no
    deadline recorded", and nothing downstream may treat it as "overdue"."""
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("manuscript_id", "reviewer_id", name="uq_review_assignments_pair"),
        CheckConstraint(
            "originality_score IS NULL OR originality_score BETWEEN 1 AND 5",
            name="originality_score_range",
        ),
        CheckConstraint(
            "rigour_score IS NULL OR rigour_score BETWEEN 1 AND 5", name="rigour_score_range"
        ),
        CheckConstraint(
            "clarity_score IS NULL OR clarity_score BETWEEN 1 AND 5", name="clarity_score_range"
        ),
        CheckConstraint(
            "significance_score IS NULL OR significance_score BETWEEN 1 AND 5",
            name="significance_score_range",
        ),
    )


class ApcInvoiceRow(Base):
    """One article processing charge per accepted manuscript.

    Created by the accept-decision path (`ugjcs.api.routers.editorial.record_decision`),
    settled by the billing routes. `manuscript_id` is UNIQUE — a manuscript is accepted
    once and owes one APC, and the constraint makes a double-billing bug loud rather
    than silently invoicing twice. `status` is a text enum checked in the schema, not a
    Postgres ENUM type, matching how every other closed vocabulary in this schema is
    stored (`manuscripts.status`, `review_assignments.status`).
    """

    __tablename__ = "apc_invoices"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    manuscript_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("manuscripts.id", ondelete="CASCADE"),
        unique=True,
    )
    amount_pesewas: Mapped[int] = mapped_column(Integer, default=15000)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    paystack_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("amount_pesewas > 0", name="apc_amount_positive"),
        CheckConstraint("status IN ('pending', 'paid', 'waived')", name="apc_status_vocabulary"),
    )


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    affiliation: Mapped[str] = mapped_column(String(255))
    expertise: Mapped[list[str]] = mapped_column(postgresql.ARRAY(Text), default=list)
    reviewer_capacity: Mapped[int] = mapped_column(Integer, default=3)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["UserRoleRow"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (CheckConstraint("reviewer_capacity >= 0", name="capacity_non_negative"),)


class UserRoleRow(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)

    user: Mapped[UserRow] = relationship(back_populates="roles")


class RefreshTokenRow(Base):
    """Only hashes are stored. A stolen database yields no usable refresh token."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[UUID | None] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True)
