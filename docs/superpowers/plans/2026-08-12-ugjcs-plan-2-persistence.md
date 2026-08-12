# UGJCS Plan 2 — Persistence and the Repository Boundary

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the domain core built in Plan 1 to PostgreSQL without the domain learning that a database exists, and make the editorial event log genuinely append-only and verifiable after a round trip.

**Architecture:** The domain layer stays framework-free. SQLAlchemy ORM classes live in `infrastructure/db/models.py` and are *separate objects* from the domain aggregates; explicit mapper functions translate between them. This is not ceremony — `Manuscript` is a `slots=True` dataclass, which SQLAlchemy cannot instrument imperatively, so separate models are the only option that preserves the import-linter contract. Repositories are defined as protocols in `application/ports.py` and implemented in infrastructure, so use cases in later plans depend on the protocol, never the adapter.

**Tech Stack:** SQLAlchemy 2.0 (async, `asyncpg`), Alembic, PostgreSQL 16, pydantic-settings, pytest-asyncio, testcontainers.

## Global Constraints

- Python pinned to **3.13**. Everything runs via `uv run` from `backend/`.
- `backend/src/ugjcs/domain/` MUST NOT import `fastapi`, `sqlalchemy`, `pydantic`, `boto3`, `arq`, `redis` or `httpx`. The import-linter contract is extended in Task 1 to also forbid `ugjcs.domain` importing `ugjcs.infrastructure`, and `ugjcs.application` importing `ugjcs.infrastructure`.
- All timestamps are timezone-aware UTC; every `DateTime` column is `timezone=True`.
- Coverage gate stays at **85%**; `make check` must remain green at every commit.
- mypy `strict`; ruff line-length 100, select `["E","F","I","N","UP","B","A","C4","SIM","RUF"]`.
- **`ruff format` is authoritative** over hand-written line breaks in this document. Any *other* lint failure is escalated, never suppressed: no `# noqa`, `# fmt: off`, `# pragma: no cover`, or `pyproject.toml` edits.
- A project-wide 100-line file-size hook may fire. **It is not a gate.** Ignore it without justification.
- Conventional Commits. Author: Roger Koranteng Obeng, student ID 22424140.
- Integration tests require Docker. They are marked `@pytest.mark.integration` and excluded from the default unit run.

## Interfaces inherited from Plan 1

Implementers must not redefine these; import them.

- `ugjcs.domain.ids` — `UserId`, `ManuscriptId`, `ReviewId`, `IssueId` (`NewType` over `UUID`), `TrackingCode` with `.value`, `.mint(year, sequence)`, `.parse(raw)`
- `ugjcs.domain.enums` — `Role`, `ManuscriptStatus`, `Recommendation`, `DecisionType`, `AssignmentStatus`, `EventType` (11 members incl. `REVIEW_ROUND_CLOSED`)
- `ugjcs.domain.events` — `EditorialEvent(manuscript_id, sequence, event_type, payload, actor_id, occurred_at)`, `.canonical_bytes()`, and `type PayloadValue = str | int | float | bool | None`
- `ugjcs.domain.hashchain` — `GENESIS_HASH`, `ChainedEvent(event, previous_hash, event_hash)`, `chain_hash(event, previous_hash)`, `append(chain, event)`, `verify(chain)`, `ChainBrokenError`
- `ugjcs.domain.manuscript` — `Manuscript` dataclass with fields `id, tracking_code, title, abstract, keywords, author_ids, corresponding_author_id, status, version, minimum_reviews, submitted_reviews, issue_id, _sequence, _events`; `pending_events` property; `pull_events()`
- `ugjcs.domain.errors` — `DomainError`, `IllegalTransitionError`, `GuardViolationError`, `AuthorizationDeniedError`

**The obligation this plan must discharge:** `Manuscript._sequence` is a monotonic counter that `pull_events()` deliberately does not reset. `hashchain.append` requires consecutive sequences across the manuscript's whole life. A repository that rehydrates a `Manuscript` without seeding `_sequence` from the last persisted event will emit a duplicate sequence on the next state change and break the chain. Task 4 exists to discharge this, and Task 6 proves it.

---

## File Structure

```
backend/
├── pyproject.toml                              Task 1  new deps, pytest markers
├── .importlinter                               Task 1  layered contract
├── alembic.ini                                 Task 3
├── src/ugjcs/
│   ├── application/
│   │   ├── __init__.py                         Task 1
│   │   └── ports.py                            Task 1  repository + UoW protocols
│   └── infrastructure/
│       ├── __init__.py                         Task 1
│       ├── config.py                           Task 1  settings from environment
│       └── db/
│           ├── __init__.py                     Task 2
│           ├── base.py                         Task 2  DeclarativeBase, naming convention
│           ├── models.py                       Task 2  ORM tables
│           ├── mappers.py                      Task 4  domain <-> ORM translation
│           ├── engine.py                       Task 5  async engine + session factory
│           ├── repository.py                   Task 5  SqlAlchemyManuscriptRepository
│           └── uow.py                          Task 7  SqlAlchemyUnitOfWork
├── alembic/
│   ├── env.py                                  Task 3
│   └── versions/0001_initial.py                Task 3  schema + append-only trigger
└── tests/
    ├── unit/db/test_mappers.py                 Task 4
    └── integration/
        ├── conftest.py                         Task 5  testcontainers fixture
        ├── test_repository.py                  Task 5
        ├── test_append_only.py                 Task 6
        ├── test_chain_persistence.py           Task 6
        └── test_unit_of_work.py                Task 7
```

