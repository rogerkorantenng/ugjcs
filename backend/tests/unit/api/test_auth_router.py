from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeAccount, FakeIdentityService, FakeSessionService, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_identity_service, get_session_service
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId

EMAIL = "editor@ug.edu.gh"
PASSWORD = "correct horse battery staple"


def make_client() -> tuple[TestClient, FakeSessionService, UserId]:
    app = create_app()
    editor_id = new_user_id()
    session_service = FakeSessionService(email=EMAIL, password=PASSWORD, account_id=editor_id)
    accounts = {editor_id: FakeAccount(id=editor_id, email=EMAIL, roles=frozenset({Role.EDITOR}))}
    app.dependency_overrides[get_session_service] = lambda: session_service
    app.dependency_overrides[get_identity_service] = lambda: FakeIdentityService(accounts)
    return TestClient(app), session_service, editor_id


def test_correct_credentials_return_a_token_pair() -> None:
    client, _, _ = make_client()
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_wrong_password_is_rejected_with_401() -> None:
    client, _, _ = make_client()
    response = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": "wrong password entirely"}
    )
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


def test_unknown_email_is_rejected_identically_to_a_wrong_password() -> None:
    """The response for a wrong password and an unknown email must be indistinguishable,
    or the endpoint becomes a way to enumerate registered users."""
    client, _, _ = make_client()
    wrong_password = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "not it"})
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@ug.edu.gh", "password": "not it either"},
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_refresh_returns_a_new_pair() -> None:
    client, _, _ = make_client()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "refresh-token-abc"})
    assert response.status_code == 200
    assert response.json()["refresh_token"] == "refresh-token-rotated"


def test_refresh_with_an_unknown_token_is_401() -> None:
    client, _, _ = make_client()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "no-such-token"})
    assert response.status_code == 401


def test_logout_succeeds_with_no_body() -> None:
    client, _, _ = make_client()
    response = client.post("/api/v1/auth/logout", json={"refresh_token": "refresh-token-abc"})
    assert response.status_code == 204


def test_me_requires_a_bearer_token() -> None:
    client, _, _ = make_client()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_the_authenticated_actor() -> None:
    client, _, editor_id = make_client()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {editor_id}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(editor_id)
    assert body["roles"] == ["editor"]


def test_me_rejects_a_malformed_authorization_header() -> None:
    client, _, editor_id = make_client()
    response = client.get("/api/v1/auth/me", headers={"Authorization": str(editor_id)})
    assert response.status_code == 401
