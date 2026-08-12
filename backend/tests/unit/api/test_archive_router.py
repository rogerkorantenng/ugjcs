from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import (
    FakeAccount,
    FakeAccountRepository,
    FakeDocumentStore,
    FakeUnitOfWork,
)
from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_document_store, get_uow
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript

AUTHOR = UserId(uuid4())


def published(title: str, sequence: int, *, status: S = S.PUBLISHED) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="An abstract about scheduling.",
        keywords=("scheduling",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=status,
        original_document_key="manuscripts/x/v1/original.pdf",
        anonymised_document_key="manuscripts/x/v1/anonymised.pdf",
    )


def make_client(*manuscripts: Manuscript, documents: FakeDocumentStore | None = None) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for manuscript in manuscripts:
        uow.manuscripts.store[manuscript.id] = manuscript
    uow.accounts = FakeAccountRepository(
        {AUTHOR: FakeAccount(id=AUTHOR, email="a@ug.edu.gh", roles=frozenset())}
    )

    async def _uow() -> object:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_document_store] = lambda: documents or FakeDocumentStore()
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
    assert body["author_names"] == ["Test Author"]


def test_retrieving_a_published_paper_by_tracking_code() -> None:
    paper = published("Fair Scheduling", 113)
    client = make_client(paper)
    response = client.get(f"/api/v1/archive/{paper.tracking_code.value}")
    assert response.status_code == 200
    assert response.json()["title"] == "Fair Scheduling"


def test_retrieving_a_missing_tracking_code_is_404() -> None:
    client = make_client()
    response = client.get("/api/v1/archive/UGJCS-2026-9999")
    assert response.status_code == 404


def test_retrieving_a_malformed_tracking_code_is_404() -> None:
    client = make_client()
    response = client.get("/api/v1/archive/not-a-tracking-code")
    assert response.status_code == 404


def test_an_unpublished_manuscript_is_not_found_via_the_archive() -> None:
    draft = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 200),
        title="Still Under Review",
        abstract="Not public yet.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    client = make_client(draft)
    response = client.get(f"/api/v1/archive/{draft.tracking_code.value}")
    assert response.status_code == 404


def test_search_finds_a_matching_paper() -> None:
    client = make_client(published("Fair Scheduling for GPUs", 114))
    response = client.get("/api/v1/archive/search", params={"q": "scheduling"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_with_no_match_returns_an_empty_list() -> None:
    client = make_client(published("Fair Scheduling for GPUs", 115))
    response = client.get("/api/v1/archive/search", params={"q": "quantum"})
    assert response.json() == []


def test_archive_entries_report_whether_a_document_is_attached() -> None:
    client = make_client(published("Fair Scheduling", 116))
    response = client.get("/api/v1/archive")
    assert response.json()[0]["has_document"] is True


def test_a_published_papers_document_is_downloadable_without_authentication() -> None:
    """FR-18: the original (non-anonymised) PDF is served, unauthenticated."""
    paper = published("Fair Scheduling", 117)
    client = make_client(paper)
    response = client.get(f"/api/v1/archive/{paper.tracking_code.value}/document")
    assert response.status_code == 200
    body = response.json()
    assert "original.pdf" in body["url"]
    assert "anonymised.pdf" not in body["url"]


def test_a_manuscript_still_under_review_cannot_be_downloaded_via_the_archive() -> None:
    """FR-18's boundary: a manuscript anywhere in the workflow, not yet published, must
    never leak through the public download route — that would defeat double-blind review
    for a paper still in progress."""
    under_review = published("Not Yet Public", 118, status=S.UNDER_REVIEW)
    client = make_client(under_review)
    response = client.get(f"/api/v1/archive/{under_review.tracking_code.value}/document")
    assert response.status_code == 404


def test_downloading_a_missing_papers_document_is_404() -> None:
    client = make_client()
    response = client.get("/api/v1/archive/UGJCS-2026-9999/document")
    assert response.status_code == 404


def test_downloading_when_no_document_was_ever_attached_is_404() -> None:
    paper = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 119),
        title="Published Without A File",
        abstract="An abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
    )
    client = make_client(paper)
    response = client.get(f"/api/v1/archive/{paper.tracking_code.value}/document")
    assert response.status_code == 404
