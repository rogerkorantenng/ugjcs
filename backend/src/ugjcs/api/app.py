"""The FastAPI application factory.

A factory, not a module-level `app`, so tests can build a fresh instance per test and
override dependencies without one test's overrides leaking into another's.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

from ugjcs.api.errors import register_exception_handlers
from ugjcs.api.wiring import _engine
from ugjcs.infrastructure.config import get_settings

_FALLBACK_APP_URL = "https://ugjcs-frontend.vercel.app"

_ROOT_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>SDJ Editorial Portal — API</title>
<style>
  body {{ margin:0; font:16px/1.6 "Segoe UI",system-ui,sans-serif; color:#14181d;
         background:#f6f7f5; display:grid; min-height:100vh; place-items:center; }}
  main {{ max-width:34rem; margin:1rem; background:#fff; border:1px solid #d8dcd6;
          border-top:4px solid #fdb515; border-radius:4px; padding:2rem 2.2rem; }}
  .eyebrow {{ font:600 11px/1 ui-monospace,monospace; letter-spacing:.2em;
              text-transform:uppercase; color:#002855; }}
  h1 {{ font-family:Georgia,serif; font-size:1.4rem; margin:.5rem 0 1rem; }}
  .ok {{ color:#1a7a3a; font-weight:600; }}
  a.button {{ display:inline-block; margin-top:1rem; background:#002855; color:#fff;
              padding:.6rem 1.1rem; border-radius:3px; text-decoration:none;
              font-weight:600; font-size:.95rem; }}
  p.small {{ font-size:.85rem; color:#5a6068; margin-top:1.4rem; }}
  a {{ color:#002855; }}
</style>
</head>
<body>
<main>
  <p class="eyebrow">Science and Development Journal · Editorial Portal</p>
  <h1>This is the portal's API</h1>
  <p><span class="ok">&#10003; The API is running and healthy.</span></p>
  <p>There is nothing to browse here — this address serves the application's backend.
     The portal itself lives at:</p>
  <a class="button" href="{app_url}">Open the SDJ Editorial Portal</a>
  <p class="small">For the machine-readable surface, see the
     <a href="/docs">interactive API documentation</a> or the
     <a href="/health">health probe</a>.<br />
     Roger Koranteng Obeng · 22424140 · Advanced Software Engineering final project</p>
</main>
</body>
</html>"""


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

    @app.get("/", tags=["ops"], include_in_schema=False)
    def root(request: Request) -> Response:
        """A signpost, not an endpoint: anyone opening the API's base address gets told the
        service is up and where the actual application lives, instead of a bare 404. The
        frontend URL comes from the first configured CORS origin — the deployment already
        has to know it there — with a fallback for a config that has none."""
        app_url = settings.cors_origins[0] if settings.cors_origins else _FALLBACK_APP_URL
        if "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(_ROOT_PAGE.format(app_url=app_url))
        return JSONResponse(
            {
                "status": "ok",
                "message": "The SDJ Editorial Portal API is running.",
                "application": app_url,
                "documentation": "/docs",
                "health": "/health",
            }
        )

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