Mappers live apart from models because they change for different reasons: models change when the schema changes, mappers when the domain changes.

---

### Task 1: Layered contract, ports and configuration

**Files:**
- Modify: `backend/pyproject.toml`, `backend/.importlinter`
- Create: `backend/src/ugjcs/application/__init__.py`, `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/__init__.py`, `backend/src/ugjcs/infrastructure/config.py`

**Interfaces:**
- Produces: `ManuscriptRepository` and `UnitOfWork` protocols; `Settings` with `database_url`.

- [ ] **Step 1: Add dependencies**

```bash
cd backend
uv add "sqlalchemy[asyncio]>=2.0" asyncpg alembic pydantic-settings
uv add --dev pytest-asyncio "testcontainers[postgres]"
```

- [ ] **Step 2: Register the integration marker and async mode**

Add to `backend/pyproject.toml`, replacing the existing `[tool.pytest.ini_options]` block:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers -m 'not integration'"
asyncio_mode = "auto"
markers = [
    "integration: requires a live PostgreSQL container (deselected by default)",
]
```

The default run excludes integration tests so `make check` stays fast and Docker-free. Task 8 adds a separate command that runs them.

- [ ] **Step 3: Extend the architecture contract**

**Do not replace the whole file blindly.** Plan 1's final review strengthened the `domain-purity` denylist after this plan was drafted; an earlier version of this step carried the stale seven-name list and would have silently undone that fix. Add the `layers` contract, and leave `domain-purity` as it stands. The finished file is:

```ini
[importlinter]
root_package = ugjcs
include_external_packages = True

[importlinter:contract:domain-purity]
name = Domain layer imports no framework, vendor SDK, or I/O module
type = forbidden
source_modules =
    ugjcs.domain
forbidden_modules =
    fastapi
    sqlalchemy
    pydantic
    boto3
    arq
    redis
    httpx
    requests
    os
    io
    socket
    sqlite3
    subprocess
    pathlib
    asyncio
    threading
    multiprocessing
    logging
    http
    smtplib
    urllib

[importlinter:contract:layers]
name = Dependencies point inwards only
type = layers
layers =
    ugjcs.infrastructure
    ugjcs.application
    ugjcs.domain
```

The `layers` contract is the one that makes hexagonal architecture a fact rather than an intention: `domain` may not import `application` or `infrastructure`, and `application` may not import `infrastructure`.

- [ ] **Step 4: Write the ports**

Create `backend/src/ugjcs/application/ports.py`:

```python
"""Ports the application layer depends on.

These are protocols, not base classes. Infrastructure supplies implementations; the
application layer never imports them, which is what the layers contract enforces.
"""

from types import TracebackType
from typing import Protocol, Self

from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript


class ManuscriptRepository(Protocol):
    """Persistence for the manuscript aggregate and its event chain."""

    async def add(self, manuscript: Manuscript) -> None:
        """Persist a manuscript that has never been stored before."""
        ...

    async def get(self, manuscript_id: ManuscriptId) -> Manuscript | None:
        """Load a manuscript with its sequence counter restored, or None."""
        ...

    async def get_by_tracking_code(self, code: TrackingCode) -> Manuscript | None:
        """Load by the human-facing reference an author quotes."""
        ...

    async def save(self, manuscript: Manuscript) -> None:
        """Persist state changes and append any buffered events to the chain."""
        ...

    async def chain_for(self, manuscript_id: ManuscriptId) -> list[ChainedEvent]:
        """Return the full audit chain in sequence order, for verification."""
        ...


class UnitOfWork(Protocol):
    """A transactional boundary. Exiting without `commit` rolls back."""

    manuscripts: ManuscriptRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
```

- [ ] **Step 5: Write configuration**

Create `backend/src/ugjcs/infrastructure/config.py`:

```python
"""Runtime configuration, read from the environment.

Secrets never have defaults. A missing DATABASE_URL must fail loudly at startup rather
than silently falling back to something that appears to work in development.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UGJCS_", env_file=".env")

    database_url: str = Field(
        description="PostgreSQL DSN using the asyncpg driver, e.g. "
        "postgresql+asyncpg://user:pass@host:5432/ugjcs",
    )
    sql_echo: bool = Field(default=False, description="Log every statement; never in production")


@lru_cache
def get_settings() -> Settings:
    """Cached so configuration is parsed once per process."""
    return Settings()  # type: ignore[call-arg]
```

The `type: ignore` is required because pydantic-settings populates required fields from the environment, which mypy cannot see.

- [ ] **Step 6: Create the package files and verify**

Create empty `__init__.py` in `src/ugjcs/application/` and `src/ugjcs/infrastructure/`.

Run: `cd backend && make check`
Expected: all gates pass, including **two** contracts KEPT from `lint-imports`. Coverage may dip because `config.py` and `ports.py` have no tests; protocols and settings are declarations, and Task 4 onwards restores the figure. If coverage fails, report the number — do not add tests for protocol stubs.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/.importlinter backend/src/ugjcs/application backend/src/ugjcs/infrastructure
git commit -m "feat: add application ports, configuration and a layered architecture contract"
```

---

### Task 2: ORM models

**Files:**
- Create: `backend/src/ugjcs/infrastructure/db/__init__.py`, `backend/src/ugjcs/infrastructure/db/base.py`, `backend/src/ugjcs/infrastructure/db/models.py`

**Interfaces:**
- Produces: `Base`; `ManuscriptRow`, `ManuscriptAuthorRow`, `EditorialEventRow`.

- [ ] **Step 1: Write the declarative base**

Create `backend/src/ugjcs/infrastructure/db/base.py`:

```python
"""Declarative base with an explicit constraint naming convention.

