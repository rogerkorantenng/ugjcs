"""Integration tests for account persistence."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_account(**overrides: object) -> Account:
    defaults: dict[str, object] = {
        "id": UserId(uuid4()),
        "email": EmailAddress("R.Obeng@UG.edu.gh"),
        "password_hash": "argon2-placeholder",
        "full_name": "Roger Koranteng Obeng",
        "affiliation": "University of Ghana",
    }
    return Account(**(defaults | overrides))  # type: ignore[arg-type]


async def test_a_stored_account_reads_back_with_its_roles(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    account.grant(Role.REVIEWER)
    account.grant(Role.EDITOR)
    await repository.add(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.id == account.id
    assert loaded.roles == frozenset({Role.REVIEWER, Role.EDITOR})


async def test_lookup_by_email_is_case_insensitive(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account(email=EmailAddress("R.Obeng@UG.edu.gh"))
    await repository.add(account)
    await session.commit()

    loaded = await repository.get_by_email(EmailAddress("r.obeng@ug.edu.gh"))
    assert loaded is not None
    assert loaded.id == account.id


async def test_a_missing_account_reads_back_as_none(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    assert await repository.get(UserId(uuid4())) is None
    assert await repository.get_by_email(EmailAddress("nobody@ug.edu.gh")) is None


async def test_granting_a_role_and_saving_persists_it(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    await repository.add(account)
    await session.commit()

    account.grant(Role.AUTHOR)
    await repository.save(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.roles == frozenset({Role.AUTHOR})


async def test_revoking_a_role_and_saving_removes_it(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    account.grant(Role.AUTHOR)
    account.grant(Role.REVIEWER)
    await repository.add(account)
    await session.commit()

    account.revoke(Role.AUTHOR)
    await repository.save(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.roles == frozenset({Role.REVIEWER})


async def test_saving_persists_scalar_field_changes_too(session: AsyncSession) -> None:
    """Roles are not the only thing `save` must persist. An implementation that only
    rewrites the role table and forgets scalar columns would still pass every test above."""
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    await repository.add(account)
    await session.commit()

    account.verify(occurred_at=NOW)
    account.deactivate()
    await repository.save(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.is_verified
    assert loaded.verified_at == NOW
    assert not loaded.is_active


async def test_a_duplicate_email_raises_an_integrity_error(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    await repository.add(make_account(email=EmailAddress("dup@ug.edu.gh")))
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.add(make_account(id=UserId(uuid4()), email=EmailAddress("DUP@ug.edu.GH")))
        await session.commit()
