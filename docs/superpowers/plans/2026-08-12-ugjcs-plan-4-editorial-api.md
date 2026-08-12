# UGJCS Plan 4 — The Editorial API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the editorial workflow already built in Plans 1–3 over HTTP, as a FastAPI application versioned under `/api/v1`, so an examiner can open `/docs` in a browser and drive submission, screening, review and publication end to end.

**Dependency:** This plan assumes `docs/superpowers/plans/2026-08-12-ugjcs-plan-3-authentication.md` has already landed. It is written but **not yet executed** at the time this plan is authored — if its task order changed during implementation, re-read it before starting Task 2. This plan consumes, without redefining:

- `ugjcs.application.identity.IdentityService.actor_for(access_token: str) -> Actor` (raises `AuthenticationError`)
- `ugjcs.application.identity.SessionService.log_in(email, password) -> TokenPair`, `.refresh(token) -> TokenPair`, `.log_out(token) -> None`
- `ugjcs.application.ports.AccountRepository`
- `ugjcs.infrastructure.security.tokens.JwtTokenService`, `InvalidToken`
- `ugjcs.infrastructure.security.passwords.Argon2PasswordHasher`
- `ugjcs.infrastructure.db.uow.SqlAlchemyUnitOfWork`

**One assumption flagged rather than silently made:** Plan 3's Task 8 write-up specifies `SessionService`'s three methods but never writes out its constructor. This plan wires it as `SessionService(accounts, tokens, hasher, clock)`, mirroring `IdentityService(accounts, tokens)`'s already-confirmed shape. If Plan 3 lands with a different constructor, `backend/src/ugjcs/api/wiring.py`'s `_session_service` is the only place to fix — the three method names are the real contract.

**Architecture:** All HTTP concerns — FastAPI app, routers, request/response schemas, dependency wiring, error translation — live in a new top-level package `ugjcs.api`, a sibling of `domain`, `application` and `infrastructure`, never imported by any of them. `ugjcs.api` depends inward on all three; nothing depends on it. Route handlers do three things and nothing else: authenticate and authorise, call one method on a repository or aggregate obtained through `UnitOfWork`, and serialise the result — business logic stays in `ugjcs.domain`. Every non-public route carries an authorisation dependency built from `ugjcs.domain.policies`, enforced mechanically by a test that walks the route table.

**Tech Stack:** FastAPI, Uvicorn, Pydantic v2 (already a transitive dependency via pydantic-settings), httpx (test client only), the SQLAlchemy/Alembic stack from Plan 2, the security stack from Plan 3.

## Global Constraints

- Python **3.13**, all tooling via `uv run` from `backend/`.
- The layered import contract holds and gains one layer: `ugjcs.api` → `ugjcs.infrastructure` → `ugjcs.application` → `ugjcs.domain`, inward only. `ugjcs.api` is added as Task 1's first step.
- Timestamps are timezone-aware UTC.
- `make check`'s coverage gate (`--cov=src/ugjcs/domain --cov=src/ugjcs/application`, `--fail-under=85`) is **untouched** by this plan — `ugjcs.api` and the new repository query methods in `ugjcs.infrastructure` are adapters, measured the same way Plan 2 already excluded infrastructure from the gate. API tests still run in the default `make check` pytest invocation and must pass; they just are not what the 85% figure is computed from. Do not edit the Makefile's `--cov` flags.
- mypy `strict`; ruff line-length 100, select `["E","F","I","N","UP","B","A","C4","SIM","RUF"]`; `ruff format` authoritative. No new `# noqa`, `# fmt: off`, or `# pragma: no cover` beyond the two already-authorised registration-side-effect imports from Plan 2.
- **API-layer tests use fakes for `AccountRepository`, `IdentityService`, `SessionService` and `TokenService`** — they are unit tests, not integration tests, and must not require Docker. Tests that exercise the new repository query methods (`list_by_author`, `list_by_status`, `list_published`, `search_published`) and the assignment repository run against the real testcontainers Postgres, marked `@pytest.mark.integration`, exactly as Plan 2 established.
- Conventional Commits. Author: Roger Koranteng Obeng, student ID 22424140.
- Never log a bearer token or a password.

## Scope decision: reviewer assignment is a persistence-only record, not a domain aggregate

**Choice:** an editor assigns a reviewer directly — `POST /editorial/{tracking_code}/reviewers` inserts a `ReviewAssignmentRow` and nothing more. No `ReviewAssignment` domain aggregate, no invitation/accept/decline lifecycle, no conflict-of-interest check.

**Why:** `Manuscript.record_review` already only counts, so an aggregate enforcing assignment invariants would have nothing in the domain layer to protect against — it would just be a second bookkeeping table with more code. Building the lifecycle `AssignmentStatus` already anticipates (invited → accepted/declined → submitted, with expiry) is a real feature with its own notification and re-invitation rules, and it does not fit a 48-hour window that still has deployment ahead of it. The gap (no COI exclusion, no capacity limit, no invitation step) is entered in the technical debt register at the end of this plan rather than partially built.

## Interfaces inherited — do not redefine, import them

- `ugjcs.domain.policies` — `Actor(id, roles)`, `Action`, `can(actor, action, manuscript=None)`, `authorize(...)`. Every `Action` except `VIEW` and `RESUBMIT` checks role membership alone and ignores its `manuscript` argument — confirmed by reading `_ROLE_GRANTS` and `_can_view` in `policies.py`. This is what makes a single role-level dependency correct for `SUBMIT`, `SCREEN`, `ASSIGN_REVIEWER`, `REVIEW`, `DECIDE`, `PUBLISH`.
- `ugjcs.domain.manuscript.Manuscript` — `submit`, `begin_screening`, `record_review`, `record_decision`, `resubmit`, `schedule`, `publish`, `withdraw`, `pull_events`, and the `status`/`version`/`submitted_reviews` fields.
- `ugjcs.domain.blinding.blind(manuscript) -> BlindedManuscript` — `tracking_code, title, abstract, keywords, version, status`. No author field exists on the type; that is the structural guarantee Task 6's test exploits.
- `ugjcs.domain.errors` — `DomainError, IllegalTransitionError, GuardViolationError, AuthorizationDeniedError`.
- `ugjcs.domain.enums` — `Role, ManuscriptStatus, DecisionType, EventType`.
- `ugjcs.application.ports` — `ManuscriptRepository, UnitOfWork, AccountRepository, Clock, PasswordHasher, TokenService`.
- `ugjcs.infrastructure.db.engine.create_engine, session_factory`; `ugjcs.infrastructure.db.uow.SqlAlchemyUnitOfWork`; `ugjcs.infrastructure.config.Settings, get_settings`.

**One necessary, minimal domain addition, flagged rather than silently made:** `ugjcs.domain.policies.Action` has no `WITHDRAW` member. Withdrawal needs an authorisation rule (only the corresponding author may withdraw their own submission — an editor desk-rejects instead, via `DECIDE`), and there is nowhere to express "only the owner may do this" outside `policies.py`'s `_OWNERSHIP_ACTIONS` mechanism. Task 3 adds one enum member and one frozenset entry. It changes no existing behaviour and breaks no existing test.

---

## File Structure

```
backend/
├── pyproject.toml                                   Task 1  fastapi, uvicorn, httpx
├── .importlinter                                     Task 1  ugjcs.api added as the outermost layer
├── src/ugjcs/
│   ├── domain/
│   │   └── policies.py                               Task 3  (extended) Action.WITHDRAW
│   ├── application/
│   │   └── ports.py                                  Task 3, 4  (extended) list_by_author/list_by_status, ReviewAssignmentRepository
│   ├── infrastructure/
│   │   ├── config.py                                 Task 1  (extended) cors_allowed_origins
│   │   └── db/
│   │       ├── models.py                             Task 4  (extended) ReviewAssignmentRow
│   │       ├── mappers.py                             Task 4  (extended) assignment mapping
│   │       └── repository.py                          Task 3, 5, 7  (extended) query methods
│   └── api/
│       ├── __init__.py                                Task 1
│       ├── errors.py                                  Task 1  RFC 9457 problem-details handlers
│       ├── wiring.py                                  Task 1  DI: engine, UoW, services
│       ├── deps.py                                    Task 1  get_current_actor, require(), marker
│       ├── schemas.py                                  Task 3  (extended per task) response/request models
│       ├── app.py                                      Task 1  (extended per task) create_app()
│       ├── main.py                                     Task 1  uvicorn entrypoint
│       └── routers/
│           ├── __init__.py                             Task 1
│           ├── auth.py                                 Task 2
│           ├── manuscripts.py                          Task 3
│           ├── editorial.py                            Task 5
│           ├── reviews.py                               Task 6
│           └── archive.py                               Task 7
├── alembic/versions/0003_review_assignments.py         Task 4
└── tests/
    ├── unit/api/
    │   ├── __init__.py                                 Task 1
    │   ├── fakes.py                                     Task 1  in-memory AccountRepository/IdentityService/SessionService
    │   ├── test_health.py                                Task 1
    │   ├── test_errors.py                                Task 1
    │   ├── test_cors.py                                  Task 1
    │   ├── test_auth_router.py                            Task 2
    │   ├── test_manuscripts_router.py                     Task 3
    │   ├── test_editorial_router.py                        Task 5
    │   ├── test_reviews_router.py                           Task 6
    │   ├── test_blinding_leak.py                            Task 6
    │   ├── test_archive_router.py                            Task 7
    │   └── test_route_audit.py                              Task 8
    └── integration/
        ├── test_manuscript_queries.py                    Task 3
        ├── test_review_assignment_repository.py           Task 4
        ├── test_editorial_queries.py                       Task 5
        └── test_archive_queries.py                          Task 7
```

---

### Task 1: Application shell — settings, errors, DI, health

**Files:**
- Modify: `backend/pyproject.toml`, `backend/.importlinter`, `backend/src/ugjcs/infrastructure/config.py`
- Create: `backend/src/ugjcs/api/__init__.py`, `backend/src/ugjcs/api/errors.py`, `backend/src/ugjcs/api/wiring.py`, `backend/src/ugjcs/api/deps.py`, `backend/src/ugjcs/api/app.py`, `backend/src/ugjcs/api/main.py`, `backend/src/ugjcs/api/routers/__init__.py`
- Test: `backend/tests/unit/api/__init__.py`, `backend/tests/unit/api/fakes.py`, `backend/tests/unit/api/test_health.py`, `backend/tests/unit/api/test_errors.py`, `backend/tests/unit/api/test_cors.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`; `get_current_actor`, `require(action) -> Callable`, `is_authorization_dependency(call) -> bool`; `register_exception_handlers(app)`; `get_uow`, `get_identity_service`, `get_session_service`.

- [ ] **Step 1: Add dependencies**

```bash
cd backend
uv add fastapi "uvicorn[standard]"
uv add --dev httpx
```

- [ ] **Step 2: Add the outermost layer to the import contract**

Modify `backend/.importlinter`, changing only the `layers` list:

```ini
[importlinter:contract:layers]
name = Dependencies point inwards only
type = layers
layers =
    ugjcs.api
    ugjcs.infrastructure
    ugjcs.application
    ugjcs.domain
```

Leave `domain-purity` exactly as it stands.

- [ ] **Step 3: Extend settings**

Add to `Settings` in `backend/src/ugjcs/infrastructure/config.py`:

```python
    cors_allowed_origins: str = Field(
        default="",
        description="Comma-separated browser origins allowed to call the API, e.g. "
        "https://ugjcs.example.edu,http://localhost:3000. Empty means none allowed.",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
```

