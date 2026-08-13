"""The public provenance endpoint: chain verification without payload exposure."""

import dataclasses
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.wiring import get_uow
from ugjcs.domain import hashchain
from ugjcs.domain.enums import DecisionType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript

AUTHOR = new_user_id()
EDITOR = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
RATIONALE_SENTINEL = "SENTINEL-RATIONALE-MUST-NEVER-LEAK"


def manuscript_with_history(sequence: int = 301) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="Provable History",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.DESK_REJECT,
        actor_id=EDITOR,
        rationale=RATIONALE_SENTINEL,
        occurred_at=NOW,
    )
    return manuscript


def chain_of(manuscript: Manuscript) -> list[ChainedEvent]:
    chain: list[ChainedEvent] = []
    for event in manuscript.pull_events():
        chain.append(hashchain.append(chain, event))
    return chain


def make_client(
    manuscript: Manuscript, chain: list[ChainedEvent], *, status: S = S.PUBLISHED
) -> TestClient:
    manuscript.status = status
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.manuscripts.chains[manuscript.id] = chain

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    return TestClient(app)


def test_an_intact_chain_verifies_and_reports_its_head_hash() -> None:
    manuscript = manuscript_with_history()
    chain = chain_of(manuscript)
    client = make_client(manuscript, chain)
    response = client.get(f"/api/v1/archive/{manuscript.tracking_code.value}/provenance")
    assert response.status_code == 200
    body = response.json()
    assert body["intact"] is True
    assert body["tracking_code"] == manuscript.tracking_code.value
    assert body["head_hash"] == chain[-1].event_hash
    assert [e["sequence"] for e in body["events"]] == [1, 2, 3]
    assert body["events"][0]["event_type"] == "manuscript_submitted"
    assert body["events"][0]["hash_prefix"] == chain[0].event_hash[:8]
    assert len(body["events"][0]["hash_prefix"]) == 8


def test_a_tampered_interior_event_is_reported_as_not_intact() -> None:
    manuscript = manuscript_with_history(302)
    chain = chain_of(manuscript)
    forged_event = dataclasses.replace(chain[1].event, payload={"status": "published"})
    chain[1] = dataclasses.replace(chain[1], event=forged_event)
    client = make_client(manuscript, chain)
    response = client.get(f"/api/v1/archive/{manuscript.tracking_code.value}/provenance")
    assert response.status_code == 200
    assert response.json()["intact"] is False


def test_event_payloads_and_actor_ids_are_never_exposed() -> None:
    """Payloads can reference reviewer ids and decision rationales; the public
    projection must carry event type, time and hash prefix only."""
    manuscript = manuscript_with_history(303)
    client = make_client(manuscript, chain_of(manuscript))
    response = client.get(f"/api/v1/archive/{manuscript.tracking_code.value}/provenance")
    assert RATIONALE_SENTINEL not in response.text
    assert str(EDITOR) not in response.text
    assert str(AUTHOR) not in response.text
    for event in response.json()["events"]:
        assert set(event.keys()) == {"sequence", "event_type", "occurred_at", "hash_prefix"}


def test_provenance_for_an_unpublished_manuscript_is_404() -> None:
    manuscript = manuscript_with_history(304)
    client = make_client(manuscript, chain_of(manuscript), status=S.UNDER_SCREENING)
    response = client.get(f"/api/v1/archive/{manuscript.tracking_code.value}/provenance")
    assert response.status_code == 404


def test_provenance_for_a_missing_tracking_code_is_404() -> None:
    manuscript = manuscript_with_history(305)
    client = make_client(manuscript, chain_of(manuscript))
    response = client.get("/api/v1/archive/SDJ-2026-9999/provenance")
    assert response.status_code == 404
