"""Every non-public route must carry an authorization dependency.

This walks the live route table rather than trusting a checklist, because a checklist is
exactly the kind of thing a future change forgets to update. If a new route is added to
`ugjcs.api` without `Depends(get_current_actor)` or `Depends(require(...))` somewhere in
its dependency tree, this test fails — that is the whole point of it.

**Why this does not just filter `app.routes` for `APIRoute` instances**, the way the plan
this test implements originally described: the installed FastAPI (0.141) resolves
`include_router()` lazily — `app.routes` holds `_IncludedRouter` wrapper objects for every
router mounted via `include_router`, not flattened `APIRoute`s with their prefix already
applied. `/health` and `/ready`, registered directly on `app` via `@app.get(...)`, are
unaffected and appear as ordinary `APIRoute`s. `_walk_routes` below recurses through
`_IncludedRouter.effective_candidates()` to reach the same `(path, methods, dependant)`
triple this test needs, imported defensively so an older or newer FastAPI that flattens
eagerly (plain `APIRoute`s all the way down) still works unchanged.
"""

from collections.abc import Iterable, Iterator
from typing import Any

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from ugjcs.api.app import create_app
from ugjcs.api.deps import is_authorization_dependency

try:
    from fastapi.routing import _EffectiveRouteContext, _IncludedRouter
except ImportError:  # pragma: no cover - depends on the installed FastAPI's internals
    _IncludedRouter = None  # type: ignore[assignment,misc]
    _EffectiveRouteContext = None  # type: ignore[assignment,misc]

PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    # Self-service sign-up is public by definition — the caller has no credentials yet.
    # It can only ever create AUTHOR accounts; editorial roles are granted server-side
    # by appointment, never through this route.
    "/api/v1/auth/register",
    # Not in the plan's original allowlist (login and refresh only) — added per
    # `docs/05-api-contract.md` §6, which is authoritative over the plan where the two
    # disagree: "POST /auth/logout | none (refresh token in body)". This test caught the
    # disagreement on its first real run — `log_out` genuinely carries no
    # `get_current_actor`/`require(...)` dependency, matching the contract, not the
    # plan's narrower prose. Revocation is keyed by the refresh token's own hash, so a
    # bearer access token — which may already be expired at logout time — is not needed.
    "/api/v1/auth/logout",
}
PUBLIC_PREFIXES = ("/api/v1/archive",)


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


class _LiveRoute:
    __slots__ = ("dependant", "methods", "path")

    def __init__(self, path: str, methods: Iterable[str], dependant: Dependant) -> None:
        self.path = path
        self.methods = methods
        self.dependant = dependant


def _walk_routes(routes: Iterable[Any]) -> Iterator[_LiveRoute]:
    """Yield every real endpoint route, however this FastAPI version stores it."""
    for route in routes:
        if _IncludedRouter is not None and isinstance(route, _IncludedRouter):
            yield from _walk_routes(route.effective_candidates())
        elif _EffectiveRouteContext is not None and isinstance(route, _EffectiveRouteContext):
            if route.dependant is not None:
                yield _LiveRoute(route.path, route.methods, route.dependant)
        elif isinstance(route, APIRoute):
            yield _LiveRoute(route.path, route.methods or set(), route.dependant)


def _dependant_is_authorized(dependant: Dependant) -> bool:
    if dependant.call is not None and is_authorization_dependency(dependant.call):
        return True
    return any(_dependant_is_authorized(sub) for sub in dependant.dependencies)


def _live_routes() -> list[_LiveRoute]:
    return list(_walk_routes(create_app().routes))


def test_every_non_public_route_carries_an_authorization_dependency() -> None:
    unprotected = [
        f"{sorted(route.methods)} {route.path}"
        for route in _live_routes()
        if not _is_public(route.path) and not _dependant_is_authorized(route.dependant)
    ]
    assert unprotected == [], f"routes with no authorization dependency: {unprotected}"


def test_the_public_allowlist_is_not_accidentally_empty() -> None:
    """A guard against the trivial way this test could pass for the wrong reason: every
    route being (mis)classified as public. If this count ever drops to zero, something
    upstream changed path prefixes and the allowlist above needs updating, not deleting."""
    protected = [route for route in _live_routes() if not _is_public(route.path)]
    assert len(protected) >= 8


def test_the_archive_prefix_genuinely_has_no_authorization_dependency() -> None:
    """The mirror image of the main test: prove the allowlist is not hiding a route that
    actually IS protected, which would make the main test pass without checking anything."""
    archive_routes = [route for route in _live_routes() if route.path.startswith("/api/v1/archive")]
    assert archive_routes
    assert all(not _dependant_is_authorized(route.dependant) for route in archive_routes)


def test_login_refresh_and_logout_are_genuinely_unauthenticated() -> None:
    """The other half of the archive mirror test, for the three public auth routes: prove
    `/auth/login`, `/auth/refresh` and `/auth/logout` are unprotected in fact, not merely
    by allowlist — the first two because issuing a token is exactly what they cannot
    require a token for, the third because revocation is keyed by the refresh token
    itself (`docs/05-api-contract.md` §6), not by a bearer access token."""
    public_auth_paths = {"/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout"}
    public_auth_routes = [route for route in _live_routes() if route.path in public_auth_paths]
    assert len(public_auth_routes) == 3
    assert all(not _dependant_is_authorized(route.dependant) for route in public_auth_routes)
