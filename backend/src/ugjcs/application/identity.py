"""Turning a credential into an `Actor` the authorisation layer can trust.

`policies.can()` trusts `Actor.roles` completely. That trust has to be earned somewhere,
and this is the only place it is: roles are read from the database on every request, never
taken from the token. The cost is one indexed query; the benefit is that revoking a role
binds immediately instead of whenever the holder's token happens to expire.
"""

import secrets
from dataclasses import dataclass
from uuid import UUID, uuid4

from ugjcs.application.ports import (
    AccountRepository,
    Clock,
    EmailSender,
    PasswordHasher,
    RefreshTokenRecord,
    RefreshTokenRepository,
    TokenService,
)
from ugjcs.domain.account import Account, AccountError, EmailAddress
from ugjcs.domain.errors import DomainError
from ugjcs.domain.ids import UserId
from ugjcs.domain.policies import Actor


class AuthenticationError(DomainError):
    """The credential is valid in form but does not identify a usable account."""


class IdentityService:
    def __init__(self, accounts: AccountRepository, tokens: TokenService) -> None:
        self._accounts = accounts
        self._tokens = tokens

    async def actor_for(self, access_token: str) -> Actor:
        subject = self._tokens.read_access(access_token)
        account = await self._accounts.get(subject)
        if account is None:
            raise AuthenticationError("no account for this credential")
        if not account.may_authenticate():
            raise AuthenticationError("account is not permitted to authenticate")
        return Actor(id=account.id, roles=account.roles)


MIN_PASSWORD_LENGTH = 12
"""NIST SP 800-63B: length predicts resistance to guessing better than composition rules
ever did. Deliberately no uppercase/digit/symbol requirement is imposed here."""

VERIFICATION_LINK_BASE = "https://ugjcs.example.edu/verify?token"


class RegistrationService:
    def __init__(
        self,
        accounts: AccountRepository,
        tokens: TokenService,
        hasher: PasswordHasher,
        emails: EmailSender,
        clock: Clock,
    ) -> None:
        self._accounts = accounts
        self._tokens = tokens
        self._hasher = hasher
        self._emails = emails
        self._clock = clock

    async def register(
        self, *, email: str, password: str, full_name: str, affiliation: str
    ) -> Account:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AccountError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
        normalised = EmailAddress(email)
        if await self._accounts.get_by_email(normalised) is not None:
            raise AccountError(f"an account already exists for {normalised.value}")
        account = Account(
            id=UserId(uuid4()),
            email=normalised,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
            affiliation=affiliation,
        )
        await self._accounts.add(account)
        token = self._tokens.issue_verification(account.id)
        await self._emails.send_verification(normalised.value, f"{VERIFICATION_LINK_BASE}={token}")
        return account

    async def verify(self, token: str) -> None:
        subject = self._tokens.read_verification(token)
        account = await self._accounts.get(subject)
        if account is None:
            raise AuthenticationError("no account for this verification link")
        account.verify(occurred_at=self._clock.now())
        await self._accounts.save(account)


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


class SessionService:
    """Login and refresh-token lifecycle: issue, rotate, and detect reuse.

    Refresh rotation with reuse detection: each successful `refresh` issues a new token in
    the same family and marks the presented row `revoked_at` with `replaced_by` pointing at
    the new row's id. If a *revoked* row is presented again, that is either the legitimate
    holder retrying a request whose response was lost, or an attacker replaying a token they
    stole — the two cannot be told apart from here, so the entire family is revoked. Ending
    both sessions is the safe failure; leaving either one open is not.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        refresh_tokens: RefreshTokenRepository,
        tokens: TokenService,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._accounts = accounts
        self._refresh_tokens = refresh_tokens
        self._tokens = tokens
        self._hasher = hasher
        self._clock = clock
        # Hashed once per service instance, not per call, so an unregistered email still
        # pays the full Argon2 cost on every login attempt — the wall-clock gap between
        # "no such account" and "wrong password" is exactly what would let a caller
        # enumerate registered addresses.
        self._dummy_hash = hasher.hash(secrets.token_urlsafe(32))

    async def log_in(self, email: str, password: str) -> TokenPair:
        account = await self._accounts.get_by_email(EmailAddress(email))
        if account is None:
            self._hasher.verify(password, self._dummy_hash)
            raise AuthenticationError("email or password is incorrect")
        if not self._hasher.verify(password, account.password_hash):
            raise AuthenticationError("email or password is incorrect")
        if not account.may_authenticate():
            raise AuthenticationError("account is not permitted to authenticate")
        if self._hasher.needs_rehash(account.password_hash):
            account.password_hash = self._hasher.hash(password)
            await self._accounts.save(account)
        pair, _ = await self._issue_pair(account.id, family_id=uuid4())
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        token_hash = self._tokens.hash_refresh(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        if record is None:
            raise AuthenticationError("refresh token is not recognised")
        if record.revoked_at is not None:
            await self._refresh_tokens.revoke_family(record.family_id)
            raise AuthenticationError("refresh token has already been used")
        if record.expires_at <= self._clock.now():
            raise AuthenticationError("refresh token has expired")
        pair, new_id = await self._issue_pair(record.user_id, family_id=record.family_id)
        await self._refresh_tokens.revoke(record.id, replaced_by=new_id)
        return pair

    async def log_out(self, refresh_token: str) -> None:
        token_hash = self._tokens.hash_refresh(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        if record is not None:
            await self._refresh_tokens.revoke_family(record.family_id)

    async def _issue_pair(self, user_id: UserId, *, family_id: UUID) -> tuple[TokenPair, UUID]:
        access = self._tokens.issue_access(user_id)
        refresh, refresh_hash = self._tokens.issue_refresh(user_id, family_id)
        issued = self._clock.now()
        record_id = uuid4()
        await self._refresh_tokens.add(
            RefreshTokenRecord(
                id=record_id,
                user_id=user_id,
                family_id=family_id,
                token_hash=refresh_hash,
                issued_at=issued,
                expires_at=issued + self._tokens.refresh_ttl,
                revoked_at=None,
                replaced_by=None,
            )
        )
        return TokenPair(access_token=access, refresh_token=refresh), record_id
