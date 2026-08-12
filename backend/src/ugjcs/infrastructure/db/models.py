"""ORM rows. These are storage records, not domain objects.

They are deliberately separate from the aggregates in `ugjcs.domain`: the domain classes
are `slots=True` dataclasses that SQLAlchemy cannot instrument, and keeping them ignorant
of persistence is what the layers contract exists to protect.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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

    authors: Mapped[list["ManuscriptAuthorRow"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan",
        order_by="ManuscriptAuthorRow.position",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("submitted_reviews >= 0", name="reviews_non_negative"),
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
