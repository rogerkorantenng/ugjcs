"""The anonymisation preflight report on submission and resubmission responses."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response

from tests.unit.api.fakes import (
    FakeAccount,
    FakeDocumentStore,
    FakeUnitOfWork,
    minimal_pdf_bytes,
    new_user_id,
)
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_document_store, get_uow
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor
from ugjcs.infrastructure.storage.demo_pdf import build_demo_pdf

AUTHOR = new_user_id()
AUTHOR_NAME = "Ama Serwaa"
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_client() -> tuple[TestClient, FakeUnitOfWork]:
    app = create_app()
    uow = FakeUnitOfWork()
    uow.accounts.accounts[AUTHOR] = FakeAccount(
        id=AUTHOR, email="ama@ug.edu.gh", roles=frozenset({Role.AUTHOR}), full_name=AUTHOR_NAME
    )

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_document_store] = lambda: FakeDocumentStore()
    app.dependency_overrides[get_current_actor] = lambda: Actor(
        id=AUTHOR, roles=frozenset({Role.AUTHOR})
    )
    return TestClient(app), uow


def submit(client: TestClient, file_bytes: bytes) -> Response:
    response: Response = client.post(
        "/api/v1/manuscripts",
        data={"title": "T", "abstract": "A.", "keywords": "", "co_author_ids": ""},
        files={"file": ("manuscript.pdf", file_bytes, "application/pdf")},
    )
    return response


def pdf_naming_author_in_body() -> bytes:
    """A parseable PDF whose *visible text* mentions the author — TD-05's exact gap."""
    return build_demo_pdf(
        tracking_code="SDJ-2026-0777",
        title="Named In Body",
        abstract=f"A study conducted by {AUTHOR_NAME} on fair scheduling.",
        keywords=("scheduling",),
        author_name=AUTHOR_NAME,
    )


def test_the_submission_response_reports_the_stripped_docinfo_keys() -> None:
    client, _ = make_client()
    response = submit(client, minimal_pdf_bytes())
    assert response.status_code == 201
    report = response.json()["anonymisation_report"]
    assert "/Author" in report["removed_docinfo_keys"]
    assert "/Title" in report["removed_docinfo_keys"]
    assert report["xmp_removed"] is False
    assert report["author_names_in_body"] == []


def test_the_response_still_carries_every_manuscript_out_field() -> None:
    client, _ = make_client()
    body = submit(client, minimal_pdf_bytes()).json()
    for field in ("tracking_code", "title", "status", "version", "has_document", "author_ids"):
        assert field in body
    assert body["status"] == "submitted"


def test_an_author_name_in_the_body_text_is_flagged() -> None:
    client, _ = make_client()
    response = submit(client, pdf_naming_author_in_body())
    assert response.status_code == 201
    report = response.json()["anonymisation_report"]
    assert report["author_names_in_body"] == [AUTHOR_NAME]


def test_a_resubmission_also_carries_the_preflight_report() -> None:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 601),
        title="Under Revision",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION, actor_id=AUTHOR, rationale="r", occurred_at=NOW
    )
    client, uow = make_client()
    uow.manuscripts.store[manuscript.id] = manuscript
    response = client.post(
        f"/api/v1/manuscripts/{manuscript.tracking_code.value}/resubmit",
        data={"response_to_reviewers": "Addressed."},
        files={"file": ("revised.pdf", pdf_naming_author_in_body(), "application/pdf")},
    )
    assert response.status_code == 200
    report = response.json()["anonymisation_report"]
    assert "/Author" in report["removed_docinfo_keys"]
    assert report["author_names_in_body"] == [AUTHOR_NAME]