Alembic cannot autogenerate a migration that drops an unnamed constraint, so naming them
deterministically here is what keeps future migrations reversible.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

- [ ] **Step 2: Write the models**

Create `backend/src/ugjcs/infrastructure/db/models.py`:

```python
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
        postgresql.UUID(as_uuid=True), ForeignKey("manuscripts.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)

    manuscript: Mapped[ManuscriptRow] = relationship(back_populates="authors")

    # Byline order is meaningful on a paper, and `order_by` alone resolves ties arbitrarily.
    __table_args__ = (
        UniqueConstraint("manuscript_id", "position", name="author_position_unique"),
    )


class EditorialEventRow(Base):
    """Append-only. A database trigger added in Task 3 rejects UPDATE and DELETE."""

    __tablename__ = "editorial_events"

    manuscript_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("manuscripts.id", ondelete="RESTRICT"), primary_key=True
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
```

Note the `ondelete="RESTRICT"` on the event foreign key: deleting a manuscript that has audit events must fail, not cascade. An audit trail that disappears with its subject is not an audit trail.

- [ ] **Step 3: Verify the metadata builds**

Run:
```bash
cd backend && uv run python -c "
from ugjcs.infrastructure.db.models import Base
print(sorted(Base.metadata.tables))
"
```
Expected: `['editorial_events', 'manuscript_authors', 'manuscripts']`

- [ ] **Step 4: Run the gates**

Run: `cd backend && make check`
Expected: ruff, mypy, and both import contracts pass. Report the coverage figure.

- [ ] **Step 5: Commit**

```bash
git add backend/src/ugjcs/infrastructure/db
git commit -m "feat: add ORM models for manuscripts, authors and editorial events"
```

---

