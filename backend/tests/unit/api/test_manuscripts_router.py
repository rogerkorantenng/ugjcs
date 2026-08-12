from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response

from tests.unit.api.fakes import FakeDocumentStore, FakeUnitOfWork, minimal_pdf_bytes, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_document_store, get_uow
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

AUTHOR = new_user_id()
OTHER_AUTHOR = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)

PDF_BYTES = minimal_pdf_bytes()
NOT_A_PDF = b"this is definitely not a PDF file, just plain text pretending to be one"


def make_client(actor: Actor) -> tuple[TestClient, FakeUnitOfWork, FakeDocumentStore]:
    app = create_app()
    uow = FakeUnitOfWork()
    documents = FakeDocumentStore()

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_document_store] = lambda: documents
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app), uow, documents


def _submit(
    client: TestClient,
    *,
    title: str = "Sparse Retrieval",
    abstract: str = "An abstract.",
    keywords: str = "ir",
    co_author_ids: str = "",
    file_bytes: bytes = PDF_BYTES,
) -> Response:
    response: Response = client.post(
        "/api/v1/manuscripts",
        data={
            "title": title,
            "abstract": abstract,
            "keywords": keywords,
            "co_author_ids": co_author_ids,
        },
        files={"file": ("manuscript.pdf", file_bytes, "application/pdf")},
    )
    return response


def test_an_author_can_submit_a_manuscript_with_a_pdf() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow, documents = make_client(actor)
    response = _submit(client)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "submitted"
    assert body["author_ids"] == [str(AUTHOR)]
    assert body["corresponding_author_id"] == str(AUTHOR)
    assert body["has_document"] is True
    assert len(uow.manuscripts.store) == 1
    [manuscript] = uow.manuscripts.store.values()
    assert manuscript.original_document_key is not None
    assert manuscript.anonymised_document_key is not None
    assert documents.objects[manuscript.original_document_key] == PDF_BYTES
    # The original carries the sentinel author name; the "anonymised" copy must not.
    assert b"Sentinel Author Name" in documents.objects[manuscript.original_document_key]
    assert b"Sentinel Author Name" not in documents.objects[manuscript.anonymised_document_key]


def test_a_non_pdf_upload_is_rejected_with_415() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow, _ = make_client(actor)
    response = _submit(client, file_bytes=NOT_A_PDF)
    assert response.status_code == 415
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "UnsupportedDocumentTypeError"
    assert len(uow.manuscripts.store) == 0


def test_an_oversized_upload_is_rejected_with_413() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    oversized = b"%PDF-1.4" + b"0" * (10 * 1024 * 1024 + 1)
    response = _submit(client, file_bytes=oversized)
    assert response.status_code == 413
    assert response.json()["title"] == "DocumentTooLargeError"


def test_a_reviewer_without_the_author_role_cannot_submit() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.REVIEWER}))
    client, _, _ = make_client(actor)
    response = _submit(client, title="X", abstract="Y", keywords="")
    assert response.status_code == 403


def test_mine_lists_only_the_callers_manuscripts() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    _submit(client, title="Mine")
    response = client.get("/api/v1/manuscripts/mine")
    assert response.status_code == 200
    assert [m["title"] for m in response.json()] == ["Mine"]


def test_retrieving_someone_elses_manuscript_is_forbidden() -> None:
    owner = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(owner)
    created = _submit(client, title="Private").json()

    stranger = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: stranger  # type: ignore[attr-defined]
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 403


def test_the_owner_can_retrieve_their_own_manuscript() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    created = _submit(client, title="Mine").json()
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Mine"