`cors_allowed_origins` is a plain string, not a `list[str]` field, because pydantic-settings expects list-typed fields to be JSON in the environment by default — a bare comma-separated value would fail to parse. Splitting it ourselves in a property keeps `UGJCS_CORS_ALLOWED_ORIGINS=https://a.com,https://b.com` working without a custom parser.

- [ ] **Step 4: Write the failing tests**

Create `backend/tests/unit/api/__init__.py` (empty) and `backend/tests/unit/api/fakes.py`:

```python
"""In-memory fakes for API-layer unit tests.

These stand in for `AccountRepository`, `IdentityService` and `SessionService` so that
routes wire correctly without a database. Correctness of the real adapters is Plan 3's
job, proven there against a live Postgres; this package tests routing, authorisation and
serialisation only.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor


@dataclass
class FakeAccount:
    id: UserId
    email: str
    roles: frozenset[Role]
    is_active: bool = True
    is_verified: bool = True


class FakeIdentityService:
    """`actor_for` reads a token that is literally the account id, as text."""

    def __init__(self, accounts: dict[UserId, FakeAccount]) -> None:
        self._accounts = accounts

    async def actor_for(self, access_token: str) -> Actor:
        from ugjcs.application.identity import AuthenticationError

        try:
            subject = UserId(UUID(access_token))
        except ValueError as error:
            raise AuthenticationError("token is not valid") from error
        account = self._accounts.get(subject)
        if account is None or not account.is_active or not account.is_verified:
            raise AuthenticationError("no usable account for this credential")
        return Actor(id=account.id, roles=account.roles)


@dataclass
class FakeManuscriptRepository:
    """Enough of `ManuscriptRepository` for router tests: an in-memory dict, no chain."""

    store: dict[ManuscriptId, Manuscript] = field(default_factory=dict)

    async def add(self, manuscript: Manuscript) -> None:
        self.store[manuscript.id] = manuscript
        manuscript.pull_events()

    async def get(self, manuscript_id: ManuscriptId) -> Manuscript | None:
        return self.store.get(manuscript_id)

    async def get_by_tracking_code(self, code: object) -> Manuscript | None:
        value = getattr(code, "value", code)
        return next(
            (m for m in self.store.values() if m.tracking_code.value == value), None
        )

    async def save(self, manuscript: Manuscript) -> None:
        self.store[manuscript.id] = manuscript
        manuscript.pull_events()

    async def chain_for(self, manuscript_id: ManuscriptId) -> list[object]:
        return []

    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        return [m for m in self.store.values() if author_id in m.author_ids]

    async def list_by_status(self, status: object) -> list[Manuscript]:
        return [m for m in self.store.values() if m.status == status]

    async def list_published(self) -> list[Manuscript]:
        from ugjcs.domain.enums import ManuscriptStatus as S

        return [m for m in self.store.values() if m.status is S.PUBLISHED]

    async def search_published(self, query: str) -> list[Manuscript]:
        published = await self.list_published()
        needle = query.lower()
        return [m for m in published if needle in m.title.lower() or needle in m.abstract.lower()]


@dataclass
class FakeUnitOfWork:
    manuscripts: FakeManuscriptRepository = field(default_factory=FakeManuscriptRepository)
    assignments: object = None

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def new_user_id() -> UserId:
    return UserId(uuid4())
```

`FakeManuscriptRepository` already implements the four query methods later tasks add to the real protocol — writing the fake once here means Tasks 3, 5 and 7 only add fixtures and assertions, never touch this file again except to extend `FakeUnitOfWork`.

Create `backend/tests/unit/api/test_health.py`:

```python
from fastapi.testclient import TestClient

from ugjcs.api.app import create_app


def test_health_reports_ok_without_touching_the_database() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_document_is_served_so_docs_can_render() -> None:
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]
```

Create `backend/tests/unit/api/test_errors.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugjcs.api.errors import register_exception_handlers
from ugjcs.domain.errors import AuthorizationDeniedError, GuardViolationError, IllegalTransitionError


def make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/illegal")
    def _illegal() -> None:
        raise IllegalTransitionError("cannot move from draft to published")

    @app.get("/boom/guard")
    def _guard() -> None:
        raise GuardViolationError("quorum not met")

    @app.get("/boom/forbidden")
    def _forbidden() -> None:
        raise AuthorizationDeniedError("actor may not decide")

    @app.get("/boom/missing")
    def _missing() -> None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="manuscript not found")

    return app


def test_illegal_transition_becomes_409_problem_json() -> None:
    response = TestClient(make_app()).get("/boom/illegal")
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 409
    assert body["title"] == "IllegalTransitionError"
    assert "draft to published" in body["detail"]
    assert body["instance"] == "/boom/illegal"


def test_guard_violation_becomes_409() -> None:
    response = TestClient(make_app()).get("/boom/guard")
    assert response.status_code == 409


def test_authorization_denied_becomes_403() -> None:
    response = TestClient(make_app()).get("/boom/forbidden")
    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"


def test_http_exception_is_also_rendered_as_a_problem() -> None:
    response = TestClient(make_app()).get("/boom/missing")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "manuscript not found"
    assert body["status"] == 404
```

Create `backend/tests/unit/api/test_cors.py`:

```python
import os

from fastapi.testclient import TestClient

from ugjcs.infrastructure.config import get_settings


def test_an_allowed_origin_receives_cors_headers(monkeypatch: object) -> None:
    import pytest

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("UGJCS_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("UGJCS_JWT_SECRET", "test-secret")
    monkeypatch.setenv("UGJCS_CORS_ALLOWED_ORIGINS", "https://ugjcs.example.edu")
    get_settings.cache_clear()

    from ugjcs.api.app import create_app

    client = TestClient(create_app())
    response = client.get(
        "/health", headers={"Origin": "https://ugjcs.example.edu"}
    )
    assert response.headers["access-control-allow-origin"] == "https://ugjcs.example.edu"
    monkeypatch.undo()
    get_settings.cache_clear()


def test_an_origin_not_on_the_allowlist_receives_no_cors_header(monkeypatch: object) -> None:
    import pytest

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("UGJCS_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("UGJCS_JWT_SECRET", "test-secret")
    monkeypatch.setenv("UGJCS_CORS_ALLOWED_ORIGINS", "https://ugjcs.example.edu")
    get_settings.cache_clear()

    from ugjcs.api.app import create_app

    client = TestClient(create_app())
    response = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers
    monkeypatch.undo()
    get_settings.cache_clear()
```

