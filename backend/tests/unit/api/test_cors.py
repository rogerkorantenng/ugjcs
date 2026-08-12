import pytest
from fastapi.testclient import TestClient

from ugjcs.infrastructure.config import get_settings


def test_an_allowed_origin_receives_cors_headers() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("UGJCS_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("UGJCS_JWT_SECRET", "test-secret")
    monkeypatch.setenv("UGJCS_CORS_ALLOWED_ORIGINS", "https://ugjcs.example.edu")
    get_settings.cache_clear()

    from ugjcs.api.app import create_app

    client = TestClient(create_app())
    response = client.get("/health", headers={"Origin": "https://ugjcs.example.edu"})
    assert response.headers["access-control-allow-origin"] == "https://ugjcs.example.edu"
    monkeypatch.undo()
    get_settings.cache_clear()


def test_an_origin_not_on_the_allowlist_receives_no_cors_header() -> None:
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
