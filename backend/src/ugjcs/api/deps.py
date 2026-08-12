"""Request-scoped dependencies: who is calling, and what they may do.

Every dependency that establishes identity or authorisation is decorated with `_mark`,
so `tests/unit/api/test_route_audit.py` can walk the route table mechanically and fail
loudly if a route was wired up without one — the one guarantee this API makes that must
never depend on a reviewer remembering to add `Depends(...)`.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends, Header

from ugjcs.api.wiring import get_identity_service
from ugjcs.application.identity import AuthenticationError, IdentityService
from ugjcs.domain.policies import Action, Actor, authorize

_MARKER = "_ugjcs_authorization_dependency"


def _mark(fn: Callable[..., Any]) -> Callable[..., Any]:
    setattr(fn, _MARKER, True)
    return fn


def is_authorization_dependency(call: Callable[..., Any]) -> bool:
    return bool(getattr(call, _MARKER, False))


IdentityDep = Annotated[IdentityService, Depends(get_identity_service)]


@_mark
async def get_current_actor(
    identity: IdentityDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Actor:
    """Read the bearer token, verify it, and assemble a fresh `Actor`.

    Roles are re-read from the database inside `IdentityService.actor_for` on every call
    — that freshness guarantee is Plan 3's, not this function's, and this function must
    never cache or otherwise shortcut it.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthenticationError("missing bearer token")
    token = authorization.removeprefix("Bearer ")
    return await identity.actor_for(token)


# See `wiring.UowDep` for why routes depend on this alias rather than a bare
# `actor: Actor = Depends(get_current_actor)` default — the same ruff B008 constraint
# applies here, including inside the `require()`-built dependency below.
ActorDep = Annotated[Actor, Depends(get_current_actor)]


def require(action: Action) -> Callable[..., Awaitable[Actor]]:
    """A role-level gate, correct for every `Action` except `VIEW` and `RESUBMIT`/`WITHDRAW`.

    `policies.can()` ignores its `manuscript` argument for every action except those
    three — confirmed by reading `_ROLE_GRANTS` and `_can_view`/`_OWNERSHIP_ACTIONS` in
    `ugjcs.domain.policies`. The exceptions call `authorize()` a second time inside the
    handler, once the resource is loaded; this dependency alone would deny them
    unconditionally, since it never has a manuscript to pass.
    """

    @_mark
    async def _dependency(actor: ActorDep) -> Actor:
        authorize(actor, action)
        return actor

    return _dependency