`get_settings` is `@lru_cache`d (Plan 2's `config.py`); these tests must clear the cache before and after or they read whatever an earlier test in the same process already cached, exactly as Plan 2's Task 5 warns.

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/api -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.api'`

- [ ] **Step 6: Write the error handlers**

Create `backend/src/ugjcs/api/__init__.py` (empty) and `backend/src/ugjcs/api/errors.py`:

```python
"""RFC 9457 problem-details responses.

Domain errors carry no HTTP semantics of their own. Translating them into status codes
is an infrastructure concern, and this module is the single place that does it, so no
route can invent its own inconsistent error shape.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ugjcs.domain.errors import (
    AuthorizationDeniedError,
    DomainError,
    GuardViolationError,
    IllegalTransitionError,
)

PROBLEM_MEDIA_TYPE = "application/problem+json"

# Ordered by specificity: an unlisted `DomainError` subclass falls through to 400, which
# is the correct default for "the request was well-formed but the domain rejected it."
_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    IllegalTransitionError: status.HTTP_409_CONFLICT,
    GuardViolationError: status.HTTP_409_CONFLICT,
    AuthorizationDeniedError: status.HTTP_403_FORBIDDEN,
}


def _status_for(error: DomainError) -> int:
    for error_type, code in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return code
    if type(error).__name__ in {"AuthenticationError", "InvalidToken"}:
        return status.HTTP_401_UNAUTHORIZED
    if type(error).__name__ == "AccountError":
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_400_BAD_REQUEST


def _problem(status_code: int, title: str, detail: str, *, instance: str) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    return JSONResponse(status_code=status_code, content=body, media_type=PROBLEM_MEDIA_TYPE)


def register_exception_handlers(app: FastAPI) -> None:
    """Wire every `DomainError`, every `HTTPException`, and validation failures alike."""

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            _status_for(exc), type(exc).__name__, str(exc), instance=str(request.url.path)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(
            exc.status_code,
            exc.__class__.__name__,
            str(exc.detail),
            instance=str(request.url.path),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RequestValidationError",
            "the request body failed validation",
            instance=str(request.url.path),
        )
```

`AuthenticationError`, `InvalidToken` and `AccountError` are matched by class name rather than imported, deliberately: importing `ugjcs.application.identity` here would be fine under the layers contract (`api` may import `application`), but importing `ugjcs.infrastructure.security.tokens` for `InvalidToken` alongside it would mean this module reaches into two different layers for what is conceptually one job — mapping domain-shaped errors to status codes. Name matching keeps `errors.py` dependent on `ugjcs.domain` alone. If this feels too clever when you are implementing it, the alternative — importing both exception classes directly — is also acceptable; report which you chose.

- [ ] **Step 7: Write the DI wiring and auth dependency**

Create `backend/src/ugjcs/api/wiring.py`:

```python
"""Dependency wiring: turns configuration into the services routes consume.

Kept apart from `deps.py` so authorisation logic stays readable without scrolling past
engine and session-factory construction.
"""

from collections.abc import AsyncIterator
from datetime import timedelta
from functools import lru_cache

from ugjcs.application.identity import IdentityService, SessionService
from ugjcs.application.ports import UnitOfWork
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import JwtTokenService, SystemClock


@lru_cache
def _engine():  # type: ignore[no-untyped-def]
    settings = get_settings()
    return create_engine(settings.database_url, echo=settings.sql_echo)


@lru_cache
def _sessions():  # type: ignore[no-untyped-def]
    return session_factory(_engine())


@lru_cache
def _tokens() -> JwtTokenService:
    settings = get_settings()
    return JwtTokenService(
        secret=settings.jwt_secret,
        clock=SystemClock(),
        access_ttl=timedelta(minutes=settings.access_token_minutes),
        refresh_ttl=timedelta(days=settings.refresh_token_days),
    )


async def get_uow() -> AsyncIterator[UnitOfWork]:
    async with SqlAlchemyUnitOfWork(_sessions()) as uow:  # type: ignore[no-untyped-call]
        yield uow


async def get_identity_service(uow: UnitOfWork = None) -> IdentityService:  # placeholder, replaced below
    raise NotImplementedError


async def get_session_service(uow: UnitOfWork = None) -> SessionService:  # placeholder, replaced below
    raise NotImplementedError
```

**Rewrite the last two functions immediately** — they are written above as an intermediate step because `Depends(get_uow)` cannot appear as a default argument until `fastapi` is imported, and this module must stay importable from `deps.py` without a circular import. Replace them with:

```python
from fastapi import Depends


async def get_identity_service(uow: UnitOfWork = Depends(get_uow)) -> IdentityService:
    return IdentityService(uow.accounts, _tokens())


async def get_session_service(uow: UnitOfWork = Depends(get_uow)) -> SessionService:
    return SessionService(uow.accounts, _tokens(), Argon2PasswordHasher(), SystemClock())
```

and delete the two `NotImplementedError` placeholders and the `# placeholder` comments. (This two-step description exists only because the plan is read top-to-bottom before being typed; write the final file directly with `Depends` imported at the top and the placeholders never created.)

Create `backend/src/ugjcs/api/deps.py`:

```python
"""Request-scoped dependencies: who is calling, and what they may do.

Every dependency that establishes identity or authorisation is decorated with
`_mark`, so `tests/unit/api/test_route_audit.py` can walk the route table mechanically
and fail loudly if a route was wired up without one — the one guarantee this API makes
that must never depend on a reviewer remembering to add `Depends(...)`.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends, Header

from ugjcs.application.identity import AuthenticationError, IdentityService
from ugjcs.api.wiring import get_identity_service
from ugjcs.domain.policies import Action, Actor, authorize

_MARKER = "_ugjcs_authorization_dependency"


def _mark(fn: Callable[..., Any]) -> Callable[..., Any]:
    setattr(fn, _MARKER, True)
    return fn


def is_authorization_dependency(call: Callable[..., Any]) -> bool:
    return bool(getattr(call, _MARKER, False))


@_mark
async def get_current_actor(
    authorization: Annotated[str | None, Header()] = None,
    identity: IdentityService = Depends(get_identity_service),
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


def require(action: Action) -> Callable[..., Awaitable[Actor]]:
    """A role-level gate, correct for every `Action` except `VIEW` and `RESUBMIT`.

    `policies.can()` ignores its `manuscript` argument for every action except those two
    — confirmed by reading `_ROLE_GRANTS` and `_can_view` in `ugjcs.domain.policies`. The
    two exceptions call `authorize()` a second time inside the handler, once the resource
    is loaded; this dependency alone would deny them unconditionally, since it never has
    a manuscript to pass.
    """

    @_mark
    async def _dependency(actor: Actor = Depends(get_current_actor)) -> Actor:
        authorize(actor, action)
        return actor

    return _dependency
```

- [ ] **Step 8: Write the app factory and entrypoint**

Create `backend/src/ugjcs/api/routers/__init__.py` (empty) and `backend/src/ugjcs/api/app.py`:

```python
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
        async with _engine().connect() as connection:  # type: ignore[no-untyped-call]
            await connection.execute(text("SELECT 1"))
        return {"status": "ready"}

    # Later tasks append one `app.include_router(...)` call per router here:
    # from ugjcs.api.routers import auth
    # app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

    return app
```

Create `backend/src/ugjcs/api/main.py`:

```python
"""Uvicorn entrypoint: `uv run uvicorn ugjcs.api.main:app`."""

from ugjcs.api.app import create_app

app = create_app()
```

- [ ] **Step 9: Run the tests**

Run: `cd backend && uv run pytest tests/unit/api -v`
Expected: PASS. `test_ready` is not exercised here (Task 1 has no repository behind it yet in these fakes) — the health/errors/cors tests above are the ones this task must turn green; `/ready` is proved by the integration suite once a real engine exists, which it already does via `_engine()`, so no separate test is required in this task beyond confirming the route imports without error.

- [ ] **Step 10: Run the gates**

Run: `cd backend && make check`
Expected: ruff, mypy, both import contracts (now three layers) pass; unit tests pass; the domain+application coverage figure is unaffected because `ugjcs.api` is outside the `--cov` flags.

- [ ] **Step 11: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/.importlinter backend/src/ugjcs/infrastructure/config.py backend/src/ugjcs/api backend/tests/unit/api
git commit -m "feat: add the FastAPI application shell, problem-details errors and DI wiring"
```

---

### Task 2: Auth router

**Files:**
- Create: `backend/src/ugjcs/api/routers/auth.py`, `backend/tests/unit/api/test_auth_router.py`
- Modify: `backend/src/ugjcs/api/app.py`

**Interfaces:**
- Consumes: `SessionService.log_in/refresh/log_out`, `IdentityService.actor_for`, `get_current_actor`.
- Produces: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/api/test_auth_router.py`:

```python
from dataclasses import dataclass

from fastapi.testclient import TestClient

from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_identity_service, get_session_service
from ugjcs.application.identity import AuthenticationError
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor
from tests.unit.api.fakes import FakeIdentityService, new_user_id


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class FakeSessionService:
    def __init__(self) -> None:
        self.editor_id = new_user_id()
        self._live_refresh = "refresh-token-abc"

    async def log_in(self, email: str, password: str) -> TokenPair:
        if email != "editor@ug.edu.gh" or password != "correct horse battery staple":
            raise AuthenticationError("invalid credentials")
        return TokenPair(access_token=str(self.editor_id), refresh_token=self._live_refresh)

    async def refresh(self, token: str) -> TokenPair:
        if token != self._live_refresh:
            raise AuthenticationError("refresh token is not valid")
        self._live_refresh = "refresh-token-rotated"
        return TokenPair(access_token=str(self.editor_id), refresh_token=self._live_refresh)

    async def log_out(self, token: str) -> None:
        self._live_refresh = ""


def make_client() -> tuple[TestClient, FakeSessionService, dict]:
    app = create_app()
    session_service = FakeSessionService()
    accounts = {
        session_service.editor_id: __import__(
            "tests.unit.api.fakes", fromlist=["FakeAccount"]
        ).FakeAccount(
            id=session_service.editor_id,
            email="editor@ug.edu.gh",
            roles=frozenset({Role.EDITOR}),
        )
    }
    app.dependency_overrides[get_session_service] = lambda: session_service
    app.dependency_overrides[get_identity_service] = lambda: FakeIdentityService(accounts)
    return TestClient(app), session_service, accounts


def test_correct_credentials_return_a_token_pair() -> None:
    client, _, _ = make_client()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "editor@ug.edu.gh", "password": "correct horse battery staple"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_wrong_password_is_rejected_with_401() -> None:
    client, _, _ = make_client()
    response = client.post(
        "/api/v1/auth/login", json={"email": "editor@ug.edu.gh", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


def test_refresh_returns_a_new_pair() -> None:
    client, session_service, _ = make_client()
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "refresh-token-abc"}
    )
    assert response.status_code == 200
    assert response.json()["refresh_token"] == "refresh-token-rotated"


def test_logout_succeeds_with_no_body() -> None:
    client, _, _ = make_client()
    response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": "refresh-token-abc"}
    )
    assert response.status_code == 204


def test_me_requires_a_bearer_token() -> None:
    client, _, _ = make_client()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_the_authenticated_actor(monkeypatch: object) -> None:
    client, session_service, _ = make_client()
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_service.editor_id}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(session_service.editor_id)
    assert body["roles"] == ["editor"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/api/test_auth_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.api.routers.auth'`

- [ ] **Step 3: Write the schemas and router**

Create `backend/src/ugjcs/api/routers/auth.py`:

```python
"""Login, refresh, logout and the identity of the caller."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr

from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_session_service
from ugjcs.application.identity import SessionService
from ugjcs.domain.policies import Actor

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ActorOut(BaseModel):
    id: str
    roles: list[str]


@router.post("/login", response_model=TokenPairOut)
async def log_in(
    body: LoginRequest, sessions: SessionService = Depends(get_session_service)
) -> TokenPairOut:
    pair = await sessions.log_in(body.email, body.password)
    return TokenPairOut(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/refresh", response_model=TokenPairOut)
async def refresh(
    body: RefreshRequest, sessions: SessionService = Depends(get_session_service)
) -> TokenPairOut:
    pair = await sessions.refresh(body.refresh_token)
    return TokenPairOut(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def log_out(
    body: RefreshRequest, sessions: SessionService = Depends(get_session_service)
) -> None:
    await sessions.log_out(body.refresh_token)


@router.get("/me", response_model=ActorOut)
async def me(actor: Actor = Depends(get_current_actor)) -> ActorOut:
    return ActorOut(id=str(actor.id), roles=sorted(role.value for role in actor.roles))
```

`/login` and `/refresh` are deliberately unauthenticated — a bearer token is exactly what they are issuing — and are the two entries `test_route_audit.py` (Task 8) allowlists as public alongside `/health`, `/ready` and `/archive`. `/logout` and `/me` both carry `get_current_actor`, which is a marked authorization dependency, so they need no allowlist entry.

- [ ] **Step 4: Wire the router**

In `backend/src/ugjcs/api/app.py`, replace the comment block at the end of `create_app` with:

```python
    from ugjcs.api.routers import auth

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
```

- [ ] **Step 5: Run the tests, gates, commit**

Run: `cd backend && uv run pytest tests/unit/api -v` — report the count.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/api/routers/auth.py backend/src/ugjcs/api/app.py backend/tests/unit/api/test_auth_router.py
git commit -m "feat: add login, refresh, logout and me under /api/v1/auth"
```

---

### Task 3: Manuscripts router

**Files:**
- Modify: `backend/src/ugjcs/domain/policies.py`, `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/db/repository.py`, `backend/src/ugjcs/api/app.py`
- Create: `backend/src/ugjcs/api/schemas.py`, `backend/src/ugjcs/api/routers/manuscripts.py`, `backend/tests/unit/api/test_manuscripts_router.py`, `backend/tests/integration/test_manuscript_queries.py`

**Interfaces:**
- Produces: `Action.WITHDRAW`; `ManuscriptRepository.list_by_author`; `ManuscriptOut`; `POST /api/v1/manuscripts`, `GET /api/v1/manuscripts/mine`, `GET /api/v1/manuscripts/{tracking_code}`, `POST /api/v1/manuscripts/{tracking_code}/withdraw`.

- [ ] **Step 1: Add `Action.WITHDRAW`**

In `backend/src/ugjcs/domain/policies.py`, add one enum member and one frozenset entry:

```python
class Action(StrEnum):
    VIEW = "view"
    SUBMIT = "submit"
    SCREEN = "screen"
    ASSIGN_REVIEWER = "assign_reviewer"
    REVIEW = "review"
    DECIDE = "decide"
    RESUBMIT = "resubmit"
    WITHDRAW = "withdraw"
    PUBLISH = "publish"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT = "view_audit"
```

```python
_OWNERSHIP_ACTIONS = frozenset({Action.RESUBMIT, Action.WITHDRAW})
```

Both actions now share the rule already coded in `can()`: the actor must hold `Role.AUTHOR` and be the manuscript's `corresponding_author_id`. No other line in `policies.py` changes.

- [ ] **Step 2: Add `list_by_author` to the port**

Append to `ManuscriptRepository` in `backend/src/ugjcs/application/ports.py`:

```python
    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        """Every manuscript on which this user appears as an author, newest first."""
        ...
```

Add `from ugjcs.domain.ids import UserId` to that file's imports if not already present (it imports `ManuscriptId, TrackingCode` already — extend the same line).

- [ ] **Step 3: Write the failing integration test**

Create `backend/tests/integration/test_manuscript_queries.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR_A = UserId(uuid4())
AUTHOR_B = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make(author: UserId, sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=f"Paper {sequence}",
        abstract="An abstract.",
        keywords=("networking",),
        author_ids=(author,),
        corresponding_author_id=author,
    )


async def test_list_by_author_returns_only_that_authors_manuscripts(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    mine = make(AUTHOR_A, 1)
    mine.submit(actor_id=AUTHOR_A, occurred_at=NOW)
    theirs = make(AUTHOR_B, 2)
    theirs.submit(actor_id=AUTHOR_B, occurred_at=NOW)
    await repository.add(mine)
    await repository.add(theirs)
    await session.commit()

    results = await repository.list_by_author(AUTHOR_A)
    assert {m.id for m in results} == {mine.id}


async def test_list_by_author_is_empty_for_an_author_with_nothing_submitted(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    assert await repository.list_by_author(UserId(uuid4())) == []
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_manuscript_queries.py -m integration -v`
Expected: FAIL — `AttributeError: 'SqlAlchemyManuscriptRepository' object has no attribute 'list_by_author'`

- [ ] **Step 5: Implement the query**

Add to `SqlAlchemyManuscriptRepository` in `backend/src/ugjcs/infrastructure/db/repository.py`:

```python
    async def list_by_author(self, author_id: UserId) -> list[Manuscript]:
        result = await self._session.execute(
            select(ManuscriptRow)
            .join(ManuscriptRow.authors)
            .where(ManuscriptAuthorRow.author_id == author_id)
            .order_by(ManuscriptRow.id)
        )
        rows = result.scalars().unique().all()
        return [await self._rehydrate(row) for row in rows]  # type: ignore[misc]
```

Add `ManuscriptAuthorRow` to that file's import from `ugjcs.infrastructure.db.models`, and `UserId` to its import from `ugjcs.domain.ids`. `_rehydrate` returns `Manuscript | None` but every row here came from a real query result, so the `# type: ignore[misc]` on the list comprehension's `None` branch is intentional — narrowing it properly would need a second helper for a case that cannot occur; report if you find a cleaner way that still satisfies mypy strict.

- [ ] **Step 6: Run the integration test**

Run: `cd backend && uv run pytest tests/integration/test_manuscript_queries.py -m integration -v`
Expected: PASS, 2 tests.

- [ ] **Step 7: Write the schemas and the failing router test**

Create `backend/src/ugjcs/api/schemas.py`:

```python
"""Wire shapes. The domain must never import pydantic — these live here, not there."""

from uuid import UUID

from pydantic import BaseModel

from ugjcs.domain.manuscript import Manuscript


class ManuscriptOut(BaseModel):
    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    author_ids: tuple[UUID, ...]
    corresponding_author_id: UUID
    status: str
    version: int
    minimum_reviews: int
    submitted_reviews: int

    @classmethod
    def from_domain(cls, manuscript: Manuscript) -> "ManuscriptOut":
        return cls(
            tracking_code=manuscript.tracking_code.value,
            title=manuscript.title,
            abstract=manuscript.abstract,
            keywords=manuscript.keywords,
            author_ids=tuple(UUID(str(a)) for a in manuscript.author_ids),
            corresponding_author_id=UUID(str(manuscript.corresponding_author_id)),
            status=manuscript.status.value,
            version=manuscript.version,
            minimum_reviews=manuscript.minimum_reviews,
            submitted_reviews=manuscript.submitted_reviews,
        )


class SubmitManuscriptRequest(BaseModel):
    title: str
    abstract: str
    keywords: tuple[str, ...]
    co_author_ids: tuple[UUID, ...] = ()
```

Create `backend/tests/unit/api/test_manuscripts_router.py`:

```python
from fastapi.testclient import TestClient

from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor
from tests.unit.api.fakes import FakeUnitOfWork, new_user_id


AUTHOR = new_user_id()
OTHER_AUTHOR = new_user_id()


def make_client(actor: Actor) -> tuple[TestClient, FakeUnitOfWork]:
    from ugjcs.api.wiring import get_uow

    app = create_app()
    uow = FakeUnitOfWork()

    async def _uow():
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app), uow


def test_an_author_can_submit_a_manuscript() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow = make_client(actor)
    response = client.post(
        "/api/v1/manuscripts",
        json={"title": "Sparse Retrieval", "abstract": "An abstract.", "keywords": ["ir"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "submitted"
    assert body["author_ids"] == [str(AUTHOR)]
    assert len(uow.manuscripts.store) == 1


def test_a_reviewer_without_the_author_role_cannot_submit() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.REVIEWER}))
    client, _ = make_client(actor)
    response = client.post(
        "/api/v1/manuscripts",
        json={"title": "X", "abstract": "Y", "keywords": []},
    )
    assert response.status_code == 403


def test_mine_lists_only_the_callers_manuscripts() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow = make_client(actor)
    client.post(
        "/api/v1/manuscripts", json={"title": "Mine", "abstract": "A.", "keywords": []}
    )
    response = client.get("/api/v1/manuscripts/mine")
    assert response.status_code == 200
    assert [m["title"] for m in response.json()] == ["Mine"]


def test_retrieving_someone_elses_manuscript_is_forbidden() -> None:
    owner = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow = make_client(owner)
    created = client.post(
        "/api/v1/manuscripts", json={"title": "Private", "abstract": "A.", "keywords": []}
    ).json()

    stranger = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: stranger  # type: ignore[attr-defined]
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 403


def test_a_missing_tracking_code_is_404() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    response = client.get("/api/v1/manuscripts/UGJCS-2026-9999")
    assert response.status_code == 404


def test_the_corresponding_author_can_withdraw() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    created = client.post(
        "/api/v1/manuscripts", json={"title": "T", "abstract": "A.", "keywords": []}
    ).json()
    response = client.post(f"/api/v1/manuscripts/{created['tracking_code']}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_a_co_author_who_is_not_corresponding_cannot_withdraw() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    created = client.post(
        "/api/v1/manuscripts",
        json={
            "title": "T",
            "abstract": "A.",
            "keywords": [],
            "co_author_ids": [str(OTHER_AUTHOR)],
        },
    ).json()

    co_author = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: co_author  # type: ignore[attr-defined]
    response = client.post(f"/api/v1/manuscripts/{created['tracking_code']}/withdraw")
    assert response.status_code == 403
```

`test_manuscript_queries.py` (Step 3) uses `uow.manuscripts.store` (a plain dict) rather than a mock, because `FakeManuscriptRepository` from Task 1 already behaves the way the real repository does for the paths these tests exercise.

- [ ] **Step 8: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/api/test_manuscripts_router.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 9: Write the router**

Create `backend/src/ugjcs/api/routers/manuscripts.py`:

```python
"""An author's own view of their submissions."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from ugjcs.api.deps import get_current_actor, require
from ugjcs.api.schemas import ManuscriptOut, SubmitManuscriptRequest
from ugjcs.api.wiring import get_uow
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Action, Actor, authorize

router = APIRouter()

_NEXT_SEQUENCE = 1  # replaced by a real counter in Step 10 below


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ManuscriptOut)
async def submit_manuscript(
    body: SubmitManuscriptRequest,
    actor: Actor = Depends(require(Action.SUBMIT)),
    uow: UnitOfWork = Depends(get_uow),
) -> ManuscriptOut:
    author_ids = (UserId(actor.id), *(UserId(uid) for uid in body.co_author_ids))
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=_mint_tracking_code(),
        title=body.title,
        abstract=body.abstract,
        keywords=body.keywords,
        author_ids=author_ids,
        corresponding_author_id=UserId(actor.id),
    )
    manuscript.submit(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.add(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.get("/mine", response_model=list[ManuscriptOut])
async def list_mine(
    actor: Actor = Depends(get_current_actor), uow: UnitOfWork = Depends(get_uow)
) -> list[ManuscriptOut]:
    manuscripts = await uow.manuscripts.list_by_author(UserId(actor.id))
    return [ManuscriptOut.from_domain(m) for m in manuscripts]


@router.get("/{tracking_code}", response_model=ManuscriptOut)
async def retrieve(
    tracking_code: str,
    actor: Actor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    authorize(actor, Action.VIEW, manuscript)
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/withdraw", response_model=ManuscriptOut)
async def withdraw(
    tracking_code: str,
    actor: Actor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    authorize(actor, Action.WITHDRAW, manuscript)
    manuscript.withdraw(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


async def _get_or_404(uow: UnitOfWork, tracking_code: str) -> Manuscript:
    try:
        code = TrackingCode.parse(tracking_code)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="manuscript not found") from error
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None:
        raise HTTPException(status_code=404, detail="manuscript not found")
    return manuscript


def _mint_tracking_code() -> TrackingCode:
    """A demonstration-scale sequence source.

    Minting a globally unique, gap-tolerant tracking code under concurrent submissions is
    a database sequence's job (`SERIAL`, or a dedicated counter table with `SELECT ...
    FOR UPDATE`), not application code guessing at the next integer. That belongs to
    Plan 2's persistence layer, not this API plan, and is entered in the technical debt
    register below. For a submission volume an examiner will generate by hand, a random
    four-to-six-digit sequence collides with negligible probability and never needs a
    second attempt in this plan's tests.
    """
    from random import randint

    return TrackingCode.mint(datetime.now(UTC).year, randint(1000, 999_999))
```

Delete the `_NEXT_SEQUENCE = 1` placeholder line before running tests — it is dead and ruff's `F841`-adjacent unused-variable checks will not catch a module-level assignment, but it has no purpose and should not survive into the commit.

- [ ] **Step 10: Wire the router**

In `backend/src/ugjcs/api/app.py`, add beside the auth import:

```python
    from ugjcs.api.routers import manuscripts

    app.include_router(manuscripts.router, prefix="/api/v1/manuscripts", tags=["manuscripts"])
```

- [ ] **Step 11: Run the tests, gates, commit**

Run: `cd backend && uv run pytest tests/unit/api/test_manuscripts_router.py tests/integration/test_manuscript_queries.py -m "not integration" -v` for the unit half, then `uv run pytest tests/integration/test_manuscript_queries.py -m integration -v` for the integration half. Report both counts.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/domain/policies.py backend/src/ugjcs/application/ports.py backend/src/ugjcs/infrastructure/db/repository.py backend/src/ugjcs/api/schemas.py backend/src/ugjcs/api/routers/manuscripts.py backend/src/ugjcs/api/app.py backend/tests/unit/api/test_manuscripts_router.py backend/tests/integration/test_manuscript_queries.py
git commit -m "feat: add manuscript submission, listing, retrieval and withdrawal"
```

---

### Task 4: Reviewer assignment (persistence-only, per the scope decision)

**Files:**
- Modify: `backend/src/ugjcs/infrastructure/db/models.py`, `backend/src/ugjcs/infrastructure/db/mappers.py`, `backend/src/ugjcs/application/ports.py`
- Create: `backend/alembic/versions/0003_review_assignments.py`, `backend/src/ugjcs/infrastructure/db/assignment_repository.py`, `backend/tests/integration/test_review_assignment_repository.py`

**Interfaces:**
- Produces: `ReviewAssignmentRow`; `ReviewAssignmentRecord` (a plain dataclass, not a domain aggregate — the scope decision made explicit in code); `ReviewAssignmentRepository` protocol; `SqlAlchemyReviewAssignmentRepository`.

- [ ] **Step 1: Add the model**

Append to `backend/src/ugjcs/infrastructure/db/models.py`:

```python
class ReviewAssignmentRow(Base):
    """A record that an editor asked a reviewer to review a manuscript, and what came back.

    Deliberately not a domain aggregate: see Plan 4's scope decision. There is no
    invitation/accept/decline lifecycle, no conflict-of-interest check, and no capacity
    limit enforced anywhere in this table's existence — an editor's assignment is final
    the moment it is recorded. `status` only ever takes the values `"assigned"` and
    `"submitted"`, a deliberate subset of `ugjcs.domain.enums.AssignmentStatus` that
    skips `INVITED`/`ACCEPTED`/`DECLINED`/`EXPIRED` because nothing here offers a
    reviewer the choice those states represent.
    """

    __tablename__ = "review_assignments"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    manuscript_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("manuscripts.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(16), default="assigned")
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("manuscript_id", "reviewer_id", name="uq_review_assignments_pair"),
    )
```

No new imports are needed — `UUID`, `datetime`, and every SQLAlchemy symbol this class uses are already imported at the top of `models.py`.

- [ ] **Step 2: Write migration 0003**

Create `backend/alembic/versions/0003_review_assignments.py`, following `0001` and `0002`'s style exactly: explicit constraint names matching the naming convention, `postgresql.UUID(as_uuid=True)`, `sa.DateTime(timezone=True)`.

```python
"""Add review_assignments: an editor's record of who was asked to review what.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manuscript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["manuscript_id"],
            ["manuscripts.id"],
            name="fk_review_assignments_manuscript_id_manuscripts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_review_assignments"),
        sa.UniqueConstraint("manuscript_id", "reviewer_id", name="uq_review_assignments_pair"),
    )
    op.create_index("ix_review_assignments_manuscript_id", "review_assignments", ["manuscript_id"])
    op.create_index("ix_review_assignments_reviewer_id", "review_assignments", ["reviewer_id"])


def downgrade() -> None:
    op.drop_table("review_assignments")
```

Verify it round-trips the same way Plans 2 and 3 did:

```bash
docker run --rm -d --name ugjcs-mig3 -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=ugjcs -p 55434:5432 postgres:16
sleep 5
cd backend
export UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@localhost:55434/ugjcs
export UGJCS_JWT_SECRET=throwaway
uv run alembic upgrade head
uv run alembic downgrade 0002
uv run alembic upgrade head
docker rm -f ugjcs-mig3
```

- [ ] **Step 3: Extend the ports**

Append to `backend/src/ugjcs/application/ports.py`:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReviewAssignmentRecord:
    """A read model, not an aggregate — there is no invariant here for a domain type to
    protect. See Plan 4's scope decision for why."""

    manuscript_id: ManuscriptId
    reviewer_id: UserId
    status: str
    recommendation: str | None
    comments: str | None
    assigned_at: datetime
    submitted_at: datetime | None


class ReviewAssignmentRepository(Protocol):
    async def assign(self, manuscript_id: ManuscriptId, reviewer_id: UserId, *, occurred_at: datetime) -> None:
        """Record that a reviewer was asked. Idempotent is not guaranteed — a second call
        for the same pair raises, because `uq_review_assignments_pair` exists precisely
        to make a duplicate assignment visible rather than silently accepted."""
        ...

    async def list_for_reviewer(self, reviewer_id: UserId) -> list[ReviewAssignmentRecord]: ...

    async def list_for_manuscript(self, manuscript_id: ManuscriptId) -> list[ReviewAssignmentRecord]: ...

    async def mark_submitted(
        self,
        manuscript_id: ManuscriptId,
        reviewer_id: UserId,
        *,
        recommendation: str,
        comments: str,
        occurred_at: datetime,
    ) -> None: ...
```

Add `assignments: ReviewAssignmentRepository` as a sibling of `manuscripts` on the `UnitOfWork` protocol, and add `UserId` to the `ugjcs.domain.ids` import line at the top of `ports.py` if it is not already imported there from Task 3.

- [ ] **Step 4: Write the failing integration test**

Create `backend/tests/integration/test_review_assignment_repository.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.assignment_repository import SqlAlchemyReviewAssignmentRepository
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
REVIEWER = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


async def stored_manuscript(session: AsyncSession) -> ManuscriptId:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 51),
        title="Paper",
        abstract="Abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()
    return manuscript.id


async def test_an_assignment_is_visible_to_both_parties(session: AsyncSession) -> None:
    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    for_reviewer = await repository.list_for_reviewer(REVIEWER)
    for_manuscript = await repository.list_for_manuscript(manuscript_id)
    assert [a.manuscript_id for a in for_reviewer] == [manuscript_id]
    assert [a.reviewer_id for a in for_manuscript] == [REVIEWER]
    assert for_reviewer[0].status == "assigned"


async def test_assigning_the_same_reviewer_twice_is_rejected(session: AsyncSession) -> None:
    from sqlalchemy.exc import IntegrityError

    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
        await session.commit()


async def test_marking_submitted_records_the_review_content(session: AsyncSession) -> None:
    manuscript_id = await stored_manuscript(session)
    repository = SqlAlchemyReviewAssignmentRepository(session)
    await repository.assign(manuscript_id, REVIEWER, occurred_at=NOW)
    await session.commit()

    await repository.mark_submitted(
        manuscript_id, REVIEWER, recommendation="accept", comments="Solid work.", occurred_at=NOW
    )
    await session.commit()

    [record] = await repository.list_for_reviewer(REVIEWER)
    assert record.status == "submitted"
    assert record.recommendation == "accept"
    assert record.submitted_at == NOW
```

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && uv run pytest tests/integration/test_review_assignment_repository.py -m integration -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.infrastructure.db.assignment_repository'`

- [ ] **Step 6: Write the mapper and the repository**

Append to `backend/src/ugjcs/infrastructure/db/mappers.py`:

```python
from ugjcs.application.ports import ReviewAssignmentRecord
from ugjcs.infrastructure.db.models import ReviewAssignmentRow


def assignment_row_to_record(row: ReviewAssignmentRow) -> ReviewAssignmentRecord:
    return ReviewAssignmentRecord(
        manuscript_id=ManuscriptId(row.manuscript_id),
        reviewer_id=UserId(row.reviewer_id),
        status=row.status,
        recommendation=row.recommendation,
        comments=row.comments,
        assigned_at=row.assigned_at,
        submitted_at=row.submitted_at,
    )
```

Create `backend/src/ugjcs/infrastructure/db/assignment_repository.py`:

```python
"""PostgreSQL implementation of the review-assignment read model.

There is no aggregate here to protect an invariant, by design — see Plan 4's scope
decision. This repository is thinner than `SqlAlchemyManuscriptRepository` on purpose.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import ReviewAssignmentRecord
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.infrastructure.db.mappers import assignment_row_to_record
from ugjcs.infrastructure.db.models import ReviewAssignmentRow


class SqlAlchemyReviewAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(
        self, manuscript_id: ManuscriptId, reviewer_id: UserId, *, occurred_at: datetime
    ) -> None:
        self._session.add(
            ReviewAssignmentRow(
                id=uuid4(),
                manuscript_id=manuscript_id,
                reviewer_id=reviewer_id,
                status="assigned",
                assigned_at=occurred_at,
            )
        )
        await self._session.flush()

    async def list_for_reviewer(self, reviewer_id: UserId) -> list[ReviewAssignmentRecord]:
        result = await self._session.execute(
            select(ReviewAssignmentRow).where(ReviewAssignmentRow.reviewer_id == reviewer_id)
        )
        return [assignment_row_to_record(row) for row in result.scalars()]

    async def list_for_manuscript(
        self, manuscript_id: ManuscriptId
    ) -> list[ReviewAssignmentRecord]:
        result = await self._session.execute(
            select(ReviewAssignmentRow).where(ReviewAssignmentRow.manuscript_id == manuscript_id)
        )
        return [assignment_row_to_record(row) for row in result.scalars()]

    async def mark_submitted(
        self,
        manuscript_id: ManuscriptId,
        reviewer_id: UserId,
        *,
        recommendation: str,
        comments: str,
        occurred_at: datetime,
    ) -> None:
        result = await self._session.execute(
            select(ReviewAssignmentRow).where(
                ReviewAssignmentRow.manuscript_id == manuscript_id,
                ReviewAssignmentRow.reviewer_id == reviewer_id,
            )
        )
        row = result.scalar_one()
        row.status = "submitted"
        row.recommendation = recommendation
        row.comments = comments
        row.submitted_at = occurred_at
```

`assign` calls `await self._session.flush()` rather than leaving the insert buffered — the uniqueness violation in `test_assigning_the_same_reviewer_twice_is_rejected` must surface from the `assign()` call whose duplicate it is, not from an unrelated later `session.commit()`, or the test would be asserting the wrong thing raised it.

- [ ] **Step 7: Run the tests, gates, commit**

Run: `cd backend && uv run pytest tests/integration/test_review_assignment_repository.py -m integration -v`
Expected: PASS, 3 tests.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/infrastructure/db/models.py backend/src/ugjcs/infrastructure/db/mappers.py backend/src/ugjcs/infrastructure/db/assignment_repository.py backend/src/ugjcs/application/ports.py backend/alembic/versions/0003_review_assignments.py backend/tests/integration/test_review_assignment_repository.py
git commit -m "feat: persist reviewer assignments as a read model, not an aggregate"
```

---

### Task 5: Editorial router

**Files:**
- Modify: `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/db/repository.py`, `backend/src/ugjcs/api/schemas.py`, `backend/src/ugjcs/api/app.py`
- Create: `backend/src/ugjcs/api/routers/editorial.py`, `backend/tests/unit/api/test_editorial_router.py`, `backend/tests/integration/test_editorial_queries.py`

**Interfaces:**
- Produces: `ManuscriptRepository.list_by_status`; `GET /api/v1/editorial/queue`, `POST /api/v1/editorial/{tracking_code}/screen`, `POST /api/v1/editorial/{tracking_code}/decision`, `POST /api/v1/editorial/{tracking_code}/reviewers`.

- [ ] **Step 1: Add `list_by_status` to the port**

Append to `ManuscriptRepository` in `ports.py`:

```python
    async def list_by_status(self, status: ManuscriptStatus) -> list[Manuscript]:
        """Every manuscript currently in this state — the screening queue's source."""
        ...
```

Add `from ugjcs.domain.enums import ManuscriptStatus` to that file's imports.

- [ ] **Step 2: Write the failing integration test**

Create `backend/tests/integration/test_editorial_queries.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make(sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=f"Paper {sequence}",
        abstract="Abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


async def test_the_screening_queue_holds_only_submitted_manuscripts(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    submitted = make(61)
    submitted.submit(actor_id=AUTHOR, occurred_at=NOW)
    draft = make(62)
    await repository.add(submitted)
    await repository.add(draft)
    await session.commit()

    queue = await repository.list_by_status(S.SUBMITTED)
    assert {m.id for m in queue} == {submitted.id}
```

- [ ] **Step 3: Run to verify it fails, then implement**

Run: `cd backend && uv run pytest tests/integration/test_editorial_queries.py -m integration -v`
Expected: FAIL.

Add to `SqlAlchemyManuscriptRepository`:

```python
    async def list_by_status(self, status: S) -> list[Manuscript]:
        result = await self._session.execute(
            select(ManuscriptRow).where(ManuscriptRow.status == status.value).order_by(ManuscriptRow.id)
        )
        rows = result.scalars().all()
        return [await self._rehydrate(row) for row in rows]  # type: ignore[misc]
```

Add `from ugjcs.domain.enums import ManuscriptStatus as S` to `repository.py`'s imports.

Run: `cd backend && uv run pytest tests/integration/test_editorial_queries.py -m integration -v`
Expected: PASS.

- [ ] **Step 4: Extend the schemas and write the failing router test**

Append to `backend/src/ugjcs/api/schemas.py`:

```python
from ugjcs.domain.enums import DecisionType


class RecordDecisionRequest(BaseModel):
    decision: DecisionType
    rationale: str


class AssignReviewerRequest(BaseModel):
    reviewer_id: UUID
```

Create `backend/tests/unit/api/test_editorial_router.py`:

```python
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor
from tests.unit.api.fakes import FakeUnitOfWork, new_user_id

EDITOR = new_user_id()
AUTHOR = new_user_id()
REVIEWER = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_client(actor: Actor, *manuscripts: Manuscript) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for manuscript in manuscripts:
        uow.manuscripts.store[manuscript.id] = manuscript

    async def _uow():
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def submitted_manuscript(sequence: int = 71) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(__import__("uuid").uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    return manuscript


def test_the_queue_lists_submitted_manuscripts_for_an_editor() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, submitted_manuscript())
    response = client.get("/api/v1/editorial/queue")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_a_reviewer_may_not_see_the_screening_queue() -> None:
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, submitted_manuscript())
    response = client.get("/api/v1/editorial/queue")
    assert response.status_code == 403


def test_an_editor_can_begin_screening() -> None:
    manuscript = submitted_manuscript()
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/screen")
    assert response.status_code == 200
    assert response.json()["status"] == "under_screening"


def test_a_decision_moves_the_manuscript_to_review() -> None:
    manuscript = submitted_manuscript()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "send_to_review", "rationale": "Fits scope, well written."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_assigning_a_reviewer_records_it() -> None:
    manuscript = submitted_manuscript()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewers",
        json={"reviewer_id": str(REVIEWER)},
    )
    assert response.status_code == 204
```

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/api/test_editorial_router.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 6: Write the router**

Create `backend/src/ugjcs/api/routers/editorial.py`:

```python
"""Screening, decisions, and reviewer assignment — the editor's desk."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ugjcs.api.deps import require
from ugjcs.api.routers.manuscripts import _get_or_404
from ugjcs.api.schemas import AssignReviewerRequest, ManuscriptOut, RecordDecisionRequest
from ugjcs.api.wiring import get_uow
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import UserId
from ugjcs.domain.policies import Action, Actor

router = APIRouter()


@router.get("/queue", response_model=list[ManuscriptOut])
async def screening_queue(
    actor: Actor = Depends(require(Action.SCREEN)), uow: UnitOfWork = Depends(get_uow)
) -> list[ManuscriptOut]:
    manuscripts = await uow.manuscripts.list_by_status(S.SUBMITTED)
    return [ManuscriptOut.from_domain(m) for m in manuscripts]


@router.post("/{tracking_code}/screen", response_model=ManuscriptOut)
async def screen(
    tracking_code: str,
    actor: Actor = Depends(require(Action.SCREEN)),
    uow: UnitOfWork = Depends(get_uow),
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.begin_screening(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/decision", response_model=ManuscriptOut)
async def record_decision(
    tracking_code: str,
    body: RecordDecisionRequest,
    actor: Actor = Depends(require(Action.DECIDE)),
    uow: UnitOfWork = Depends(get_uow),
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.record_decision(
        decision=body.decision,
        actor_id=UserId(actor.id),
        rationale=body.rationale,
        occurred_at=datetime.now(UTC),
    )
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/reviewers", status_code=status.HTTP_204_NO_CONTENT)
async def assign_reviewer(
    tracking_code: str,
    body: AssignReviewerRequest,
    actor: Actor = Depends(require(Action.ASSIGN_REVIEWER)),
    uow: UnitOfWork = Depends(get_uow),
) -> None:
    manuscript = await _get_or_404(uow, tracking_code)
    if uow.assignments is None:
        raise HTTPException(status_code=500, detail="assignment repository not configured")
    await uow.assignments.assign(
        manuscript.id, UserId(body.reviewer_id), occurred_at=datetime.now(UTC)
    )
    await uow.commit()
```

`_get_or_404` is imported from `manuscripts.py` rather than duplicated — both routers need "load by tracking code or 404", and one private helper shared across two router modules in the same package is simpler than a third module that exists only to hold it. Rename it to a public name (`get_manuscript_or_404`) if this feels too coupled when implementing; report which you chose.

- [ ] **Step 7: Wire the router**

Add to `app.py`:

```python
    from ugjcs.api.routers import editorial

    app.include_router(editorial.router, prefix="/api/v1/editorial", tags=["editorial"])
```

- [ ] **Step 8: Run the tests, gates, commit**

Run: `cd backend && uv run pytest tests/unit/api/test_editorial_router.py -v` and `uv run pytest tests/integration/test_editorial_queries.py -m integration -v`. Report both counts.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/application/ports.py backend/src/ugjcs/infrastructure/db/repository.py backend/src/ugjcs/api/schemas.py backend/src/ugjcs/api/routers/editorial.py backend/src/ugjcs/api/app.py backend/tests/unit/api/test_editorial_router.py backend/tests/integration/test_editorial_queries.py
git commit -m "feat: add the screening queue, screening, decisions and reviewer assignment"
```

---

### Task 6: Reviews router — the blinding guarantee

**Files:**
- Modify: `backend/src/ugjcs/api/schemas.py`, `backend/src/ugjcs/api/app.py`, `backend/tests/unit/api/fakes.py`
- Create: `backend/src/ugjcs/api/routers/reviews.py`, `backend/tests/unit/api/test_reviews_router.py`, `backend/tests/unit/api/test_blinding_leak.py`

**Interfaces:**
- Consumes: `ugjcs.domain.blinding.blind`.
- Produces: `BlindedManuscriptOut`; `GET /api/v1/reviews/mine`, `POST /api/v1/reviews/{tracking_code}/submit`.

This is the task the prompt's non-negotiable guarantee belongs to: **a reviewer must never receive `author_ids` or `corresponding_author_id`, under any response this router produces.**

- [ ] **Step 1: Give the fake a manuscript store the assignment fake can share**

Add to `backend/tests/unit/api/fakes.py`, alongside `FakeUnitOfWork`:

```python
@dataclass
class FakeAssignmentRepository:
    assignments: list[tuple[ManuscriptId, UserId]] = field(default_factory=list)
    submitted: dict[tuple[ManuscriptId, UserId], tuple[str, str]] = field(default_factory=dict)

    async def assign(self, manuscript_id, reviewer_id, *, occurred_at) -> None:  # type: ignore[no-untyped-def]
        self.assignments.append((manuscript_id, reviewer_id))

    async def list_for_reviewer(self, reviewer_id):  # type: ignore[no-untyped-def]
        from ugjcs.application.ports import ReviewAssignmentRecord

        return [
            ReviewAssignmentRecord(
                manuscript_id=m,
                reviewer_id=r,
                status="submitted" if (m, r) in self.submitted else "assigned",
                recommendation=self.submitted.get((m, r), (None, None))[0],
                comments=self.submitted.get((m, r), (None, None))[1],
                assigned_at=NOW,
                submitted_at=NOW if (m, r) in self.submitted else None,
            )
            for m, r in self.assignments
            if r == reviewer_id
        ]

    async def list_for_manuscript(self, manuscript_id):  # type: ignore[no-untyped-def]
        return []

    async def mark_submitted(
        self, manuscript_id, reviewer_id, *, recommendation, comments, occurred_at
    ) -> None:  # type: ignore[no-untyped-def]
        self.submitted[(manuscript_id, reviewer_id)] = (recommendation, comments)
```

Change `FakeUnitOfWork.assignments`'s default from `None` to `field(default_factory=FakeAssignmentRepository)`, and add `from ugjcs.domain.ids import ManuscriptId` to the imports already present.

- [ ] **Step 2: Extend the schemas**

Append to `backend/src/ugjcs/api/schemas.py`:

```python
from dataclasses import asdict

from ugjcs.domain.blinding import BlindedManuscript


class BlindedManuscriptOut(BaseModel):
    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    version: int
    status: str

    @classmethod
    def from_domain(cls, blinded: BlindedManuscript) -> "BlindedManuscriptOut":
        return cls(**asdict(blinded))


class SubmitReviewRequest(BaseModel):
    recommendation: str
    comments: str
```

`asdict` is required, not `blinded.__dict__` — `BlindedManuscript` is `slots=True`, which has no `__dict__` at all; `dataclasses.asdict` is the supported way to get a plain mapping from a slotted dataclass.

- [ ] **Step 3: Write the failing router test**

Create `backend/tests/unit/api/test_reviews_router.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor
from tests.unit.api.fakes import FakeUnitOfWork, new_user_id

REVIEWER = new_user_id()
AUTHOR = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def under_review_manuscript() -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 81),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=__import__("ugjcs.domain.enums", fromlist=["DecisionType"]).DecisionType.SEND_TO_REVIEW,
        actor_id=AUTHOR,
        rationale="ok",
        occurred_at=NOW,
    )
    return manuscript


def make_client(manuscript: Manuscript, assign: bool = True) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    if assign:
        uow.assignments.assignments.append((manuscript.id, REVIEWER))
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))

    async def _uow():
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def test_my_assignments_lists_only_manuscripts_assigned_to_me() -> None:
    manuscript = under_review_manuscript()
    client = make_client(manuscript)
    response = client.get("/api/v1/reviews/mine")
    assert response.status_code == 200
    assert [m["tracking_code"] for m in response.json()] == [manuscript.tracking_code.value]


def test_my_assignments_is_empty_with_no_assignment() -> None:
    manuscript = under_review_manuscript()
    client = make_client(manuscript, assign=False)
    response = client.get("/api/v1/reviews/mine")
    assert response.json() == []


def test_a_non_reviewer_cannot_reach_my_assignments() -> None:
    manuscript = under_review_manuscript()
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))

    async def _uow():
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    response = TestClient(app).get("/api/v1/reviews/mine")
    assert response.status_code == 403


def test_submitting_a_review_counts_it_and_records_the_content() -> None:
    manuscript = under_review_manuscript()
    client = make_client(manuscript)
    response = client.post(
        f"/api/v1/reviews/{manuscript.tracking_code.value}/submit",
        json={"recommendation": "accept", "comments": "Solid work."},
    )
    assert response.status_code == 204
    assert manuscript.submitted_reviews == 1


def test_submitting_without_an_assignment_is_forbidden() -> None:
    manuscript = under_review_manuscript()
    client = make_client(manuscript, assign=False)
    response = client.post(
        f"/api/v1/reviews/{manuscript.tracking_code.value}/submit",
        json={"recommendation": "accept", "comments": "x"},
    )
    assert response.status_code == 403
```

- [ ] **Step 4: Write the leak test**

Create `backend/tests/unit/api/test_blinding_leak.py`:

```python
"""The one guarantee this router exists to make: a reviewer never sees who wrote what.

Every field name and value here is a distinctive sentinel — chosen so that if any
reviewer-facing response ever starts including author data, whether by a field being
added back, a `.from_domain` typo, or a future `model_dump()` that walks the wrong
object, this test fails on sight rather than needing a human to notice a real name in a
JSON blob during manual testing.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor
from tests.unit.api.fakes import FakeUnitOfWork

SENTINEL_CORRESPONDING_AUTHOR = UserId(UUID("de110000-0000-4000-8000-000000000001"))
SENTINEL_CO_AUTHOR = UserId(UUID("de110000-0000-4000-8000-000000000002"))
REVIEWER = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def leak_fixture_manuscript() -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 91),
        title="Sentinel Title Deliberately Unrelated To Authorship",
        abstract="Sentinel abstract.",
        keywords=("sentinel",),
        author_ids=(SENTINEL_CORRESPONDING_AUTHOR, SENTINEL_CO_AUTHOR),
        corresponding_author_id=SENTINEL_CORRESPONDING_AUTHOR,
    )
    manuscript.submit(actor_id=SENTINEL_CORRESPONDING_AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=SENTINEL_CORRESPONDING_AUTHOR, occurred_at=NOW)
    from ugjcs.domain.enums import DecisionType

    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW,
        actor_id=SENTINEL_CORRESPONDING_AUTHOR,
        rationale="ok",
        occurred_at=NOW,
    )
    return manuscript


