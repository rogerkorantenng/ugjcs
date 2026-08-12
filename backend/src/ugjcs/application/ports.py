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
