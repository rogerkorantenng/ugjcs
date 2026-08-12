"""Ports the application layer depends on.

These are protocols, not base classes. Infrastructure supplies implementations; the
application layer never imports them, which is what the layers contract enforces.
"""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from ugjcs.domain.account import Account, EmailAddress
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


class UnitOfWork(Protocol):
    """A transactional boundary. Exiting without `commit` rolls back."""

    manuscripts: ManuscriptRepository
    accounts: AccountRepository

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


class EmailSender(Protocol):
    async def send_verification(self, to: str, link: str) -> None: ...
