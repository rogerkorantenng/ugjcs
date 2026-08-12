"""The one guarantee this router exists to make: a reviewer never sees who wrote what.

Every field name and value here is a distinctive sentinel — chosen so that if any
reviewer-facing response ever starts including author data, whether by a field being
added back, a `.from_domain` typo, or a future `model_dump()` that walks the wrong
object, this test fails on sight rather than needing a human to notice a real name in a
JSON blob during manual testing.

Every reviewer-facing endpoint this router exposes (`GET /reviews/mine` and the response
shape reused by `POST /reviews/{tracking_code}/submit`, which returns no body but shares
the same `BlindedManuscriptOut` construction path via `my_assignments`) is exercised here
against a fixture whose author identifiers are the sentinels below.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeUnitOfWork
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

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

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
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
    assert set(entry.keys()) == {
        "tracking_code",
        "title",
        "abstract",
        "keywords",
        "version",
        "status",
    }


def test_submitting_a_review_never_echoes_author_identifiers_either() -> None:
    """The submit endpoint returns no body, but this closes the loop: if a future change
    gave it a response body, it must be checked the same way `/mine` is, not assumed safe
    because it happens to be empty today."""
    manuscript = leak_fixture_manuscript()
    response = make_client(manuscript).post(
        f"/api/v1/reviews/{manuscript.tracking_code.value}/submit",
        json={"recommendation": "accept", "comments": "Solid work."},
    )
    assert response.status_code == 204
    _assert_no_sentinel_leaks(response.text)