def make_client(manuscript: Manuscript) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.assignments.assignments.append((manuscript.id, REVIEWER))
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))

    async def _uow():
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def _assert_no_sentinel_leaks(raw_body: str) -> None:
    for forbidden in (
        str(SENTINEL_CORRESPONDING_AUTHOR),
        str(SENTINEL_CO_AUTHOR),
        "corresponding_author_id",
        "author_ids",
    ):
        assert forbidden not in raw_body, f"reviewer response leaked {forbidden!r}"


def test_my_assignments_never_serialises_author_identifiers() -> None:
    manuscript = leak_fixture_manuscript()
    response = make_client(manuscript).get("/api/v1/reviews/mine")
    assert response.status_code == 200
    _assert_no_sentinel_leaks(response.text)


def test_the_manuscript_returned_by_my_assignments_is_the_blinded_type() -> None:
    manuscript = leak_fixture_manuscript()
    response = make_client(manuscript).get("/api/v1/reviews/mine")
    [entry] = response.json()
    assert set(entry.keys()) == {"tracking_code", "title", "abstract", "keywords", "version", "status"}
```

- [ ] **Step 5: Run to verify both new test files fail**

Run: `cd backend && uv run pytest tests/unit/api/test_reviews_router.py tests/unit/api/test_blinding_leak.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 6: Write the router**