### Task 3: Alembic migration with an append-only event table

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`

**Interfaces:**
- Produces: revision `0001`, creating all three tables plus the trigger that makes `editorial_events` genuinely append-only.

- [ ] **Step 1: Initialise Alembic**

```bash
cd backend && uv run alembic init -t async alembic
```

- [ ] **Step 2: Point `env.py` at the models and settings**

In `backend/alembic/env.py`, replace the `target_metadata = None` line with:

```python
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.base import Base
from ugjcs.infrastructure.db import models  # noqa: F401  ensures tables are registered

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings().database_url)
```

The `noqa: F401` here is **authorised**: importing `models` purely for its registration side effect is the documented Alembic pattern, and without it autogenerate sees an empty schema. This is the single permitted suppression in this plan.

- [ ] **Step 3: Write the initial migration**

Create `backend/alembic/versions/0001_initial.py`:

```python
"""Initial schema with an append-only editorial event log.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

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
        sa.CheckConstraint("version >= 1", name="ck_manuscripts_version_positive"),
        sa.CheckConstraint("submitted_reviews >= 0", name="ck_manuscripts_reviews_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_manuscripts"),
        sa.UniqueConstraint("tracking_code", name="uq_manuscripts_tracking_code"),
    )
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
        sa.CheckConstraint("sequence >= 1", name="ck_editorial_events_sequence_positive"),
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


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS editorial_events_append_only ON editorial_events")
    op.execute("DROP FUNCTION IF EXISTS ugjcs_reject_event_mutation()")
    op.drop_table("editorial_events")
    op.drop_table("manuscript_authors")
    op.drop_table("manuscripts")
```

**Two constraint names look inconsistent, and that is correct.** The naming convention's `uq`
template is `uq_%(table_name)s_%(column_0_name)s`, which contains no `%(constraint_name)s` token,
so SQLAlchemy uses an explicitly supplied `name=` verbatim rather than expanding it. `event_hash_unique`
and `author_position_unique` therefore keep those exact names, while the `ck` template does contain
the token and so expands `version_positive` into `ck_manuscripts_version_positive`. The migration must
match the metadata exactly or Task 8's parity test will fail — which is what that test is for.

- [ ] **Step 4: Verify the migration applies and reverses**

Start a throwaway database and round-trip the migration:

```bash
docker run --rm -d --name ugjcs-mig -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=ugjcs -p 55432:5432 postgres:16
sleep 5
cd backend
UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@localhost:55432/ugjcs uv run alembic upgrade head
UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@localhost:55432/ugjcs uv run alembic downgrade base
UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@localhost:55432/ugjcs uv run alembic upgrade head
docker rm -f ugjcs-mig
```

Expected: all three commands succeed. A migration that cannot be reversed is a migration you cannot roll back in production — verify the downgrade, do not assume it.

- [ ] **Step 5: Run the gates and commit**

Run: `cd backend && make check`, then:

```bash
git add backend/alembic.ini backend/alembic
git commit -m "feat: add initial migration with an append-only editorial event trigger"
```

---

### Task 4: Mappers, including sequence rehydration

**Files:**
- Create: `backend/src/ugjcs/infrastructure/db/mappers.py`
- Test: `backend/tests/unit/db/test_mappers.py`, `backend/tests/unit/db/__init__.py`

**Interfaces:**
- Consumes: domain aggregates and `models.py` rows.
- Produces: `to_row(manuscript) -> ManuscriptRow`, `to_domain(row, last_sequence) -> Manuscript`, `event_to_row(chained, manuscript_id) -> EditorialEventRow`, `row_to_chained(row) -> ChainedEvent`.

**This task discharges the `_sequence` obligation.** `to_domain` takes the last persisted sequence and seeds the counter.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/db/__init__.py` (empty) and `backend/tests/unit/db/test_mappers.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

from ugjcs.domain.enums import EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.hashchain import GENESIS_HASH, append
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.mappers import (
    event_to_row,
    row_to_chained,
    to_domain,
    to_row,
)

AUTHOR = UserId(uuid4())
COAUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 12),
        title="Sparse Retrieval for Low-Resource Languages",
        abstract="A sparse retrieval baseline for Akan and Ewe corpora.",
        keywords=("information retrieval", "low-resource"),
        author_ids=(AUTHOR, COAUTHOR),
        corresponding_author_id=AUTHOR,
    )


def test_row_carries_every_scalar_field() -> None:
    manuscript = make_manuscript()
    row = to_row(manuscript)
    assert row.id == manuscript.id
    assert row.tracking_code == "UGJCS-2026-0012"
    assert row.title == manuscript.title
    assert row.abstract == manuscript.abstract
    assert row.keywords == ["information retrieval", "low-resource"]
    assert row.status == "draft"
    assert row.version == 1
    assert row.corresponding_author_id == AUTHOR


def test_row_preserves_author_order() -> None:
    row = to_row(make_manuscript())
    assert [author.author_id for author in row.authors] == [AUTHOR, COAUTHOR]
    assert [author.position for author in row.authors] == [0, 1]


def test_round_trip_restores_the_aggregate() -> None:
    original = make_manuscript()
    restored = to_domain(to_row(original), last_sequence=0)
    assert restored.id == original.id
    assert restored.tracking_code == original.tracking_code
    assert restored.author_ids == original.author_ids
    assert restored.corresponding_author_id == original.corresponding_author_id
    assert restored.status is original.status
    assert restored.keywords == original.keywords


def test_rehydration_seeds_the_sequence_counter() -> None:
    """Without this, the next event collides with one already in the chain."""
    restored = to_domain(to_row(make_manuscript()), last_sequence=7)
    restored.status = S.SUBMITTED
    event = restored.begin_screening(actor_id=UserId(uuid4()), occurred_at=NOW)
    assert event.sequence == 8


def test_a_fresh_aggregate_starts_its_sequence_at_one() -> None:
    restored = to_domain(to_row(make_manuscript()), last_sequence=0)
    event = restored.submit(actor_id=AUTHOR, occurred_at=NOW)
    assert event.sequence == 1


def test_event_round_trip_preserves_the_hash() -> None:
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    chained = append([], manuscript.pending_events[0])
    row = event_to_row(chained, manuscript.id)
    assert row.previous_hash == GENESIS_HASH
    assert row.event_hash == chained.event_hash
    assert row.event_type == EventType.MANUSCRIPT_SUBMITTED.value
    assert row_to_chained(row) == chained


def test_event_row_keeps_the_timestamp_timezone_aware() -> None:
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    row = event_to_row(append([], manuscript.pending_events[0]), manuscript.id)
    assert row.occurred_at.tzinfo is not None
    assert row_to_chained(row).event.occurred_at == NOW
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/db/test_mappers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.infrastructure.db.mappers'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/infrastructure/db/mappers.py`:

```python
"""Translation between domain aggregates and storage rows.

