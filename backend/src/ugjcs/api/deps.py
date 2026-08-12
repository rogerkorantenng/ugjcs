"""Request-scoped dependencies: who is calling, and what they may do.

Every dependency that establishes identity or authorisation is decorated with `_mark`,
so a future `tests/unit/api/test_route_audit.py` can walk the route table mechanically
and fail loudly if a route was wired up without one.

TODO(Plan 3): `get_current_actor` and `require()` are stubbed pending
`ugjcs.application.identity.IdentityService`/`SessionService`, which does not exist in
this worktree yet — authentication is being written concurrently in another worktree.
Do not wire either of these into a router until Plan 3 lands: doing so now would mean
either importing a module this task must not depend on, or fabricating authentication
behaviour that was never specified here. Replace the bodies below with the real
`Depends(get_identity_service)` / bearer-header parsing / `authorize()` call once it
does, following the shape already recorded in
`docs/superpowers/plans/2026-08-12-ugjcs-plan-4-editorial-api.md` Task 1 Step 7.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from ugjcs.domain.policies import Action, Actor

_MARKER = "_ugjcs_authorization_dependency"


def _mark(fn: Callable[..., Any]) -> Callable[..., Any]:
    setattr(fn, _MARKER, True)
    return fn


def is_authorization_dependency(call: Callable[..., Any]) -> bool:
    return bool(getattr(call, _MARKER, False))


@_mark
async def get_current_actor() -> Actor:
    """TODO(Plan 3): wire to `IdentityService.actor_for` once authentication lands."""
    raise NotImplementedError("authentication is not available in this worktree yet; see Plan 3")


def require(action: Action) -> Callable[..., Awaitable[Actor]]:
    """TODO(Plan 3): wire to `get_current_actor` + `authorize(actor, action)` once landed."""

    @_mark
    async def _dependency() -> Actor:
        raise NotImplementedError(
            f"authentication is not available in this worktree yet; see Plan 3 "
            f"(action={action.value})"
        )

    return _dependency
