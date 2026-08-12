"""Ports the application layer depends on.

These are protocols, not base classes. Infrastructure supplies implementations; the
application layer never imports them, which is what the layers contract enforces.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import ManuscriptStatus
from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
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

    async def list_published(self) -> list[Manuscript]:
        """Every published manuscript — the public archive's contents."""
        ...

    async def search_published(self, query: str) -> list[Manuscript]:
        """Published manuscripts whose title or abstract contains `query`, case-insensitively."""
        ...

    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        """Every manuscript on which this user appears as an author, newest first."""
        ...

    async def list_by_status(self, status: ManuscriptStatus) -> list[Manuscript]:
        """Every manuscript currently in this state — the screening queue's source."""
        ...

    async def list_by_statuses(self, statuses: frozenset[ManuscriptStatus]) -> list[Manuscript]:
        """Every manuscript currently in any of these states — the editorial queue's
        source, which needs several non-terminal states at once, not just one."""
        ...


class AccountRepository(Protocol):
    """Persistence for the account aggregate and its role grants."""

    async def add(self, account: Account) -> None:
        """Persist an account that has never been stored before."""
        ...

    async def get(self, user_id: UserId) -> Account | None: ...

    async def get_by_email(self, email: EmailAddress) -> Account | None:
        """Look up by the normalised address. Case and whitespace never distinguish accounts."""
        ...

    async def save(self, account: Account) -> None:
        """Persist scalar field changes and replace the role rows to match `account.roles`."""
        ...


@dataclass(frozen=True, slots=True)
class RefreshTokenRecord:
    """A `refresh_tokens` row, as far as the application layer needs to see it."""

    id: UUID
    user_id: UserId
    family_id: UUID
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by: UUID | None


class RefreshTokenRepository(Protocol):
    async def add(self, record: RefreshTokenRecord) -> None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None: ...

    async def revoke(self, token_id: UUID, *, replaced_by: UUID | None = None) -> None:
        """Mark a single token spent. `replaced_by` records the row that superseded it."""
        ...

    async def revoke_family(self, family_id: UUID) -> None:
        """Revoke every unrevoked token sharing this family — the reuse-detection response."""
        ...


@dataclass(frozen=True, slots=True)
class ReviewAssignmentRecord:
    """A read model, not an aggregate — there is no invariant here for a domain type to
    protect. See Plan 4's scope decision for why.

    FR-11 requires a structured review: four criterion scores (1-5), an overall
    recommendation, comments to the author, and comments to the editor alone. The last
    field is the one that must never reach an author-facing response model — see
    `ugjcs.api.schemas.ReviewOut`, which is built only from an editor-gated route.
    """

    manuscript_id: ManuscriptId
    reviewer_id: UserId
    status: str
    recommendation: str | None
    originality_score: int | None
    rigour_score: int | None
    clarity_score: int | None
    significance_score: int | None
    comments_to_author: str | None
    confidential_comments_to_editor: str | None
    assigned_at: datetime
    submitted_at: datetime | None


class ReviewAssignmentRepository(Protocol):
    async def assign(
        self, manuscript_id: ManuscriptId, reviewer_id: UserId, *, occurred_at: datetime
    ) -> None:
        """Record that a reviewer was asked. Idempotent is not guaranteed — a second call
        for the same pair raises, because `uq_review_assignments_pair` exists precisely
        to make a duplicate assignment visible rather than silently accepted."""
        ...

    async def list_for_reviewer(self, reviewer_id: UserId) -> list[ReviewAssignmentRecord]: ...

    async def list_for_manuscript(
        self, manuscript_id: ManuscriptId
    ) -> list[ReviewAssignmentRecord]: ...

    async def mark_submitted(
        self,
        manuscript_id: ManuscriptId,
        reviewer_id: UserId,
        *,
        recommendation: str,
        originality_score: int,
        rigour_score: int,
        clarity_score: int,
        significance_score: int,
        comments_to_author: str,
        confidential_comments_to_editor: str,
        occurred_at: datetime,
    ) -> None: ...


class UnitOfWork(Protocol):
    """A transactional boundary. Exiting without `commit` rolls back."""

    manuscripts: ManuscriptRepository
    accounts: AccountRepository
    refresh_tokens: RefreshTokenRepository
    assignments: ReviewAssignmentRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class Clock(Protocol):
    """Time as a dependency, so expiry logic is testable without sleeping."""

    def now(self) -> datetime: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Constant-time where the algorithm allows. Returns False; never raises on mismatch."""
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        """True when the hash was produced with weaker parameters than current policy."""
        ...


class TokenService(Protocol):
    def issue_access(self, subject: UserId) -> str: ...

    def read_access(self, token: str) -> UserId:
        """Return the subject, or raise `InvalidTokenError` if absent, expired or tampered with."""
        ...

    def issue_refresh(self, subject: UserId, family_id: UUID) -> tuple[str, str]:
        """Return `(token, token_hash)`. Only the hash is ever stored."""
        ...

    def hash_refresh(self, token: str) -> str: ...

    def issue_verification(self, subject: UserId) -> str: ...

    def read_verification(self, token: str) -> UserId:
        """Return the subject, or raise `InvalidTokenError` if absent, expired, replayed-typed,
        or of the wrong `typ`."""
        ...

    @property
    def refresh_ttl(self) -> timedelta:
        """How long a freshly issued refresh token is valid, for computing its DB expiry."""
        ...


class EmailSender(Protocol):
    async def send_verification(self, to: str, link: str) -> None: ...


class DocumentStore(Protocol):
    """Object storage for manuscript documents.

    Deliberately ignorant of "original" vs "anonymised": that distinction lives entirely
    in the key an `application`-layer caller chooses (see `application.documents`), so
    this port stays a plain key/bytes store an adapter can satisfy without knowing
    anything about manuscripts. The S3 adapter lives in `infrastructure.storage`; this
    layer must never import `boto3` itself.
    """

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        """Write `data` under `key`, replacing whatever was there before."""
        ...

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        """A short-lived, time-limited URL a client can fetch `key` from directly.

        The bucket itself blocks all public access; a pre-signed URL is the only way
        any document ever reaches a browser, and it is never proxied through this API.
        """
        ...