Create `backend/src/ugjcs/api/routers/reviews.py`:

```python
"""A reviewer's queue and their submissions — blinded, structurally, every time.

`BlindedManuscriptOut.from_domain` takes a `BlindedManuscript`, never a `Manuscript`. A
handler in this file that called `ManuscriptOut.from_domain` on a manuscript instead
would be a type error the moment mypy strict looks at the `response_model`, not a review
comment — that is what "structural" means here, and it is the same guarantee
`ugjcs.domain.blinding` documents for the type itself.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ugjcs.api.deps import require
from ugjcs.api.routers.manuscripts import _get_or_404
from ugjcs.api.schemas import BlindedManuscriptOut, SubmitReviewRequest
from ugjcs.api.wiring import get_uow
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.blinding import blind
from ugjcs.domain.ids import UserId
from ugjcs.domain.policies import Action, Actor

router = APIRouter()


@router.get("/mine", response_model=list[BlindedManuscriptOut])
async def my_assignments(
    actor: Actor = Depends(require(Action.REVIEW)), uow: UnitOfWork = Depends(get_uow)
) -> list[BlindedManuscriptOut]:
    records = await uow.assignments.list_for_reviewer(UserId(actor.id))
    out: list[BlindedManuscriptOut] = []
    for record in records:
        manuscript = await uow.manuscripts.get(record.manuscript_id)
        if manuscript is not None:
            out.append(BlindedManuscriptOut.from_domain(blind(manuscript)))
    return out


@router.post("/{tracking_code}/submit", status_code=status.HTTP_204_NO_CONTENT)
async def submit_review(
    tracking_code: str,
    body: SubmitReviewRequest,
    actor: Actor = Depends(require(Action.REVIEW)),
    uow: UnitOfWork = Depends(get_uow),
) -> None:
    manuscript = await _get_or_404(uow, tracking_code)
    assigned = {
        record.manuscript_id
        for record in await uow.assignments.list_for_reviewer(UserId(actor.id))
    }
    if manuscript.id not in assigned:
        raise HTTPException(status_code=403, detail="you were not assigned this manuscript")
    manuscript.record_review(reviewer_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.assignments.mark_submitted(
        manuscript.id,
        UserId(actor.id),
        recommendation=body.recommendation,
        comments=body.comments,
        occurred_at=datetime.now(UTC),
    )
    await uow.commit()
```

