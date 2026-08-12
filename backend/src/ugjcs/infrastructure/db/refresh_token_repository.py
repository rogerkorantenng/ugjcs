"""PostgreSQL implementation of the refresh token repository port."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import RefreshTokenRecord
from ugjcs.infrastructure.db.mappers import refresh_token_to_row, row_to_refresh_token
from ugjcs.infrastructure.db.models import RefreshTokenRow


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RefreshTokenRecord) -> None:
        self._session.add(refresh_token_to_row(record))

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        result = await self._session.execute(
            select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return row_to_refresh_token(row) if row is not None else None

    async def revoke(self, token_id: UUID, *, replaced_by: UUID | None = None) -> None:
        row = await self._session.get(RefreshTokenRow, token_id)
        if row is None:
            raise LookupError(f"refresh token {token_id} has never been persisted")
        row.revoked_at = datetime.now(UTC)
        row.replaced_by = replaced_by

    async def revoke_family(self, family_id: UUID) -> None:
        result = await self._session.execute(
            select(RefreshTokenRow).where(
                RefreshTokenRow.family_id == family_id, RefreshTokenRow.revoked_at.is_(None)
            )
        )
        now = datetime.now(UTC)
        for row in result.scalars():
            row.revoked_at = now
