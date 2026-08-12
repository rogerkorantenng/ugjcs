"""The FastAPI application factory.

A factory, not a module-level `app`, so tests can build a fresh instance per test and
override dependencies without one test's overrides leaking into another's.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from ugjcs.api.errors import register_exception_handlers
from ugjcs.api.wiring import _engine
from ugjcs.infrastructure.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UGJCS Editorial API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness only — must never touch the database."""
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready() -> dict[str, str]:
        """Readiness — proves the database is reachable, for the deployment platform's probe."""
        async with _engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ready"}

    # Auth, manuscripts, editorial and reviews routers (Plan 4 Tasks 2, 3, 5, 6) all
    # require an authenticated `Actor`, which needs `ugjcs.application.identity` (Plan
    # 3) — not available in this worktree. They are deliberately not wired here; see
    # `ugjcs.api.deps` for the stubbed `get_current_actor`/`require()` this leaves
    # behind for that work to finish against.
    from ugjcs.api.routers import archive

    app.include_router(archive.router, prefix="/api/v1/archive", tags=["archive"])

    return app