Kept apart from `models.py` because the two change for different reasons: models change
with the schema, mappers with the domain.
"""

from ugjcs.domain.enums import EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.models import (
    EditorialEventRow,
    ManuscriptAuthorRow,
    ManuscriptRow,
)


def to_row(manuscript: Manuscript) -> ManuscriptRow:
    """Project an aggregate onto a storage row, authors included in order."""
    return ManuscriptRow(
        id=manuscript.id,
        tracking_code=manuscript.tracking_code.value,
        title=manuscript.title,
        abstract=manuscript.abstract,
        keywords=list(manuscript.keywords),
        corresponding_author_id=manuscript.corresponding_author_id,
        status=manuscript.status.value,
        version=manuscript.version,
        minimum_reviews=manuscript.minimum_reviews,
        submitted_reviews=manuscript.submitted_reviews,
        issue_id=manuscript.issue_id,
        authors=[
            ManuscriptAuthorRow(manuscript_id=manuscript.id, author_id=author_id, position=position)
            for position, author_id in enumerate(manuscript.author_ids)
        ],
    )


def to_domain(row: ManuscriptRow, *, last_sequence: int) -> Manuscript:
    """Rebuild an aggregate, restoring the monotonic event sequence counter.

    `last_sequence` must be the highest sequence already persisted for this manuscript.
    Passing 0 means no events exist yet. Getting this wrong silently reissues a sequence
    number that is already in the chain, and `hashchain.append` will reject the next event.
    """
    manuscript = Manuscript(
        id=ManuscriptId(row.id),
        tracking_code=TrackingCode.parse(row.tracking_code),
        title=row.title,
        abstract=row.abstract,
        keywords=tuple(row.keywords),
        author_ids=tuple(UserId(author.author_id) for author in row.authors),
        corresponding_author_id=UserId(row.corresponding_author_id),
        status=S(row.status),
        version=row.version,
        minimum_reviews=row.minimum_reviews,
        submitted_reviews=row.submitted_reviews,
        issue_id=IssueId(row.issue_id) if row.issue_id is not None else None,
    )
    manuscript._sequence = last_sequence
    return manuscript


def event_to_row(chained: ChainedEvent, manuscript_id: ManuscriptId) -> EditorialEventRow:
    """Store a linked event, hashes and all."""
    return EditorialEventRow(
        manuscript_id=manuscript_id,
        sequence=chained.event.sequence,
        event_type=chained.event.event_type.value,
        payload=dict(chained.event.payload),
        actor_id=chained.event.actor_id,
        occurred_at=chained.event.occurred_at,
        previous_hash=chained.previous_hash,
        event_hash=chained.event_hash,
    )


def row_to_chained(row: EditorialEventRow) -> ChainedEvent:
    """Rebuild a linked event exactly as it was hashed."""
    payload: dict[str, PayloadValue] = dict(row.payload)  # type: ignore[arg-type]
    return ChainedEvent(
        event=EditorialEvent(
            manuscript_id=ManuscriptId(row.manuscript_id),
            sequence=row.sequence,
            event_type=EventType(row.event_type),
            payload=payload,
            actor_id=UserId(row.actor_id) if row.actor_id is not None else None,
            occurred_at=row.occurred_at,
        ),
        previous_hash=row.previous_hash,
        event_hash=row.event_hash,
    )
```

`manuscript._sequence = last_sequence` reaches past a private name deliberately. The alternative — a public setter — would let any caller rewrite the counter, which is precisely the mistake this attribute exists to prevent. Assignment here is confined to the one function whose job is rehydration.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit/db/test_mappers.py -v`
Expected: PASS, 7 tests.

If `test_rehydration_seeds_the_sequence_counter` fails, the mapper is not seeding `_sequence` — fix the mapper, never the test. That test is the whole point of this task.

- [ ] **Step 5: Run the gates and commit**

Run: `cd backend && make check`, then:

```bash
git add backend/src/ugjcs/infrastructure/db/mappers.py backend/tests/unit/db
git commit -m "feat: map manuscripts and events between domain and storage"
```

---

### Task 5: Repository and integration harness

**Files:**
- Create: `backend/src/ugjcs/infrastructure/db/engine.py`, `backend/src/ugjcs/infrastructure/db/repository.py`, `backend/tests/integration/__init__.py`, `backend/tests/integration/conftest.py`, `backend/tests/integration/test_repository.py`

**Interfaces:**
- Consumes: `ManuscriptRepository` protocol, mappers, models.
- Produces: `create_engine(url, echo)`, `session_factory(engine)`, `SqlAlchemyManuscriptRepository(session)`.

- [ ] **Step 1: Write the engine module**

Create `backend/src/ugjcs/infrastructure/db/engine.py`:

```python
"""Async engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ugjcs.infrastructure.config import get_settings


def create_engine(url: str | None = None, *, echo: bool | None = None) -> AsyncEngine:
    """Build an engine, falling back to configured settings only for what was not supplied.

    Settings are read lazily and only when needed. Reading them unconditionally would make
    this function require `UGJCS_DATABASE_URL` even when the caller supplied a URL — which
    would break every integration test, since those point at a throwaway container and set
    no environment at all.

    `pool_pre_ping` costs one round trip per checkout and saves the first request after an
    idle connection is dropped by RDS or a load balancer.
    """
    if url is None or echo is None:
        settings = get_settings()
        url = url if url is not None else settings.database_url
        echo = echo if echo is not None else settings.sql_echo
    return create_async_engine(url, echo=echo, pool_pre_ping=True)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessions do not expire attributes on commit, so aggregates stay readable after."""
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 2: Write the repository**

Create `backend/src/ugjcs/infrastructure/db/repository.py`:

```python
"""PostgreSQL implementation of the manuscript repository port."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.hashchain import ChainedEvent, append
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.mappers import (
    event_to_row,
    row_to_chained,
    to_domain,
    to_row,
)
from ugjcs.infrastructure.db.models import EditorialEventRow, ManuscriptRow


