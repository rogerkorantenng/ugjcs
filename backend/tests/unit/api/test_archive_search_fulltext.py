"""Full-text archive search at the router level: snippets on body matches, `null` on
metadata matches, and the publish-time indexing hook that feeds the column.

The fake repository's matching is substring-based; Postgres stemming, the `@@` operator
and real `ts_headline` snippets are proven against a live container in
`tests/integration/test_fulltext_search.py`. What belongs here is the wire contract and
the routing: which endpoint consults the full text, what shape the response takes, and
that publishing extracts and stores the text.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeDocumentStore, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_document_store, get_uow
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import ManuscriptId, TrackingCode, mint_issue_id
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor
from ugjcs.infrastructure.storage.demo_pdf import build_demo_pdf

AUTHOR = new_user_id()
EDITOR = new_user_id()
EIC = new_user_id()
REVIEWER = new_user_id()
NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)


def published_manuscript(
    sequence: int, *, title: str, keywords: tuple[str, ...] = ()
) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="An abstract.",
        keywords=keywords,
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
        status=S.PUBLISHED,
    )


def make_public_client(uow: FakeUnitOfWork) -> TestClient:
    app = create_app()

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    return TestClient(app)


def test_a_fulltext_match_carries_a_snippet_of_context() -> None:
    manuscript = published_manuscript(401, title="Fair Scheduling")
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.manuscripts.fulltext[manuscript.id] = (
        "Section 4 evaluates the gossip protocol under simulated packet loss across nodes."
    )
    client = make_public_client(uow)

    response = client.get("/api/v1/archive/search", params={"q": "gossip protocol"})
    assert response.status_code == 200
    [result] = response.json()
    assert result["tracking_code"] == manuscript.tracking_code.value
    assert result["snippet"] is not None
    assert "gossip protocol" in result["snippet"]


def test_a_title_match_carries_a_null_snippet() -> None:
    manuscript = published_manuscript(402, title="Fair Scheduling for GPU Clusters")
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    client = make_public_client(uow)

    response = client.get("/api/v1/archive/search", params={"q": "scheduling"})
    assert response.status_code == 200
    [result] = response.json()
    assert result["snippet"] is None


def test_a_keyword_match_is_found_with_a_null_snippet() -> None:
    manuscript = published_manuscript(
        403, title="An Unrelated Title", keywords=("mobile money", "fraud detection")
    )
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    client = make_public_client(uow)

    response = client.get("/api/v1/archive/search", params={"q": "fraud detection"})
    assert response.status_code == 200
    [result] = response.json()
    assert result["tracking_code"] == manuscript.tracking_code.value
    assert result["snippet"] is None


def test_no_match_anywhere_returns_an_empty_list() -> None:
    manuscript = published_manuscript(404, title="Fair Scheduling")
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.manuscripts.fulltext[manuscript.id] = "Nothing about the query term here."
    client = make_public_client(uow)

    response = client.get("/api/v1/archive/search", params={"q": "blockchain"})
    assert response.status_code == 200
    assert response.json() == []


# --- publish-time indexing -----------------------------------------------------------


def scheduled_manuscript_with_document(sequence: int, key: str) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Community Networks",
        abstract="An abstract.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(
        actor_id=AUTHOR,
        occurred_at=NOW,
        original_document_key=key,
        anonymised_document_key=f"anon-{key}",
    )
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    for _ in range(manuscript.minimum_reviews):
        manuscript.record_review(reviewer_id=REVIEWER, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    manuscript.schedule(issue_id=mint_issue_id(1, 1), actor_id=EIC, occurred_at=NOW)
    return manuscript


def make_publisher_client(uow: FakeUnitOfWork, documents: FakeDocumentStore) -> TestClient:
    app = create_app()

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: Actor(
        id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF})
    )
    app.dependency_overrides[get_document_store] = lambda: documents
    return TestClient(app)


def test_publishing_extracts_the_pdf_text_into_the_search_column() -> None:
    manuscript = scheduled_manuscript_with_document(405, "manuscripts/405/original.pdf")
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    documents = FakeDocumentStore()
    documents.objects["manuscripts/405/original.pdf"] = build_demo_pdf(
        tracking_code=manuscript.tracking_code.value,
        title="Community Networks",
        abstract="Mesh networking for rural connectivity.",
        keywords=("mesh", "connectivity"),
        author_name="Ama Mensah",
    )
    client = make_publisher_client(uow, documents)

    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/publish")
    assert response.status_code == 200
    stored = uow.manuscripts.fulltext[manuscript.id]
    # The demo PDF's title page and filler sections are real, extractable text.
    assert "Community Networks" in stored
    assert "Introduction" in stored
    assert "\n" not in stored  # whitespace-normalised for clean tsvector tokens


def test_a_missing_or_unreadable_document_never_blocks_publishing() -> None:
    """Indexing is best-effort: the object is absent from the store, publish must still
    succeed, and no fulltext entry appears (the entrypoint backfill's retry ground)."""
    manuscript = scheduled_manuscript_with_document(406, "manuscripts/406/original.pdf")
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    client = make_publisher_client(uow, FakeDocumentStore())

    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/publish")
    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert manuscript.id not in uow.manuscripts.fulltext
