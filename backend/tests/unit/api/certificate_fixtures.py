"""Shared fixtures for the editorial-certificate router tests."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response
from pypdf import PdfReader

from tests.unit.api.fakes import FakeReviewContent, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain import hashchain
from ugjcs.domain.enums import DecisionType
from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

AUTHOR = new_user_id()
EDITOR = new_user_id()
REVIEWER_ONE = new_user_id()
REVIEWER_TWO = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
CONFIDENTIAL_SENTINEL = "CONFIDENTIAL-NOTE-FOR-EDITOR-ONLY"


def bare_manuscript(sequence: int, title: str = "Certified Findings") -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title=title,
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


def accepted_manuscript(sequence: int = 401) -> Manuscript:
    manuscript = bare_manuscript(sequence)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    for reviewer in (REVIEWER_ONE, REVIEWER_TWO):
        manuscript.record_review(reviewer_id=reviewer, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT,
        actor_id=EDITOR,
        rationale="Strong contribution to scheduling.",
        occurred_at=NOW,
    )
    return manuscript


def chain_of(manuscript: Manuscript) -> list[ChainedEvent]:
    chain: list[ChainedEvent] = []
    for event in manuscript.pull_events():
        chain.append(hashchain.append(chain, event))
    return chain


def add_submitted_reviews(uow: FakeUnitOfWork, manuscript: Manuscript) -> None:
    """Populate the fake assignment repo directly, the way `test_blinding_leak` does."""
    for score, reviewer in enumerate((REVIEWER_ONE, REVIEWER_TWO), start=4):
        uow.assignments.assignments.append((manuscript.id, reviewer))
        uow.assignments.submitted[(manuscript.id, reviewer)] = FakeReviewContent(
            recommendation="accept",
            originality_score=score,
            rigour_score=4,
            clarity_score=5,
            significance_score=4,
            comments_to_author=f"Well argued, says referee {score}.",
            confidential_comments_to_editor=CONFIDENTIAL_SENTINEL,
        )


def make_client(manuscript: Manuscript, actor: Actor) -> tuple[TestClient, FakeUnitOfWork]:
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.manuscripts.chains[manuscript.id] = chain_of(manuscript)

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app), uow


def fetch(client: TestClient, tracking_code: str) -> Response:
    response: Response = client.get(f"/api/v1/editorial-certificate/{tracking_code}")
    return response


def pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() for page in reader.pages)
