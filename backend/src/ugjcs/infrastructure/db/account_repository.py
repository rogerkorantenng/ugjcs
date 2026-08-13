"""PostgreSQL implementation of the account repository port."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.mappers import account_to_row, row_to_account
from ugjcs.infrastructure.db.models import UserRoleRow, UserRow


class SqlAlchemyAccountRepository:
    """Persists the account aggregate and keeps its role rows in sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: Account) -> None:
        self._session.add(account_to_row(account))

    async def get(self, user_id: UserId) -> Account | None:
        row = await self._session.get(UserRow, user_id)
        return row_to_account(row) if row is not None else None

    async def get_by_email(self, email: EmailAddress) -> Account | None:
        result = await self._session.execute(select(UserRow).where(UserRow.email == email.value))
        row = result.scalar_one_or_none()
        return row_to_account(row) if row is not None else None

    async def save(self, account: Account) -> None:
        row = await self._session.get(UserRow, account.id)
        if row is None:
            raise LookupError(f"account {account.id} has never been persisted")
        row.email = account.email.value
        row.password_hash = account.password_hash
        row.full_name = account.full_name
        row.affiliation = account.affiliation
        row.expertise = list(account.expertise)
        row.reviewer_capacity = account.reviewer_capacity
        row.is_verified = account.is_verified
        row.is_active = account.is_active
        row.verified_at = account.verified_at
        held = {existing.role for existing in row.roles}
        wanted = {role.value for role in account.roles}
        for existing in list(row.roles):
            if existing.role not in wanted:
                row.roles.remove(existing)
        for role in wanted - held:
            row.roles.append(UserRoleRow(user_id=account.id, role=role))

    async def list_by_role(self, role: Role) -> list[Account]:
        result = await self._session.execute(
            select(UserRow)
            .join(UserRoleRow, UserRoleRow.user_id == UserRow.id)
            .where(
                UserRoleRow.role == role.value,
                UserRow.is_verified.is_(True),
                UserRow.is_active.is_(True),
            )
        )
        return [row_to_account(row) for row in result.scalars()]
