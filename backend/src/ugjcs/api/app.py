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
    app = FastAPI(
        title="Science and Development Journal (SDJ) — Editorial Portal (pilot codename UGJCS)",
        description=(
            "Submission and peer-review portal for the Science and Development Journal, "
            "published by the College of Basic and Applied Sciences (CBAS), University of "
            "Ghana — moving the journal's editorial process off its manual email workflow."
        ),
        version="0.1.0",
    )

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

    from ugjcs.api.routers import (
        admin,
        archive,
        auth,
        billing,
        certificate,
        editorial,
        manuscripts,
        people,
        reviews,
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(manuscripts.router, prefix="/api/v1/manuscripts", tags=["manuscripts"])
    app.include_router(editorial.router, prefix="/api/v1/editorial", tags=["editorial"])
    app.include_router(
        certificate.router, prefix="/api/v1/editorial-certificate", tags=["editorial"]
    )
    app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
    app.include_router(archive.router, prefix="/api/v1/archive", tags=["archive"])
    app.include_router(people.router, prefix="/api/v1/people", tags=["people"])

    return app
