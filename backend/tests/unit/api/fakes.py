"""In-memory fakes for API-layer unit tests.

These stand in for the query surface of `ManuscriptRepository` and `UnitOfWork` so that
routes wire correctly without a database. Correctness of the real adapters is proven
against a live Postgres in `tests/integration`; this package tests routing, authorisation
and serialisation only.

`FakeIdentityService` and any other authentication fake are deliberately not defined
here: `ugjcs.application.identity.SessionService` does not exist in this worktree yet
(Plan 3 is being written concurrently in another worktree), and this task's scope
excludes anything that authenticates a caller or produces an `Actor`. Add those fakes
back here when the auth router's task resumes after the merge.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.domain.manuscript import Manuscript


@dataclass
class FakeAccount:
    id: UserId
    email: str
    roles: frozenset[Role]
    full_name: str = "Test Author"
    is_active: bool = True
    is_verified: bool = True


@dataclass
class FakeAccountRepository:
    accounts: dict[UserId, FakeAccount] = field(default_factory=dict)

    async def get(self, user_id: UserId) -> FakeAccount | None:
        return self.accounts.get(user_id)


@dataclass
class FakeManuscriptRepository:
    """Enough of `ManuscriptRepository` for router tests: an in-memory dict, no chain."""

    store: dict[ManuscriptId, Manuscript] = field(default_factory=dict)

    async def add(self, manuscript: Manuscript) -> None:
        self.store[manuscript.id] = manuscript
        manuscript.pull_events()

    async def get(self, manuscript_id: ManuscriptId) -> Manuscript | None:
        return self.store.get(manuscript_id)

    async def get_by_tracking_code(self, code: object) -> Manuscript | None:
        value = getattr(code, "value", code)
        return next((m for m in self.store.values() if m.tracking_code.value == value), None)

    async def save(self, manuscript: Manuscript) -> None:
        self.store[manuscript.id] = manuscript
        manuscript.pull_events()

    async def chain_for(self, manuscript_id: ManuscriptId) -> list[object]:
        return []

    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        return [m for m in self.store.values() if author_id in m.author_ids]

    async def list_by_status(self, status: S) -> list[Manuscript]:
        return [m for m in self.store.values() if m.status == status]

    async def list_published(self) -> list[Manuscript]:
        return [m for m in self.store.values() if m.status is S.PUBLISHED]

    async def search_published(self, query: str) -> list[Manuscript]:
        published = await self.list_published()
        needle = query.lower()
        return [m for m in published if needle in m.title.lower() or needle in m.abstract.lower()]


@dataclass
class FakeUnitOfWork:
    manuscripts: FakeManuscriptRepository = field(default_factory=FakeManuscriptRepository)
    accounts: FakeAccountRepository = field(default_factory=FakeAccountRepository)

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def new_user_id() -> UserId:
    return UserId(uuid4())
