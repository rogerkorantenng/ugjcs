"""Turning a credential into an `Actor` the authorisation layer can trust.

`policies.can()` trusts `Actor.roles` completely. That trust has to be earned somewhere,
and this is the only place it is: roles are read from the database on every request, never
taken from the token. The cost is one indexed query; the benefit is that revoking a role
binds immediately instead of whenever the holder's token happens to expire.
"""

from uuid import uuid4

from ugjcs.application.ports import (
    AccountRepository,
    Clock,
    EmailSender,
    PasswordHasher,
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
