"""Turning a credential into an `Actor` the authorisation layer can trust.

`policies.can()` trusts `Actor.roles` completely. That trust has to be earned somewhere,
and this is the only place it is: roles are read from the database on every request, never
taken from the token. The cost is one indexed query; the benefit is that revoking a role
binds immediately instead of whenever the holder's token happens to expire.
"""

from ugjcs.application.ports import AccountRepository, TokenService
from ugjcs.domain.errors import DomainError
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
