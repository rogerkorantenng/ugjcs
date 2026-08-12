from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeDocumentStore, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_document_store, get_uow
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

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
        decision=DecisionType.SEND_TO_REVIEW,
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

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
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

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
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


def test_submitting_a_review_for_a_missing_manuscript_is_404() -> None:
    manuscript = under_review_manuscript()
    client = make_client(manuscript)
    response = client.post(
        "/api/v1/reviews/UGJCS-2026-9999/submit",
        json={"recommendation": "accept", "comments": "x"},
    )
    assert response.status_code == 404


def test_an_assigned_reviewer_gets_the_anonymised_documents_presigned_url() -> None:
    manuscript = under_review_manuscript()
    manuscript.original_document_key = "manuscripts/x/v1/original.pdf"
    manuscript.anonymised_document_key = "manuscripts/x/v1/anonymised.pdf"
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.assignments.assignments.append((manuscript.id, REVIEWER))
    documents = FakeDocumentStore()
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_document_store] = lambda: documents
    app.dependency_overrides[get_current_actor] = lambda: actor
    response = TestClient(app).get(f"/api/v1/reviews/{manuscript.tracking_code.value}/document")

    assert response.status_code == 200
    body = response.json()
    assert "anonymised.pdf" in body["url"]
    assert "original.pdf" not in body["url"]


def test_an_unassigned_reviewer_cannot_fetch_the_document() -> None:
    manuscript = under_review_manuscript()
    manuscript.anonymised_document_key = "manuscripts/x/v1/anonymised.pdf"
    client = make_client(manuscript, assign=False)
    response = client.get(f"/api/v1/reviews/{manuscript.tracking_code.value}/document")
    assert response.status_code == 403


def test_fetching_a_document_with_none_attached_is_404() -> None:
    manuscript = under_review_manuscript()
    client = make_client(manuscript)
    response = client.get(f"/api/v1/reviews/{manuscript.tracking_code.value}/document")
    assert response.status_code == 404
