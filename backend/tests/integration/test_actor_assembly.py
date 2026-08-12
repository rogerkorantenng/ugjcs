"""Integration tests proving roles are read fresh, not carried by the token.

Discharges Plan 1's Task 8 review finding: `Actor.roles` must be authentic AND current.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.identity import AuthenticationError, IdentityService
from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository
from ugjcs.infrastructure.security.tokens import InvalidTokenError, JwtTokenService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


def make_account(**overrides: object) -> Account:
    defaults: dict[str, object] = {
        "id": UserId(uuid4()),
        "email": EmailAddress(f"{uuid4()}@ug.edu.gh"),
        "password_hash": "argon2-placeholder",
        "full_name": "Roger Koranteng Obeng",
        "affiliation": "University of Ghana",
    }
    return Account(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(NOW)


@pytest.fixture
def tokens(clock: FrozenClock) -> JwtTokenService:
    return JwtTokenService(
        secret="test-secret-not-used-anywhere-real",
        clock=clock,
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


@pytest.fixture
def repository(session: AsyncSession) -> SqlAlchemyAccountRepository:
    return SqlAlchemyAccountRepository(session)


@pytest.fixture
def identity(repository: SqlAlchemyAccountRepository, tokens: JwtTokenService) -> IdentityService:
    return IdentityService(repository, tokens)


async def verified_account_with(
    session: AsyncSession, repository: SqlAlchemyAccountRepository, *roles: Role
) -> Account:
    account = make_account()
    account.verify(occurred_at=NOW)
    for role in roles:
        account.grant(role)
    await repository.add(account)
    await session.commit()
    return account


async def test_roles_revoked_after_a_token_was_issued_take_effect_immediately(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    """The finding from Plan 1's Task 8 review, answered.

    A role encoded in the token would remain valid until the token expired. Reading roles
    from the database per request means an administrator's revocation binds on the very
    next call. A broken implementation that reads roles from the token, or caches the
    first lookup, would return EDITOR on the second assertion below — it must not.
    """
    account = await verified_account_with(session, repository, Role.EDITOR)
    token = tokens.issue_access(account.id)
    assert Role.EDITOR in (await identity.actor_for(token)).roles

    account.revoke(Role.EDITOR)
    await repository.save(account)
    await session.commit()

    assert Role.EDITOR not in (await identity.actor_for(token)).roles


async def test_roles_granted_after_a_token_was_issued_take_effect_immediately(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = await verified_account_with(session, repository)
    token = tokens.issue_access(account.id)
    assert Role.REVIEWER not in (await identity.actor_for(token)).roles

    account.grant(Role.REVIEWER)
    await repository.save(account)
    await session.commit()

    assert Role.REVIEWER in (await identity.actor_for(token)).roles


async def test_a_token_for_a_deleted_account_is_refused(
    identity: IdentityService, tokens: JwtTokenService
) -> None:
    token = tokens.issue_access(UserId(uuid4()))
    with pytest.raises(AuthenticationError, match="no account"):
        await identity.actor_for(token)


async def test_a_deactivated_account_is_refused(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = await verified_account_with(session, repository)
    account.deactivate()
    await repository.save(account)
    await session.commit()

    token = tokens.issue_access(account.id)
    with pytest.raises(AuthenticationError):
        await identity.actor_for(token)


async def test_an_unverified_account_is_refused(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = make_account()
    await repository.add(account)
    await session.commit()

    token = tokens.issue_access(account.id)
    with pytest.raises(AuthenticationError):
        await identity.actor_for(token)


async def test_an_expired_token_is_refused(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    """`InvalidTokenError`, not `AuthenticationError`: Step 2 makes `actor_for` let token
    errors propagate unwrapped, precisely so the API layer can tell "bad token" apart
    from "no such account". A test asserting `AuthenticationError` here would pass
    against an implementation that violated that contract, so it must not be written."""
    account = await verified_account_with(session, repository)
    token = tokens.issue_access(account.id)
    clock.moment += timedelta(minutes=16)

    with pytest.raises(InvalidTokenError, match="expired"):
        await identity.actor_for(token)


async def test_the_assembled_actor_id_equals_the_account_id(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = await verified_account_with(session, repository, Role.AUTHOR)
    token = tokens.issue_access(account.id)
    actor = await identity.actor_for(token)
    assert actor.id == account.id
