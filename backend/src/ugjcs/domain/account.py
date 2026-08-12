"""The account aggregate: who someone is, and what they are allowed to be.

The password *hash* lives here; hashing itself does not. Choosing an algorithm is an
infrastructure concern, and keeping it out preserves the domain's freedom from libraries.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from ugjcs.domain.enums import Role
from ugjcs.domain.errors import DomainError
from ugjcs.domain.ids import UserId

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


class AccountError(DomainError):
    """An operation the account's current state does not permit."""


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """A normalised address. Case and surrounding whitespace never distinguish accounts."""

    value: str

    def __init__(self, raw: str) -> None:
        normalised = raw.strip().lower()
        if not _EMAIL_PATTERN.match(normalised):
            raise ValueError(f"not a valid email address: {raw!r}")
        object.__setattr__(self, "value", normalised)


@dataclass(slots=True)
class Account:
    id: UserId
    email: EmailAddress
    password_hash: str
    full_name: str
    affiliation: str
    expertise: tuple[str, ...] = ()
    reviewer_capacity: int = 3
    is_verified: bool = False
    is_active: bool = True
    verified_at: datetime | None = None
    _roles: set[Role] = field(default_factory=set, repr=False)

    @property
    def roles(self) -> frozenset[Role]:
        return frozenset(self._roles)

    def verify(self, *, occurred_at: datetime) -> None:
        if self.is_verified:
            raise AccountError("account is already verified")
        self.is_verified = True
        self.verified_at = occurred_at

    def grant(self, role: Role) -> None:
        """Idempotent: granting a held role is a no-op, not an error."""
        self._roles.add(role)

    def revoke(self, role: Role) -> None:
        if role not in self._roles:
            raise AccountError(f"account does not hold the {role.value} role")
        self._roles.discard(role)

    def deactivate(self) -> None:
        self.is_active = False

    def reactivate(self) -> None:
        self.is_active = True

    def may_authenticate(self) -> bool:
        """Both conditions are required; neither implies the other."""
        return self.is_verified and self.is_active
