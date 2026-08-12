"""Autouse defaults for `Settings`, so `create_app()` does not require the caller to
export `UGJCS_DATABASE_URL`/`UGJCS_JWT_SECRET` before every API unit test.

Plan 4 Task 1's `test_health.py` calls `create_app()` directly, which reads `Settings()`
through `get_settings()`. Neither field has a default — correctly, secrets must fail
loudly in production rather than silently pick something that looks like it works — so
nothing before this file ever supplied them for a test process. `test_cors.py` manages
its own `UGJCS_CORS_ALLOWED_ORIGINS` per test because it asserts on that value directly;
this fixture exists for every other test in the package that just needs `create_app()`
to construct without a `pydantic.ValidationError`.
"""

from collections.abc import Iterator

import pytest

from ugjcs.infrastructure.config import get_settings


@pytest.fixture(autouse=True)
def _default_settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("UGJCS_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("UGJCS_JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
