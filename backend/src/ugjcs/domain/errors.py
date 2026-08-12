"""Domain-level exceptions.

These carry no HTTP or framework semantics; adapters translate them at the boundary.
"""


class DomainError(Exception):
    """Base class for every domain rule violation."""


class IllegalTransition(DomainError):
    """A manuscript state transition that the lifecycle does not permit."""


class GuardViolation(DomainError):
    """A transition is structurally legal but its precondition is unmet."""


class AuthorizationDenied(DomainError):
    """The actor may not perform this action on this resource."""
