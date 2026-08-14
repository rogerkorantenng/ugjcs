"""Unit tests for registration and verification, entirely in memory."""

from datetime import UTC, datetime, timedelta

import pytest

from ugjcs.application.identity import RegistrationService
from ugjcs.domain.account import Account, AccountError, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import InvalidTokenError, JwtTokenService

# Anchored to the real clock rather than a hardcoded moment, and deliberately so.
# `JwtTokenService` mints `exp` from the clock injected into it, but PyJWT validates that
# claim against the *system* clock when the token is decoded. A fixed date therefore makes
# every verification test a time bomb: it passes until the wall clock drifts past the
# verification window, then fails for a reason that has nothing to do with the code under
# test. This one detonated on 2026-08-14, two days after the date it was pinned to.
# Reading the clock once here keeps the determinism the frozen fake exists to provide,
# since every clock in a given run still returns the same instant.
NOW = datetime.now(UTC)
PASSWORD = "correct horse battery staple"


class DictAccountRepository:
    """A dict-backed fake satisfying the `AccountRepository` protocol."""

    def __init__(self) -> None:
        self._by_id: dict[UserId, Account] = {}

    async def add(self, account: Account) -> None:
        self._by_id[account.id] = account

    async def get(self, user_id: UserId) -> Account | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: EmailAddress) -> Account | None:
        return next((a for a in self._by_id.values() if a.email.value == email.value), None)

    async def save(self, account: Account) -> None:
        if account.id not in self._by_id:
            raise LookupError(f"account {account.id} has never been persisted")
        self._by_id[account.id] = account

    async def list_by_role(self, role: Role) -> list[Account]:
        return [
            a for a in self._by_id.values() if role in a.roles and a.is_verified and a.is_active
        ]

    async def list_all(self) -> list[Account]:
        return sorted(self._by_id.values(), key=lambda a: a.email.value)


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_verification(self, to: str, link: str) -> None:
        self.sent.append((to, link))


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class CountingHasher:
    """Spies on `hash` calls so "no hashing occurred" can be asserted directly."""

    def __init__(self) -> None:
        self._inner = Argon2PasswordHasher()
        self.hash_calls = 0

    def hash(self, password: str) -> str:
        self.hash_calls += 1
        return self._inner.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._inner.verify(password, password_hash)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._inner.needs_rehash(password_hash)


def make_service(
    accounts: DictAccountRepository | None = None,
    emails: FakeEmailSender | None = None,
    hasher: Argon2PasswordHasher | CountingHasher | None = None,
) -> tuple[RegistrationService, DictAccountRepository, FakeEmailSender]:
    accounts = accounts or DictAccountRepository()
    emails = emails or FakeEmailSender()
    tokens = JwtTokenService(
        secret="test-secret-not-used-anywhere-real",
        clock=FrozenClock(NOW),
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )
    service = RegistrationService(
        accounts, tokens, hasher or Argon2PasswordHasher(), emails, FrozenClock(NOW)
    )
    return service, accounts, emails


async def test_registering_creates_an_unverified_account_and_sends_one_message() -> None:
    service, _accounts, emails = make_service()
    account = await service.register(
        email="r.obeng@ug.edu.gh",
        password=PASSWORD,
        full_name="Roger Koranteng Obeng",
        affiliation="University of Ghana",
    )
    assert not account.is_verified
    assert len(emails.sent) == 1
    assert emails.sent[0][0] == "r.obeng@ug.edu.gh"


async def test_the_stored_password_hash_is_not_the_plaintext_password() -> None:
    service, _accounts, _ = make_service()
    account = await service.register(
        email="hash@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    assert account.password_hash != PASSWORD


async def test_registering_an_existing_email_raises_and_sends_no_second_message() -> None:
    service, _accounts, emails = make_service()
    await service.register(
        email="dup@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    with pytest.raises(AccountError, match="already exists"):
        await service.register(
            email="dup@ug.edu.gh", password=PASSWORD, full_name="B", affiliation="UG"
        )
    assert len(emails.sent) == 1


async def test_registering_an_email_differing_only_in_case_is_a_duplicate() -> None:
    service, _accounts, emails = make_service()
    await service.register(
        email="Case@UG.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    with pytest.raises(AccountError, match="already exists"):
        await service.register(
            email="case@ug.edu.gh", password=PASSWORD, full_name="B", affiliation="UG"
        )
    assert len(emails.sent) == 1


async def test_a_valid_verification_token_verifies_the_account() -> None:
    service, accounts, emails = make_service()
    account = await service.register(
        email="verify@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    link = emails.sent[0][1]
    token = link.rsplit("=", 1)[-1]

    await service.verify(token)

    stored = await accounts.get(account.id)
    assert stored is not None
    assert stored.is_verified


async def test_a_verification_token_cannot_be_replayed() -> None:
    service, _accounts, emails = make_service()
    await service.register(
        email="replay@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    token = emails.sent[0][1].rsplit("=", 1)[-1]
    await service.verify(token)

    with pytest.raises(AccountError, match="already verified"):
        await service.verify(token)


async def test_an_unknown_verification_token_raises() -> None:
    service, _, _ = make_service()
    with pytest.raises(InvalidTokenError):
        await service.verify("not-a-real-token")


async def test_a_short_password_is_refused_before_any_hashing_occurs() -> None:
    hasher = CountingHasher()
    service, accounts, emails = make_service(hasher=hasher)
    with pytest.raises(AccountError, match="at least 12"):
        await service.register(
            email="short@ug.edu.gh", password="short", full_name="A", affiliation="UG"
        )
    assert hasher.hash_calls == 0
    assert await accounts.get_by_email(EmailAddress("short@ug.edu.gh")) is None
    assert emails.sent == []