- [ ] **Step 7: Wire the router**

Add to `app.py`:

```python
    from ugjcs.api.routers import reviews

    app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
```

- [ ] **Step 8: Run the tests, gates, commit**

Run: `cd backend && uv run pytest tests/unit/api/test_reviews_router.py tests/unit/api/test_blinding_leak.py -v`
Expected: PASS. If `test_the_manuscript_returned_by_my_assignments_is_the_blinded_type` fails on an extra key, the router is calling the wrong `from_domain` — fix the router, never the assertion.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/api/schemas.py backend/src/ugjcs/api/routers/reviews.py backend/src/ugjcs/api/app.py backend/tests/unit/api/fakes.py backend/tests/unit/api/test_reviews_router.py backend/tests/unit/api/test_blinding_leak.py
git commit -m "feat: add the reviewer's queue and review submission, blinded by construction"
```

---

### Task 7: Archive router (public)

**Files:**
- Modify: `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/db/repository.py`, `backend/src/ugjcs/api/schemas.py`, `backend/src/ugjcs/api/app.py`, `backend/tests/unit/api/fakes.py`
- Create: `backend/src/ugjcs/api/routers/archive.py`, `backend/tests/unit/api/test_archive_router.py`, `backend/tests/integration/test_archive_queries.py`

**Interfaces:**
- Produces: `ManuscriptRepository.list_published`, `.search_published`; `ArchivePaperOut`; `GET /api/v1/archive`, `GET /api/v1/archive/{tracking_code}`, `GET /api/v1/archive/search`.

**Reconciliation correction (against Plan 5, 2026-08-12):** the version of this task originally drafted returned `ManuscriptOut` — the authenticated, author-facing shape, carrying `author_ids`/`corresponding_author_id` as raw UUIDs — from the three public archive routes. That is wrong for a public, anonymous-caller endpoint for two independent reasons: it leaks internal account identifiers to the internet for no reason, and a UUID is useless to Plan 5's public pages, which need a byline a human or Google Scholar can read (`citation_author`, the JSON-LD `author` list, `PaperCard`'s "A. Mensah et al."). This is exactly the case where the API plan was the one that needed fixing rather than the frontend: `ArchivePaperOut` below resolves each author id to `Account.full_name` via `AccountRepository` (already an inherited interface, `uow.accounts`) and returns names, not ids. Volume/issue/DOI/PDF fields are deliberately still absent — that part of Plan 5's original assumption was checked against this plan's own "Deliberately not in this plan" list (issue composition, citation export) and Plan 5 was corrected to match instead.

- [ ] **Step 1: Extend the port**

Append to `ManuscriptRepository` in `ports.py`:

```python
    async def list_published(self) -> list[Manuscript]:
        """Every published manuscript — the public archive's contents."""
        ...

    async def search_published(self, query: str) -> list[Manuscript]:
        """Published manuscripts whose title or abstract contains `query`, case-insensitively."""
        ...
