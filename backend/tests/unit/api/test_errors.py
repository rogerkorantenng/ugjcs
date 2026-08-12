from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from ugjcs.api.errors import register_exception_handlers
from ugjcs.domain.errors import (
    AuthorizationDeniedError,
    GuardViolationError,
    IllegalTransitionError,
)


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
