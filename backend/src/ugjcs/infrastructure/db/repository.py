"""PostgreSQL implementation of the manuscript repository port."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.hashchain import ChainedEvent, append
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.mappers import (
    event_to_row,
    row_to_chained,
    to_domain,
    to_row,
)
from ugjcs.infrastructure.db.models import EditorialEventRow, ManuscriptAuthorRow, ManuscriptRow


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

    async def list_by_status(self, status: S) -> list[Manuscript]:
        result = await self._session.execute(
            select(ManuscriptRow)
            .where(ManuscriptRow.status == status.value)
            .order_by(ManuscriptRow.id)
        )
        rows = result.scalars().all()
        return [await self._rehydrate(row) for row in rows]  # type: ignore[misc]

    async def list_published(self) -> list[Manuscript]:
        return await self.list_by_status(S.PUBLISHED)

    async def search_published(self, query: str) -> list[Manuscript]:
        result = await self._session.execute(
            select(ManuscriptRow).where(
                ManuscriptRow.status == S.PUBLISHED.value,
                (ManuscriptRow.title.ilike(f"%{query}%"))
                | (ManuscriptRow.abstract.ilike(f"%{query}%")),
            )
        )
        rows = result.scalars().all()
        return [await self._rehydrate(row) for row in rows]  # type: ignore[misc]

    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        result = await self._session.execute(
            select(ManuscriptRow)
            .join(ManuscriptRow.authors)
            .where(ManuscriptAuthorRow.author_id == author_id)
            .order_by(ManuscriptRow.id)
        )
        rows = result.scalars().unique().all()
        return [await self._rehydrate(row) for row in rows]  # type: ignore[misc]

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