def test_an_editor_can_retrieve_any_manuscript() -> None:
    author = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(author)
    created = _submit(client, title="Editor Visible").json()

    editor = Actor(id=new_user_id(), roles=frozenset({Role.EDITOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: editor  # type: ignore[attr-defined]
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 200


def test_a_missing_tracking_code_is_404() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    response = client.get("/api/v1/manuscripts/UGJCS-2026-9999")
    assert response.status_code == 404


def test_a_malformed_tracking_code_is_404_not_a_500() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    response = client.get("/api/v1/manuscripts/not-a-tracking-code")
    assert response.status_code == 404


def test_the_corresponding_author_can_withdraw() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    created = _submit(client, title="T").json()
    response = client.post(f"/api/v1/manuscripts/{created['tracking_code']}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_a_co_author_who_is_not_corresponding_cannot_withdraw() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    created = _submit(client, title="T", co_author_ids=str(OTHER_AUTHOR)).json()

    co_author = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: co_author  # type: ignore[attr-defined]
    response = client.post(f"/api/v1/manuscripts/{created['tracking_code']}/withdraw")
    assert response.status_code == 403


def test_withdrawing_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    response = client.post("/api/v1/manuscripts/UGJCS-2026-9999/withdraw")
    assert response.status_code == 404


def _revision_requested_manuscript() -> Manuscript:
    from ugjcs.domain.enums import DecisionType

    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 501),
        title="Under Revision",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION,
        actor_id=AUTHOR,
        rationale="Needs work",
        occurred_at=NOW,
    )
    return manuscript


def test_the_corresponding_author_can_resubmit_with_a_revised_file() -> None:
    manuscript = _revision_requested_manuscript()
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow, documents = make_client(actor)
    uow.manuscripts.store[manuscript.id] = manuscript

    response = client.post(
        f"/api/v1/manuscripts/{manuscript.tracking_code.value}/resubmit",
        data={"response_to_reviewers": "Addressed reviewer 2's concerns about the baseline."},
        files={"file": ("revised.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resubmitted"
    assert body["version"] == 2
    assert manuscript.original_document_key is not None
    assert documents.objects[manuscript.original_document_key] == PDF_BYTES


def test_a_stranger_cannot_resubmit_someone_elses_manuscript() -> None:
    manuscript = _revision_requested_manuscript()
    stranger = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow, _ = make_client(stranger)
    uow.manuscripts.store[manuscript.id] = manuscript

    response = client.post(
        f"/api/v1/manuscripts/{manuscript.tracking_code.value}/resubmit",
        data={"response_to_reviewers": "x"},
        files={"file": ("revised.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 403


def test_resubmitting_a_non_pdf_is_rejected() -> None:
    manuscript = _revision_requested_manuscript()
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow, _ = make_client(actor)
    uow.manuscripts.store[manuscript.id] = manuscript

    response = client.post(
        f"/api/v1/manuscripts/{manuscript.tracking_code.value}/resubmit",
        data={"response_to_reviewers": "x"},
        files={"file": ("revised.pdf", NOT_A_PDF, "application/pdf")},
    )
    assert response.status_code == 415
    assert manuscript.status.value == "revision_requested"


def test_the_author_can_fetch_a_presigned_url_for_the_original() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    created = _submit(client).json()
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}/document")
    assert response.status_code == 200
    body = response.json()
    assert "original.pdf" in body["url"]
    assert body["expires_in_seconds"] == 300


def test_an_author_may_not_request_the_anonymised_variant() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(actor)
    created = _submit(client).json()
    response = client.get(
        f"/api/v1/manuscripts/{created['tracking_code']}/document?variant=anonymised"
    )
    assert response.status_code == 403


def test_an_editor_can_fetch_either_variant() -> None:
    author = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _, _ = make_client(author)
    created = _submit(client).json()

    editor = Actor(id=new_user_id(), roles=frozenset({Role.EDITOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: editor  # type: ignore[attr-defined]
    original = client.get(f"/api/v1/manuscripts/{created['tracking_code']}/document")
    anonymised = client.get(
        f"/api/v1/manuscripts/{created['tracking_code']}/document?variant=anonymised"
    )
    assert original.status_code == 200
    assert "original.pdf" in original.json()["url"]
    assert anonymised.status_code == 200
    assert "anonymised.pdf" in anonymised.json()["url"]


def test_fetching_a_document_for_a_manuscript_with_none_attached_is_404() -> None:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 502),
        title="No Document",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow, _ = make_client(actor)
    uow.manuscripts.store[manuscript.id] = manuscript
    response = client.get(f"/api/v1/manuscripts/{manuscript.tracking_code.value}/document")
    assert response.status_code == 404