class SqlAlchemyManuscriptRepository:
    """Persists the aggregate and appends its buffered events to the audit chain."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, manuscript: Manuscript) -> None:
        self._session.add(to_row(manuscript))
        await self._flush_events(manuscript)

    async def get(self, manuscript_id: ManuscriptId) -> Manuscript | None:
        row = await self._session.get(ManuscriptRow, manuscript_id)
        return await self._rehydrate(row)

    async def get_by_tracking_code(self, code: TrackingCode) -> Manuscript | None:
        result = await self._session.execute(
            select(ManuscriptRow).where(ManuscriptRow.tracking_code == code.value)
        )
        return await self._rehydrate(result.scalar_one_or_none())

    async def save(self, manuscript: Manuscript) -> None:
        row = await self._session.get(ManuscriptRow, manuscript.id)
        if row is None:
            raise LookupError(f"manuscript {manuscript.id} has never been persisted")
        row.status = manuscript.status.value
        row.version = manuscript.version
        row.submitted_reviews = manuscript.submitted_reviews
        row.issue_id = manuscript.issue_id
        await self._flush_events(manuscript)

    async def chain_for(self, manuscript_id: ManuscriptId) -> list[ChainedEvent]:
        result = await self._session.execute(
            select(EditorialEventRow)
            .where(EditorialEventRow.manuscript_id == manuscript_id)
            .order_by(EditorialEventRow.sequence)
        )
        return [row_to_chained(row) for row in result.scalars()]

    async def _rehydrate(self, row: ManuscriptRow | None) -> Manuscript | None:
        if row is None:
            return None
        last_sequence = await self._last_sequence(ManuscriptId(row.id))
        return to_domain(row, last_sequence=last_sequence)

    async def _last_sequence(self, manuscript_id: ManuscriptId) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(EditorialEventRow.sequence), 0)).where(
                EditorialEventRow.manuscript_id == manuscript_id
            )
        )
        return int(result.scalar_one())

    async def _flush_events(self, manuscript: Manuscript) -> None:
        """Link buffered events onto the stored chain and drain the aggregate."""
        pending = manuscript.pull_events()
        if not pending:
            return
        chain = await self.chain_for(manuscript.id)
        for event in pending:
            link = append(chain, event)
            chain.append(link)
            self._session.add(event_to_row(link, manuscript.id))
```

- [ ] **Step 3: Write the integration fixtures**

Create `backend/tests/integration/__init__.py` (empty) and `backend/tests/integration/conftest.py`:

```python
"""Integration fixtures. One PostgreSQL container per test session."""

from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer

from ugjcs.infrastructure.db.base import Base
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.models import EditorialEventRow  # noqa: F401  register tables

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


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        yield container.get_connection_url()


@pytest.fixture
async def session(postgres_url: str) -> AsyncIterator[AsyncSession]:
    """A clean schema per test, with the append-only trigger installed."""
    engine = create_engine(postgres_url, echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
        await connection.exec_driver_sql(APPEND_ONLY_FUNCTION)
        await connection.exec_driver_sql(APPEND_ONLY_TRIGGER)
    factory = session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()
```

**`get_settings()` is `@lru_cache`d, so never let a test depend on it.** The fixture passes both
`postgres_url` and `echo` explicitly, which is what keeps `create_engine` from reading settings at
all. Anything that does call `get_settings()` in a test must call `get_settings.cache_clear()` first,
or it silently receives configuration captured by an earlier test in the same process.

The trigger is created here as well as in the migration because these tests build the schema from metadata rather than by running Alembic. Task 8 adds a separate check that the migration itself produces the same trigger, so the duplication cannot drift unnoticed.

The `noqa: F401` is authorised for the same registration-side-effect reason as Alembic's.

- [ ] **Step 4: Write the repository tests**

Create `backend/tests/integration/test_repository.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
EDITOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 10, 0, tzinfo=UTC)


def make_manuscript(sequence: int = 1) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Adaptive Bitrate Selection over Intermittent Links",
        abstract="A controller for video delivery under bandwidth collapse.",
        keywords=("networking", "video"),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


async def test_a_stored_manuscript_can_be_read_back(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    assert loaded.tracking_code == manuscript.tracking_code
    assert loaded.status is S.SUBMITTED
    assert loaded.author_ids == (AUTHOR,)


async def test_a_missing_manuscript_reads_back_as_none(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    assert await repository.get(ManuscriptId(uuid4())) is None


async def test_lookup_by_tracking_code(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript(sequence=44)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get_by_tracking_code(TrackingCode.mint(2026, 44))
    assert loaded is not None
    assert loaded.id == manuscript.id


async def test_saving_an_unpersisted_manuscript_is_refused(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    with pytest.raises(LookupError, match="never been persisted"):
        await repository.save(make_manuscript())


async def test_state_changes_survive_a_round_trip(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript(sequence=7)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    await repository.save(loaded)
    await session.commit()

    reloaded = await repository.get(manuscript.id)
    assert reloaded is not None
    assert reloaded.status is S.UNDER_SCREENING
```

- [ ] **Step 5: Run the integration tests**

Run: `cd backend && uv run pytest tests/integration/test_repository.py -m integration -v`
Expected: PASS, 5 tests. The first run pulls the `postgres:16` image, so allow time.

If Docker is unavailable, report BLOCKED rather than skipping — these tests are the point of the task.

- [ ] **Step 6: Run the gates and commit**

Run: `cd backend && make check` (integration tests are deselected by default and must not run here).

```bash
git add backend/src/ugjcs/infrastructure/db/engine.py backend/src/ugjcs/infrastructure/db/repository.py backend/tests/integration
git commit -m "feat: add async engine and PostgreSQL manuscript repository"
```

---

### Task 6: Prove the audit trail holds across persistence

**Files:**
- Create: `backend/tests/integration/test_append_only.py`, `backend/tests/integration/test_chain_persistence.py`

**Interfaces:**
- Consumes: the repository and the container fixture. Produces no production code.

This task is the reason the plan exists. Plan 1 proved the chain is sound *in memory*. These tests prove it survives a database, and that the database itself refuses to let anyone rewrite history.

- [ ] **Step 1: Write the append-only tests**

Create `backend/tests/integration/test_append_only.py`:

```python
"""The database must refuse to rewrite the audit log, not merely decline to offer an API."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)


