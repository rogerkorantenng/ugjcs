"""In-memory fakes for API-layer unit tests.

These stand in for the query surface of `ManuscriptRepository`, `UnitOfWork`,
`IdentityService` and `SessionService` so that routes wire correctly without a database
or a real token/hasher stack. Correctness of the real adapters is proven against a live
Postgres in `tests/integration`; this package tests routing, authorisation and
serialisation only.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

from pypdf import PdfWriter

from ugjcs.application.identity import AuthenticationError
from ugjcs.application.ports import REVIEW_PERIOD, ReviewAssignmentRecord
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.enums import Role
from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.hashchain import append as chain_append
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

# Defined before the fakes that use it as a dataclass field default (`FakeReviewContent`),
# which is evaluated at class-definition time, not lazily.
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


@dataclass
class FakeAccount:
    id: UserId
    email: str
    roles: frozenset[Role]
    full_name: str = "Test Author"
    affiliation: str = "Test University"
    expertise: tuple[str, ...] = ()
    reviewer_capacity: int = 3
    is_active: bool = True
    is_verified: bool = True


@dataclass
class FakeAccountRepository:
    accounts: dict[UserId, FakeAccount] = field(default_factory=dict)

    async def get(self, user_id: UserId) -> FakeAccount | None:
        return self.accounts.get(user_id)

    async def get_by_email(self, email: object) -> FakeAccount | None:
        value = getattr(email, "value", email)
        return next(
            (a for a in self.accounts.values() if getattr(a.email, "value", a.email) == value),
            None,
        )

    async def add(self, account: object) -> None:
        self.accounts[account.id] = account  # type: ignore[index,assignment]

    async def save(self, account: object) -> None:
        self.accounts[account.id] = account  # type: ignore[index,assignment]

    async def list_by_role(self, role: Role) -> list[FakeAccount]:
        return [
            a for a in self.accounts.values() if role in a.roles and a.is_active and a.is_verified
        ]


class FakeIdentityService:
    """`actor_for` looks a token up as if it were a validated access token's subject.

    The token is literally the account id, as text — enough to prove routing and
    authorisation without a real `JwtTokenService`.
    """

    def __init__(self, accounts: dict[UserId, FakeAccount]) -> None:
        self._accounts = accounts

    async def actor_for(self, access_token: str) -> Actor:
        try:
            subject = UserId(UUID(access_token))
        except ValueError as error:
            raise AuthenticationError("token is not valid") from error
        account = self._accounts.get(subject)
        if account is None or not account.is_active or not account.is_verified:
            raise AuthenticationError("no usable account for this credential")
        return Actor(id=account.id, roles=account.roles)


@dataclass(frozen=True, slots=True)
class FakeTokenPair:
    access_token: str
    refresh_token: str


class FakeSessionService:
    """Stands in for `SessionService`: one fixed account, one live refresh token.

    `log_in` is deliberately timing-shaped like the real thing is documented to be —
    both an unknown email and a wrong password raise the identical `AuthenticationError`
    message, so a test asserting the two responses are indistinguishable proves
    something about the router, not about this fake.
    """

    def __init__(self, *, email: str, password: str, account_id: UserId) -> None:
        self._email = email
        self._password = password
        self.account_id = account_id
        self._live_refresh = "refresh-token-abc"

    async def log_in(self, email: str, password: str) -> FakeTokenPair:
        if email != self._email or password != self._password:
            raise AuthenticationError("email or password is incorrect")
        return FakeTokenPair(access_token=str(self.account_id), refresh_token=self._live_refresh)

    async def refresh(self, refresh_token: str) -> FakeTokenPair:
        if refresh_token != self._live_refresh:
            raise AuthenticationError("refresh token is not valid")
        self._live_refresh = "refresh-token-rotated"
        return FakeTokenPair(access_token=str(self.account_id), refresh_token=self._live_refresh)

    async def log_out(self, refresh_token: str) -> None:
        self._live_refresh = ""


@dataclass
class FakeManuscriptRepository:
    """Enough of `ManuscriptRepository` for router tests: an in-memory dict, plus a real
    hash chain per manuscript so the analytics route (which reads event timestamps
    through `chain_for`) has genuine history to aggregate. The chain is built with the
    same `hashchain.append` the real repository uses — cheaper than a parallel fake
    event format, and it keeps sequence rules honest.

    A manuscript placed straight into `store` (as most tests do) has its buffered events
    still on the aggregate; they are drained into the chain only when a route later
    calls `save`, mirroring the real repository's flush-on-save. A test that needs the
    history present *before* any route runs should call `ingest` instead of writing to
    `store` directly.
    """

    store: dict[ManuscriptId, Manuscript] = field(default_factory=dict)
    chains: dict[ManuscriptId, list[ChainedEvent]] = field(default_factory=dict)

    def ingest(self, manuscript: Manuscript) -> None:
        """Store the manuscript and link its pending events onto its chain, the way a
        real `add`/`save` round-trip would have."""
        self.store[manuscript.id] = manuscript
        chain = self.chains.setdefault(manuscript.id, [])
        for event in manuscript.pull_events():
            chain.append(chain_append(chain, event))

    async def add(self, manuscript: Manuscript) -> None:
        self.ingest(manuscript)

    async def get(self, manuscript_id: ManuscriptId) -> Manuscript | None:
        return self.store.get(manuscript_id)

    async def get_by_tracking_code(self, code: object) -> Manuscript | None:
        value = getattr(code, "value", code)
        return next((m for m in self.store.values() if m.tracking_code.value == value), None)

    async def save(self, manuscript: Manuscript) -> None:
        self.ingest(manuscript)

    async def chain_for(self, manuscript_id: ManuscriptId) -> list[ChainedEvent]:
        return self.chains.get(manuscript_id, [])

    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        return [m for m in self.store.values() if author_id in m.author_ids]

    async def list_by_status(self, status: S) -> list[Manuscript]:
        return [m for m in self.store.values() if m.status == status]

    async def list_by_statuses(self, statuses: frozenset[S]) -> list[Manuscript]:
        return [m for m in self.store.values() if m.status in statuses]

    async def list_published(self) -> list[Manuscript]:
        return [m for m in self.store.values() if m.status is S.PUBLISHED]

    async def search_published(self, query: str) -> list[Manuscript]:
        published = await self.list_published()
        needle = query.lower()
        return [m for m in published if needle in m.title.lower() or needle in m.abstract.lower()]


@dataclass
class FakeAssignmentRepository:
    """Enough of `ReviewAssignmentRepository` for router tests: two in-memory collections.

    `assignments` mirrors the (manuscript_id, reviewer_id) pairs a real `assign()` call
    would insert; `submitted` records what a `mark_submitted()` call attached. Both are
    kept separate from `FakeManuscriptRepository`, matching the real schema's split
    between the `manuscripts` and `review_assignments` tables.
    """

    assignments: list[tuple[ManuscriptId, UserId]] = field(default_factory=list)
    submitted: dict[tuple[ManuscriptId, UserId], "FakeReviewContent"] = field(default_factory=dict)
    # Deadlines keyed per pair so a test can plant a past `due_at` (to exercise the
    # overdue flag) without touching every other assignment. Pairs appended straight to
    # `assignments` — the shortcut existing tests take — fall back to `NOW + REVIEW_PERIOD`
    # in `_record`, mirroring what the real adapter stamps at assignment time.
    due_dates: dict[tuple[ManuscriptId, UserId], datetime | None] = field(default_factory=dict)

    async def assign(
        self, manuscript_id: ManuscriptId, reviewer_id: UserId, *, occurred_at: datetime
    ) -> None:
        self.assignments.append((manuscript_id, reviewer_id))
        self.due_dates[(manuscript_id, reviewer_id)] = occurred_at + REVIEW_PERIOD

    async def list_for_reviewer(self, reviewer_id: UserId) -> list[ReviewAssignmentRecord]:
        return [
            self._record(manuscript_id, reviewer)
            for manuscript_id, reviewer in self.assignments
            if reviewer == reviewer_id
        ]

    async def list_for_manuscript(
        self, manuscript_id: ManuscriptId
    ) -> list[ReviewAssignmentRecord]:
        return [
            self._record(manuscript, reviewer)
            for manuscript, reviewer in self.assignments
            if manuscript == manuscript_id
        ]

    async def list_all(self) -> list[ReviewAssignmentRecord]:
        return [self._record(manuscript, reviewer) for manuscript, reviewer in self.assignments]

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
    ) -> None:
        self.submitted[(manuscript_id, reviewer_id)] = FakeReviewContent(
            recommendation=recommendation,
            originality_score=originality_score,
            rigour_score=rigour_score,
            clarity_score=clarity_score,
            significance_score=significance_score,
            comments_to_author=comments_to_author,
            confidential_comments_to_editor=confidential_comments_to_editor,
            submitted_at=occurred_at,
        )

    def _record(self, manuscript_id: ManuscriptId, reviewer_id: UserId) -> ReviewAssignmentRecord:
        pair = (manuscript_id, reviewer_id)
        content = self.submitted.get(pair)
        return ReviewAssignmentRecord(
            manuscript_id=manuscript_id,
            reviewer_id=reviewer_id,
            status="submitted" if content is not None else "assigned",
            recommendation=content.recommendation if content is not None else None,
            originality_score=content.originality_score if content is not None else None,
            rigour_score=content.rigour_score if content is not None else None,
            clarity_score=content.clarity_score if content is not None else None,
            significance_score=content.significance_score if content is not None else None,
            comments_to_author=content.comments_to_author if content is not None else None,
            confidential_comments_to_editor=(
                content.confidential_comments_to_editor if content is not None else None
            ),
            assigned_at=NOW,
            due_at=self.due_dates.get(pair, NOW + REVIEW_PERIOD),
            submitted_at=content.submitted_at if content is not None else None,
        )


@dataclass(frozen=True, slots=True)
class FakeReviewContent:
    """What `mark_submitted` recorded for one (manuscript, reviewer) pair — grouped so
    `FakeAssignmentRepository.submitted` doesn't carry a seven-element tuple positionally.

    `submitted_at` carries the `occurred_at` the caller passed, defaulting to `NOW`, so a
    performance test can plant a submission time later than `assigned_at` and get a
    non-zero turnaround."""

    recommendation: str
    originality_score: int
    rigour_score: int
    clarity_score: int
    significance_score: int
    comments_to_author: str
    confidential_comments_to_editor: str
    submitted_at: datetime = NOW


@dataclass
class FakeDocumentStore:
    """Records what would have been written to S3, and hands back a fake URL that
    encodes the key so a test can assert which object a route resolved to."""

    objects: dict[str, bytes] = field(default_factory=dict)

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self.objects[key] = data

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        return f"https://fake-s3.test/{key}?ttl={int(expires_in.total_seconds())}"


@dataclass
class FakeUnitOfWork:
    manuscripts: FakeManuscriptRepository = field(default_factory=FakeManuscriptRepository)
    accounts: FakeAccountRepository = field(default_factory=FakeAccountRepository)
    assignments: FakeAssignmentRepository = field(default_factory=FakeAssignmentRepository)

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def new_user_id() -> UserId:
    return UserId(uuid4())


def minimal_pdf_bytes() -> bytes:
    """A genuinely parseable one-page PDF carrying an author name in its DocInfo, not
    merely four magic bytes: the anonymiser route calls `pypdf.PdfReader` on whatever a
    test uploads, and the identifying metadata is what proves stripping actually ran."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Author": "Sentinel Author Name", "/Title": "Sentinel Title"})
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
