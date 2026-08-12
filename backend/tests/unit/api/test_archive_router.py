from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeAccount, FakeAccountRepository, FakeUnitOfWork
from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript

AUTHOR = UserId(uuid4())


def published(title: str, sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="An abstract about scheduling.",
        keywords=("scheduling",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
    )


def make_client(*manuscripts: Manuscript) -> TestClient:
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
