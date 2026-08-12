"""Integration tests for login, refresh rotation and reuse detection."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.identity import AuthenticationError, SessionService
from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository
from ugjcs.infrastructure.db.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import JwtTokenService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
PASSWORD = "correct horse battery staple"


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class CountingHasher:
    """Spies on `verify` calls. A wall-clock timing assertion would be flaky under CI
    load; this proves the same code path — a real Argon2 verify — runs for both a wrong
    password and an unregistered email, which is what makes the timing comparable."""

    def __init__(self) -> None:
        self._inner = Argon2PasswordHasher()
        self.verify_calls = 0

    def hash(self, password: str) -> str:
        return self._inner.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        self.verify_calls += 1
        return self._inner.verify(password, password_hash)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._inner.needs_rehash(password_hash)


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
def accounts(session: AsyncSession) -> SqlAlchemyAccountRepository:
    return SqlAlchemyAccountRepository(session)


@pytest.fixture
def refresh_tokens(session: AsyncSession) -> SqlAlchemyRefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


async def register_account(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    *,
    email: str = "r.obeng@ug.edu.gh",
    password: str = PASSWORD,
    verified: bool = True,
    active: bool = True,
    hasher: Argon2PasswordHasher | None = None,
) -> Account:
    account = Account(
        id=UserId(uuid4()),
        email=EmailAddress(email),
        password_hash=(hasher or Argon2PasswordHasher()).hash(password),
        full_name="Roger Koranteng Obeng",
        affiliation="University of Ghana",
    )
    if verified:
        account.verify(occurred_at=NOW)
    if not active:
        account.deactivate()
    await accounts.add(account)
    await session.commit()
    return account


def make_service(
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
    hasher: Argon2PasswordHasher | CountingHasher | None = None,
) -> SessionService:
    return SessionService(accounts, refresh_tokens, tokens, hasher or Argon2PasswordHasher(), clock)


async def test_correct_credentials_return_an_access_and_a_refresh_token(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    account = await register_account(session, accounts)
    service = make_service(accounts, refresh_tokens, tokens, clock)

    pair = await service.log_in(account.email.value, PASSWORD)

    assert pair.access_token
    assert pair.refresh_token
    assert tokens.read_access(pair.access_token) == account.id


async def test_an_unknown_email_fails_like_a_wrong_password(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts)
    hasher = CountingHasher()
    service = make_service(accounts, refresh_tokens, tokens, clock, hasher)

    with pytest.raises(AuthenticationError) as unknown_error:
        await service.log_in("nobody@ug.edu.gh", "whatever-password")
    assert hasher.verify_calls == 1

    with pytest.raises(AuthenticationError) as wrong_error:
        await service.log_in("r.obeng@ug.edu.gh", "not the right password")
    assert hasher.verify_calls == 2

    assert str(unknown_error.value) == str(wrong_error.value)


async def test_an_unverified_account_cannot_log_in(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="unverified@ug.edu.gh", verified=False)
    service = make_service(accounts, refresh_tokens, tokens, clock)

    with pytest.raises(AuthenticationError):
        await service.log_in("unverified@ug.edu.gh", PASSWORD)


async def test_a_deactivated_account_cannot_log_in(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="deactivated@ug.edu.gh", active=False)
    service = make_service(accounts, refresh_tokens, tokens, clock)

    with pytest.raises(AuthenticationError):
        await service.log_in("deactivated@ug.edu.gh", PASSWORD)


async def test_refreshing_returns_a_new_pair_and_the_old_token_stops_working(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    account = await register_account(session, accounts, email="rotate@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    first = await service.log_in("rotate@ug.edu.gh", PASSWORD)

    second = await service.refresh(first.refresh_token)

    assert second.refresh_token != first.refresh_token
    assert tokens.read_access(second.access_token) == account.id
    with pytest.raises(AuthenticationError):
        await service.refresh(first.refresh_token)


async def test_replaying_a_rotated_refresh_token_revokes_the_entire_family(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="reuse@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    first = await service.log_in("reuse@ug.edu.gh", PASSWORD)
    second = await service.refresh(first.refresh_token)

    # Replaying the spent token is theft-or-replay; the whole family dies, including the
    # newest, legitimately rotated token. An implementation that revoked only the
    # presented token would leave `second` usable — this is what that would miss.
    with pytest.raises(AuthenticationError):
        await service.refresh(first.refresh_token)

    with pytest.raises(AuthenticationError):
        await service.refresh(second.refresh_token)


async def test_an_expired_refresh_token_is_refused(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="expiring@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    pair = await service.log_in("expiring@ug.edu.gh", PASSWORD)

    clock.moment += timedelta(days=8)

    with pytest.raises(AuthenticationError, match="expired"):
        await service.refresh(pair.refresh_token)


async def test_logging_out_revokes_the_presented_tokens_family(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="logout@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    pair = await service.log_in("logout@ug.edu.gh", PASSWORD)

    await service.log_out(pair.refresh_token)

    with pytest.raises(AuthenticationError):
        await service.refresh(pair.refresh_token)


async def test_a_successful_login_upgrades_an_outdated_password_hash(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    weak_hasher = Argon2PasswordHasher(memory_cost=8, time_cost=1, parallelism=1)
    account = await register_account(session, accounts, email="weak@ug.edu.gh", hasher=weak_hasher)
    stored_before = account.password_hash
    service = make_service(accounts, refresh_tokens, tokens, clock)

    await service.log_in("weak@ug.edu.gh", PASSWORD)

    reloaded = await accounts.get(account.id)
    assert reloaded is not None
    assert reloaded.password_hash != stored_before
    assert Argon2PasswordHasher().verify(PASSWORD, reloaded.password_hash)
    assert not Argon2PasswordHasher().needs_rehash(reloaded.password_hash)