```

- [ ] **Step 2: Write the failing integration test**

Create `backend/tests/integration/test_archive_queries.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


async def _seed_published(session: AsyncSession, title: str, sequence: int) -> Manuscript:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="Abstract about scheduling.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
    )
    await repository.add(manuscript)
    await session.commit()
    return manuscript


async def test_list_published_returns_only_published_manuscripts(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    published = await _seed_published(session, "Fair Scheduling", 101)
    draft = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 102),
        title="Unpublished Draft",
        abstract="Not yet.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    await repository.add(draft)
    await session.commit()

    results = await repository.list_published()
    assert {m.id for m in results} == {published.id}


async def test_search_published_matches_the_title_case_insensitively(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    match = await _seed_published(session, "Fair Scheduling for Shared GPU Clusters", 103)
    await _seed_published(session, "Edge Caching for Campus Networks", 104)

    results = await repository.search_published("scheduling")
    assert {m.id for m in results} == {match.id}
```

- [ ] **Step 3: Run to verify it fails, then implement**

Run: `cd backend && uv run pytest tests/integration/test_archive_queries.py -m integration -v`
Expected: FAIL.

Add to `SqlAlchemyManuscriptRepository`:

```python
    async def list_published(self) -> list[Manuscript]:
        return await self.list_by_status(S.PUBLISHED)

    async def search_published(self, query: str) -> list[Manuscript]:
        result = await self._session.execute(
            select(ManuscriptRow).where(
                ManuscriptRow.status == S.PUBLISHED.value,
                (ManuscriptRow.title.ilike(f"%{query}%")) | (ManuscriptRow.abstract.ilike(f"%{query}%")),
            )
        )
        rows = result.scalars().all()
        return [await self._rehydrate(row) for row in rows]  # type: ignore[misc]
```

`list_published` reuses `list_by_status` rather than duplicating its query — it is exactly that query with the state fixed, and there is no reason for the two to drift.

Run: `cd backend && uv run pytest tests/integration/test_archive_queries.py -m integration -v`
Expected: PASS, 2 tests.

- [ ] **Step 3b: Add `ArchivePaperOut` — resolved author names, not raw ids**

Append to `backend/src/ugjcs/api/schemas.py`:

```python
from ugjcs.application.ports import AccountRepository


class ArchivePaperOut(BaseModel):
    """The public shape: a byline a human (or Google Scholar) can read, never a UUID."""

    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    author_names: list[str]
    status: str
    version: int

    @classmethod
    async def from_domain(
        cls, manuscript: Manuscript, accounts: AccountRepository
    ) -> "ArchivePaperOut":
        names: list[str] = []
        for author_id in manuscript.author_ids:
            account = await accounts.get(author_id)
            names.append(account.full_name if account is not None else "Unknown author")
        return cls(
            tracking_code=manuscript.tracking_code.value,
            title=manuscript.title,
            abstract=manuscript.abstract,
            keywords=manuscript.keywords,
            author_names=names,
            status=manuscript.status.value,
            version=manuscript.version,
        )
```

Add `from ugjcs.domain.manuscript import Manuscript` to `schemas.py`'s imports if not already present (Task 3's `ManuscriptOut.from_domain` already imports it).

- [ ] **Step 4: Write the failing router test**

Create `backend/tests/unit/api/test_archive_router.py`:

```python
from uuid import uuid4

from fastapi.testclient import TestClient

from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from tests.unit.api.fakes import FakeAccount, FakeUnitOfWork

AUTHOR = UserId(uuid4())


def published(title: str, sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="An abstract about scheduling.",
        keywords=("scheduling",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
    )


def make_client(*manuscripts: Manuscript) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for manuscript in manuscripts:
        uow.manuscripts.store[manuscript.id] = manuscript
    uow.accounts = {  # type: ignore[attr-defined]
        AUTHOR: FakeAccount(id=AUTHOR, email="a@ug.edu.gh", roles=frozenset())
    }

    async def _uow():
        yield uow

    app.dependency_overrides[get_uow] = _uow
    return TestClient(app)


def test_the_archive_requires_no_authentication() -> None:
    client = make_client(published("Fair Scheduling", 111))
    response = client.get("/api/v1/archive")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_the_archive_never_exposes_a_raw_author_id() -> None:
    client = make_client(published("Fair Scheduling", 112))
    response = client.get("/api/v1/archive")
    body = response.json()[0]
    assert "author_ids" not in body
    assert "corresponding_author_id" not in body
    assert "author_names" in body


def test_retrieving_a_published_paper_by_tracking_code() -> None:
    paper = published("Fair Scheduling", 113)
    client = make_client(paper)
    response = client.get(f"/api/v1/archive/{paper.tracking_code.value}")
    assert response.status_code == 200
    assert response.json()["title"] == "Fair Scheduling"


def test_search_finds_a_matching_paper() -> None:
    client = make_client(published("Fair Scheduling for GPUs", 114))
    response = client.get("/api/v1/archive/search", params={"q": "scheduling"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_with_no_match_returns_an_empty_list() -> None:
    client = make_client(published("Fair Scheduling for GPUs", 115))
    response = client.get("/api/v1/archive/search", params={"q": "quantum"})
    assert response.json() == []
```

`FakeUnitOfWork.accounts` does not exist yet in Task 1's fake — add `accounts: dict[UserId, FakeAccount] = field(default_factory=dict)` to `FakeUnitOfWork` in `backend/tests/unit/api/fakes.py` as part of this task, and give `FakeAccount` a trivial `async def get(self, ...)`-compatible lookup by wrapping the dict in a tiny adapter, e.g. add a `FakeAccountRepository` dataclass (`accounts: dict[UserId, FakeAccount]`, `async def get(self, user_id): return self.accounts.get(user_id)`) and change `FakeUnitOfWork.accounts`'s default to `field(default_factory=lambda: FakeAccountRepository({}))`, then have `make_client` above assign `uow.accounts = FakeAccountRepository({AUTHOR: FakeAccount(...)})` instead of a bare dict — report which shape you chose, the test only depends on `await uow.accounts.get(id)` returning a `FakeAccount | None`.

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/api/test_archive_router.py -v`
Expected: FAIL.

- [ ] **Step 6: Write the router**

Create `backend/src/ugjcs/api/routers/archive.py`:

```python
"""The public archive. No authentication anywhere in this file, by design."""

from fastapi import APIRouter, Depends, HTTPException, Query

from ugjcs.api.schemas import ArchivePaperOut
from ugjcs.api.wiring import get_uow
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.ids import TrackingCode

router = APIRouter()


@router.get("", response_model=list[ArchivePaperOut])
async def list_published(uow: UnitOfWork = Depends(get_uow)) -> list[ArchivePaperOut]:
    manuscripts = await uow.manuscripts.list_published()
    return [await ArchivePaperOut.from_domain(m, uow.accounts) for m in manuscripts]


@router.get("/search", response_model=list[ArchivePaperOut])
async def search(
    q: str = Query(..., min_length=1), uow: UnitOfWork = Depends(get_uow)
) -> list[ArchivePaperOut]:
    manuscripts = await uow.manuscripts.search_published(q)
    return [await ArchivePaperOut.from_domain(m, uow.accounts) for m in manuscripts]


@router.get("/{tracking_code}", response_model=ArchivePaperOut)
async def retrieve_published(
    tracking_code: str, uow: UnitOfWork = Depends(get_uow)
) -> ArchivePaperOut:
    try:
        code = TrackingCode.parse(tracking_code)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="paper not found") from error
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None or manuscript.status.value != "published":
        raise HTTPException(status_code=404, detail="paper not found")
    return await ArchivePaperOut.from_domain(manuscript, uow.accounts)
```

`/search` is registered before `/{tracking_code}` — FastAPI matches routes in registration order, and a literal path must be declared ahead of a path parameter that would otherwise swallow it (`GET /archive/search` would match `/{tracking_code}` with `tracking_code="search"` if the order were reversed).

`ArchivePaperOut`, not `ManuscriptOut` or `BlindedManuscriptOut`, is the response type here — publication is post-decision and authorship is public record for a published paper (so, unlike `BlindedManuscriptOut`, author information belongs in the response), but "public record" means a name, not the internal account UUID `ManuscriptOut` carries for the authenticated author-facing routes. `retrieve_published` still checks `status == "published"` explicitly rather than trusting `get_by_tracking_code` alone: an unpublished manuscript must 404 here even though the same tracking code returns real data on the authenticated `/manuscripts/{tracking_code}` route.

- [ ] **Step 7: Wire the router**

Add to `app.py`:

```python
    from ugjcs.api.routers import archive

    app.include_router(archive.router, prefix="/api/v1/archive", tags=["archive"])
```

- [ ] **Step 8: Run the tests, gates, commit**

Run: `cd backend && uv run pytest tests/unit/api/test_archive_router.py -v` and `uv run pytest tests/integration/test_archive_queries.py -m integration -v`. Report both counts.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/application/ports.py backend/src/ugjcs/infrastructure/db/repository.py backend/src/ugjcs/api/schemas.py backend/src/ugjcs/api/routers/archive.py backend/src/ugjcs/api/app.py backend/tests/unit/api/fakes.py backend/tests/unit/api/test_archive_router.py backend/tests/integration/test_archive_queries.py
git commit -m "feat: add the public archive: list, retrieve and search published papers"
```

---

### Task 8: Route authorisation audit — the mechanical guarantee

**Files:**
- Create: `backend/tests/unit/api/test_route_audit.py`
- Modify: `backend/src/ugjcs/api/app.py` (docstring only, no behaviour change)

**Interfaces:**
- Consumes: the finished route table from `create_app()`; `is_authorization_dependency` from `deps.py`.
- Produces: no production code — this task is the one from Plan 2's Task 6 playbook, proving a guarantee rather than adding a feature.

This task must run last: it inspects the complete, wired-up application, so it can only be written once every router above exists.

- [ ] **Step 1: Write the test**

Create `backend/tests/unit/api/test_route_audit.py`:

```python
"""Every non-public route must carry an authorisation dependency.

This walks the live route table rather than trusting a checklist, because a checklist
is exactly the kind of thing a future change forgets to update. If a new route is added
to `ugjcs.api` without `Depends(get_current_actor)` or `Depends(require(...))` somewhere
in its dependency tree, this test fails — that is the whole point of it.
"""

from collections.abc import Iterable

from fastapi.routing import APIRoute

from ugjcs.api.app import create_app
from ugjcs.api.deps import is_authorization_dependency

PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}
PUBLIC_PREFIXES = ("/api/v1/archive",)


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def _dependant_is_authorized(dependant: object) -> bool:
    if is_authorization_dependency(dependant.call):  # type: ignore[attr-defined]
        return True
    return any(
        _dependant_is_authorized(sub) for sub in dependant.dependencies  # type: ignore[attr-defined]
    )


def _api_routes(app: object) -> Iterable[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]  # type: ignore[attr-defined]


def test_every_non_public_route_carries_an_authorization_dependency() -> None:
    app = create_app()
    unprotected = [
        f"{sorted(route.methods)} {route.path}"
        for route in _api_routes(app)
        if not _is_public(route.path) and not _dependant_is_authorized(route.dependant)
    ]
    assert unprotected == [], f"routes with no authorization dependency: {unprotected}"


def test_the_public_allowlist_is_not_accidentally_empty() -> None:
    """A guard against the trivial way this test could pass for the wrong reason: every
    route being (mis)classified as public. If this count ever drops to zero, something
    upstream changed path prefixes and the allowlist above needs updating, not deleting."""
    app = create_app()
    protected = [route for route in _api_routes(app) if not _is_public(route.path)]
    assert len(protected) >= 8


def test_the_archive_prefix_genuinely_has_no_authorization_dependency() -> None:
    """The mirror image of the main test: prove the allowlist is not hiding a route that
    actually IS protected, which would make the main test pass without checking anything."""
    app = create_app()
    archive_routes = [
        route for route in _api_routes(app) if route.path.startswith("/api/v1/archive")
    ]
    assert archive_routes
    assert all(not _dependant_is_authorized(route.dependant) for route in archive_routes)
```

- [ ] **Step 2: Run to verify it fails first, if any route was missed**

Run: `cd backend && uv run pytest tests/unit/api/test_route_audit.py -v`

If it fails, the failure message names the exact unprotected route — go back to the router that defines it and add `Depends(get_current_actor)` or `Depends(require(...))`. Do not add the route's path to `PUBLIC_PATHS` unless it is genuinely meant to be public; that allowlist is a design decision, not an escape hatch for a forgotten dependency.

Expected once every router is correctly wired: PASS, 3 tests.

- [ ] **Step 3: Run the full suite and the gates**

Run: `cd backend && uv run pytest tests/unit -v` — report the total count.
Run: `cd backend && uv run pytest tests/integration -m integration -v` — report the total count (requires Docker).
Run: `cd backend && make check`.

- [ ] **Step 4: Manual smoke test in a browser**

```bash
cd backend
export UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@localhost:5432/ugjcs
export UGJCS_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
uv run alembic upgrade head
uv run uvicorn ugjcs.api.main:app --reload
```

Open `http://localhost:8000/docs` in a browser. Expected: Swagger UI renders, lists every route under `auth`, `manuscripts`, `editorial`, `reviews`, `archive` and `ops`, and `GET /api/v1/archive` executes successfully with no `Authorize` step. This is the concrete, browser-visible proof the top of this plan asked for — record that it worked, or report exactly what did not render.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/unit/api/test_route_audit.py
git commit -m "test: prove every non-public route carries an authorization dependency"
```

---

## Definition of done for Plan 4

- `cd backend && make check` passes: ruff, mypy strict, **three** import contracts (`domain-purity`, `layers` with `ugjcs.api` as the outermost), and the domain+application coverage gate at 85%.
- `cd backend && make integration` passes against a real PostgreSQL container, including the new manuscript queries, the assignment repository, and migration `0003`.
- `uv run uvicorn ugjcs.api.main:app` starts, and `/docs` renders and is operable in a browser with no authentication for the archive.
- An author can submit, view their own manuscript, and withdraw it; a stranger cannot view or withdraw it.
- An editor can see the screening queue, screen a submission, record a decision, and assign a reviewer.
- A reviewer's `/reviews/mine` and `/reviews/{tracking_code}/submit` responses contain **no** `author_ids` or `corresponding_author_id` field, under any circumstance the sentinel test constructs — proven by `test_blinding_leak.py`, not merely asserted in a docstring.
- Every non-public route carries an authorisation dependency, proven mechanically by walking the live route table, not by a checklist a future PR can silently violate.
- Every `DomainError` subclass reaches the client as `application/problem+json` with a status code, never a raw 500 or an unstructured error string.
- CORS accepts only origins on `UGJCS_CORS_ALLOWED_ORIGINS`; an unlisted origin receives no `Access-Control-Allow-Origin` header.

## Deliberately not in this plan

Reviewer invitation/accept/decline and conflict-of-interest exclusion (the scope decision above); issue composition and the published table of contents beyond a flat archive listing; OAI-PMH; citation export (BibTeX/RIS); similarity/plagiarism screening; reviewer-matching or recommendation of any kind; rate limiting (carried forward from Plan 3, still belongs at the API edge); account registration over HTTP (examiner accounts are seeded directly, per Plan 3's technical debt entry on `LoggingEmailSender`); pagination on list endpoints (a 48-hour demonstration corpus does not need it, and adding it later is a query parameter, not a redesign); WebSocket or SSE notifications.

## Entering the technical debt register from this plan

- **Reviewer assignment has no invitation lifecycle or conflict-of-interest check** → Cause: the domain has no `ReviewAssignment` aggregate and building one plus its policy checks did not fit alongside deployment in 48 hours → Impact: an editor can assign an author to review their own manuscript, and a reviewer cannot decline → Priority: **Critical before real reviewers** → Resolution: promote `ReviewAssignmentRecord` into a real aggregate with `AssignmentStatus` transitions and wire COI exclusion into `policies.can()`.
- **Tracking codes are minted by random sequence, not a database counter** → Cause: a real sequence source is a persistence concern out of this API plan's scope → Impact: a birthday-paradox collision is possible, though negligible at demonstration volume → Priority: Scheduled → Resolution: a `SERIAL`-backed counter table in a future persistence migration.
- **No pagination on `/manuscripts/mine`, `/editorial/queue`, `/reviews/mine`, or `/archive`** → Cause: 48-hour scope; a demonstration corpus is small → Impact: response size grows unbounded with real submission volume → Priority: Scheduled → Resolution: `limit`/`offset` query parameters plus a `Total-Count` header.
- **Review recommendation and comments are stored on `ReviewAssignmentRow`, outside the append-only hash chain** → Cause: `Manuscript.record_review` only counts; there is no domain event payload slot for free-text review content → Impact: review content itself is not tamper-evident the way the editorial event log is — only the fact that a review happened is → Priority: Scheduled → Resolution: extend `EventType.REVIEW_SUBMITTED`'s payload, or accept the split as permanent and document it in the audit model instead.
