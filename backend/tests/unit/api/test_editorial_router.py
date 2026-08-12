from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

EDITOR = new_user_id()
AUTHOR = new_user_id()
REVIEWER = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_client(actor: Actor, *manuscripts: Manuscript) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for manuscript in manuscripts:
        uow.manuscripts.store[manuscript.id] = manuscript

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def submitted_manuscript(sequence: int = 71) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
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


def test_screening_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor)
    response = client.post("/api/v1/editorial/UGJCS-2026-9999/screen")
    assert response.status_code == 404


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


def test_a_reviewer_cannot_record_a_decision() -> None:
    manuscript = submitted_manuscript()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "send_to_review", "rationale": "x"},
    )
    assert response.status_code == 403


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


def test_assigning_a_reviewer_to_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor)
    response = client.post(
        "/api/v1/editorial/UGJCS-2026-9999/reviewers",
        json={"reviewer_id": str(REVIEWER)},
    )
    assert response.status_code == 404
