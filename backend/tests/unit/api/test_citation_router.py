"""The DOI-shaped identifier and the citation export endpoint."""

from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeAccount, FakeAccountRepository, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript

AUTHOR = new_user_id()
CO_AUTHOR = new_user_id()


def published_paper(sequence: int = 123, *, status: S = S.PUBLISHED) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Fair Scheduling for GPUs",
        abstract="An abstract.",
        keywords=("scheduling",),
        author_ids=(AUTHOR, CO_AUTHOR),
        corresponding_author_id=AUTHOR,
        status=status,
    )


def make_client(manuscript: Manuscript) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.accounts = FakeAccountRepository(
        {
            AUTHOR: FakeAccount(
                id=AUTHOR, email="ama@ug.edu.gh", roles=frozenset(), full_name="Ama Serwaa"
            ),
            CO_AUTHOR: FakeAccount(
                id=CO_AUTHOR, email="kofi@ug.edu.gh", roles=frozenset(), full_name="Kofi Mensah"
            ),
        }
    )

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    return TestClient(app)


def test_archive_entries_carry_the_doi_shaped_identifier() -> None:
    paper = published_paper()
    client = make_client(paper)
    response = client.get(f"/api/v1/archive/{paper.tracking_code.value}")
    assert response.status_code == 200
    assert response.json()["doi"] == "10.55555/sdj.2026.0123"


def test_a_bibtex_citation_is_well_formed_plain_text() -> None:
    paper = published_paper()
    client = make_client(paper)
    response = client.get(
        f"/api/v1/archive/{paper.tracking_code.value}/citation", params={"format": "bibtex"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert text.startswith("@article{sdj_2026_0123,")
    assert "author  = {Ama Serwaa and Kofi Mensah}" in text
    assert "title   = {Fair Scheduling for GPUs}" in text
    assert "journal = {Science and Development Journal}" in text
    assert "year    = {2026}" in text
    assert "doi     = {10.55555/sdj.2026.0123}" in text
    assert "url     = {https://ugjcs-frontend.vercel.app/papers/SDJ-2026-0123}" in text
    assert text.rstrip().endswith("}")


def test_a_ris_citation_is_a_jour_record_with_one_au_tag_per_author() -> None:
    paper = published_paper(124)
    client = make_client(paper)
    response = client.get(
        f"/api/v1/archive/{paper.tracking_code.value}/citation", params={"format": "ris"}
    )
    assert response.status_code == 200
    lines = response.text.splitlines()
    assert lines[0] == "TY  - JOUR"
    assert "AU  - Ama Serwaa" in lines
    assert "AU  - Kofi Mensah" in lines
    assert "JO  - Science and Development Journal" in lines
    assert "PY  - 2026" in lines
    assert "DO  - 10.55555/sdj.2026.0124" in lines
    assert lines[-1] == "ER  -"


def test_an_unknown_citation_format_is_422() -> None:
    paper = published_paper(125)
    client = make_client(paper)
    response = client.get(
        f"/api/v1/archive/{paper.tracking_code.value}/citation", params={"format": "endnote"}
    )
    assert response.status_code == 422


def test_a_missing_citation_format_is_422() -> None:
    paper = published_paper(126)
    client = make_client(paper)
    response = client.get(f"/api/v1/archive/{paper.tracking_code.value}/citation")
    assert response.status_code == 422


def test_a_citation_for_an_unpublished_manuscript_is_404() -> None:
    paper = published_paper(127, status=S.UNDER_REVIEW)
    client = make_client(paper)
    response = client.get(
        f"/api/v1/archive/{paper.tracking_code.value}/citation", params={"format": "bibtex"}
    )
    assert response.status_code == 404