async def stored_manuscript(session: AsyncSession) -> Manuscript:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 21),
        title="Edge Caching for Campus Networks",
        abstract="A cache placement strategy for constrained campus links.",
        keywords=("caching",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()
    return manuscript


async def test_updating_an_event_is_rejected_by_the_database(session: AsyncSession) -> None:
    manuscript = await stored_manuscript(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(
            text("UPDATE editorial_events SET event_type = 'forged' WHERE manuscript_id = :id"),
            {"id": manuscript.id},
        )


async def test_deleting_an_event_is_rejected_by_the_database(session: AsyncSession) -> None:
    manuscript = await stored_manuscript(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(
            text("DELETE FROM editorial_events WHERE manuscript_id = :id"),
            {"id": manuscript.id},
        )


async def test_deleting_a_manuscript_with_events_is_refused(session: AsyncSession) -> None:
    """ondelete=RESTRICT: an audit trail that vanishes with its subject is not a trail."""
    manuscript = await stored_manuscript(session)
    with pytest.raises(DBAPIError):
        await session.execute(
            text("DELETE FROM manuscripts WHERE id = :id"), {"id": manuscript.id}
        )
```

- [ ] **Step 2: Write the chain persistence tests**

Create `backend/tests/integration/test_chain_persistence.py`:

```python
"""The chain must verify after a round trip, and keep verifying as events accumulate."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import DecisionType
from ugjcs.domain.hashchain import GENESIS_HASH, verify
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
EDITOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def make_manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 33),
        title="Fair Scheduling for Shared GPU Clusters",
        abstract="A scheduler balancing fairness against utilisation.",
        keywords=("scheduling",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


async def test_a_persisted_chain_verifies(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    chain = await repository.chain_for(manuscript.id)
    verify(chain)
    assert len(chain) == 1
    assert chain[0].previous_hash == GENESIS_HASH


async def test_the_chain_stays_consecutive_across_separate_transactions(
    session: AsyncSession,
) -> None:
    """The regression this whole plan exists to prevent.

    Each save drains the aggregate's buffer. If rehydration failed to restore the sequence
    counter, the second transaction would emit sequence 1 again and `append` would reject it.
    """
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    await repository.save(loaded)
    await session.commit()

    reloaded = await repository.get(manuscript.id)
    assert reloaded is not None
    reloaded.record_decision(
        decision=DecisionType.SEND_TO_REVIEW,
        actor_id=EDITOR,
        rationale="In scope",
        occurred_at=NOW,
    )
    await repository.save(reloaded)
    await session.commit()

    chain = await repository.chain_for(manuscript.id)
    verify(chain)
    assert [link.event.sequence for link in chain] == [1, 2, 3]


async def test_each_stored_link_points_at_its_predecessor(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    await repository.save(loaded)
    await session.commit()

    chain = await repository.chain_for(manuscript.id)
    assert chain[1].previous_hash == chain[0].event_hash
```

- [ ] **Step 3: Run the integration tests**

Run: `cd backend && uv run pytest tests/integration -m integration -v`
Expected: PASS, 11 tests in total across all three integration modules.

`test_the_chain_stays_consecutive_across_separate_transactions` is the load-bearing one. If it fails with `ChainBrokenError: expected sequence 2, received 1`, the mapper is not seeding `_sequence` — fix Task 4's mapper, not this test.

- [ ] **Step 4: Run the gates and commit**

Run: `cd backend && make check`, then:

```bash
git add backend/tests/integration/test_append_only.py backend/tests/integration/test_chain_persistence.py
git commit -m "test: prove the audit chain survives persistence and cannot be rewritten"
```

---

### Task 7: Unit of work

**Files:**
- Create: `backend/src/ugjcs/infrastructure/db/uow.py`, `backend/tests/integration/test_unit_of_work.py`

**Interfaces:**
- Consumes: `UnitOfWork` protocol, session factory, repository.
- Produces: `SqlAlchemyUnitOfWork(session_factory)` with `.manuscripts`, `commit()`, `rollback()`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_unit_of_work.py`:

```python
"""A transaction boundary that rolls back unless commit is called explicitly."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.engine import session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)


def make_manuscript(sequence: int) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Congestion Control for Satellite Backhaul",
        abstract="A congestion controller for high-latency backhaul links.",
        keywords=("congestion control",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    return manuscript


async def test_work_is_visible_after_commit(engine: AsyncEngine) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    manuscript = make_manuscript(61)
    async with uow:
        await uow.manuscripts.add(manuscript)
        await uow.commit()

    async with uow:
        assert await uow.manuscripts.get(manuscript.id) is not None


async def test_work_is_discarded_without_commit(engine: AsyncEngine) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    manuscript = make_manuscript(62)
    async with uow:
        await uow.manuscripts.add(manuscript)

    async with uow:
        assert await uow.manuscripts.get(manuscript.id) is None


async def test_an_exception_rolls_the_transaction_back(engine: AsyncEngine) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    manuscript = make_manuscript(63)
    with pytest.raises(RuntimeError, match="deliberate"):
        async with uow:
            await uow.manuscripts.add(manuscript)
            raise RuntimeError("deliberate failure after a write")

    async with uow:
        assert await uow.manuscripts.get(manuscript.id) is None
```

This test needs an `engine` fixture rather than a `session`. Add to `backend/tests/integration/conftest.py`:

```python
@pytest.fixture
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    """A clean schema per test, exposed as an engine for unit-of-work tests."""
    engine = create_engine(postgres_url, echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
        await connection.exec_driver_sql(APPEND_ONLY_FUNCTION)
        await connection.exec_driver_sql(APPEND_ONLY_TRIGGER)
    yield engine
    await engine.dispose()
```

and extend its imports with `from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_unit_of_work.py -m integration -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.infrastructure.db.uow'`

- [ ] **Step 3: Write the implementation**

Create `backend/src/ugjcs/infrastructure/db/uow.py`:

```python
"""Transactional boundary.

Rollback on exit is unconditional: it is a no-op after a successful commit, and it is the
safety net that stops a forgotten `commit()` from leaving a half-written transaction open.
"""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository


class SqlAlchemyUnitOfWork:
    manuscripts: SqlAlchemyManuscriptRepository

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self.manuscripts = SqlAlchemyManuscriptRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        await self._session.rollback()
        await self._session.close()
        self._session = None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("commit outside an active unit of work")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("rollback outside an active unit of work")
        await self._session.rollback()
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/integration/test_unit_of_work.py -m integration -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Run the gates and commit**

Run: `cd backend && make check`, then:

```bash
git add backend/src/ugjcs/infrastructure/db/uow.py backend/tests/integration/test_unit_of_work.py backend/tests/integration/conftest.py
git commit -m "feat: add a unit of work that rolls back unless committed"
```

---

### Task 8: Migration parity check and CI for integration tests

**Files:**
- Create: `backend/tests/integration/test_migration_parity.py`
- Modify: `backend/Makefile`, `.github/workflows/backend-ci.yml`

**Interfaces:**
- Produces: `make integration`; a CI job running integration tests against a PostgreSQL service.

The parity test closes a real risk introduced in Task 5: the test schema is built from metadata plus a hand-copied trigger, while production is built by Alembic. Those two can drift, and if they do, every integration test could pass against a schema production never has.

- [ ] **Step 1: Write the parity test**

Create `backend/tests/integration/test_migration_parity.py`:

```python
"""The migration and the metadata must produce the same schema.

Integration tests build the schema from `Base.metadata`; production builds it with Alembic.
Nothing forces those to agree, so this test asserts it explicitly.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {"editorial_events", "manuscript_authors", "manuscripts"}


async def test_the_expected_tables_exist(session: AsyncSession) -> None:
    result = await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    assert EXPECTED_TABLES <= {row[0] for row in result}


async def test_the_append_only_trigger_is_installed(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT tgname FROM pg_trigger "
            "WHERE tgrelid = 'editorial_events'::regclass AND NOT tgisinternal"
        )
    )
    assert "editorial_events_append_only" in {row[0] for row in result}


async def test_the_event_primary_key_is_manuscript_and_sequence(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'editorial_events'::regclass AND i.indisprimary"
        )
    )
    assert {row[0] for row in result} == {"manuscript_id", "sequence"}
```

- [ ] **Step 2: Add the Makefile target**

Add to `backend/Makefile`:

```make
integration:
	uv run pytest -m integration -v
```

and add `integration` to the `.PHONY` line.

- [ ] **Step 3: Add the CI job**

Append to `.github/workflows/backend-ci.yml`, as a sibling of the existing `check` job:

```yaml
  integration:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ugjcs
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Verify the migration applies and reverses
        env:
          UGJCS_DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/ugjcs
        run: |
          uv run alembic upgrade head
          uv run alembic downgrade base
          uv run alembic upgrade head

      - name: Integration tests
        env:
          UGJCS_DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/ugjcs
        run: uv run pytest -m integration -v
```

Note the migration is exercised in CI on every push — a migration that only ever runs in production is a migration nobody has tested.

- [ ] **Step 4: Verify**

Run:
```bash
cd backend && uv run pytest -m integration -v
python3 -c "import yaml; d=yaml.safe_load(open('../.github/workflows/backend-ci.yml')); print(sorted(d['jobs']))"
```
Expected: 14 integration tests pass; the workflow reports `['check', 'integration']`.

Then `cd backend && make check` — the default run must still deselect integration tests and stay green.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_migration_parity.py backend/Makefile .github/workflows/backend-ci.yml
git commit -m "ci: run integration tests and verify the migration round-trips"
```

---

## Definition of done for Plan 2

- `cd backend && make check` passes: ruff, format, mypy strict, **two** import contracts, and unit tests at or above 85% coverage.
- `cd backend && make integration` passes 14 tests against a real PostgreSQL container.
- A manuscript survives a full round trip with its status, authorship and version intact.
- The audit chain verifies after persistence, and stays consecutive across separate transactions — the regression this plan exists to prevent.
- The database itself rejects `UPDATE` and `DELETE` on `editorial_events`, and refuses to delete a manuscript that has audit events.
- The migration applies, reverses and re-applies cleanly, and CI proves it on every push.

## Deliberately not in this plan

Users, roles, password hashing and tokens; the `Actor` construction the policy layer needs; HTTP routing; reviews, assignments and issues as stored entities. Those belong to Plan 3 (authentication and identity) and Plan 4 (the editorial API).

The `ExpertiseScorer` port for Bedrock-backed reviewer matching is **not** declared here. A protocol with no implementer is dead code; it belongs in the plan that introduces matching, alongside its first two adapters.

## Carried forward from Plan 1's reviews

- `Actor.roles` is caller-supplied and unverified by the domain. Plan 3 must guarantee roles are authentic and current before constructing an `Actor`.
- `_can_view` grants on identity alone, without requiring `Role.AUTHOR`, whereas `RESUBMIT` requires both. Confirm this asymmetry is intended when the API layer lands.
- The hash chain has no external anchor, so tail truncation and wholesale forgery remain undetectable by the application alone. Task 6 here narrows the exposure by making the *database* reject mutation, but the anchor itself stays in the technical debt register.
