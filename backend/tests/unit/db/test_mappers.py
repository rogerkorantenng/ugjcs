from datetime import UTC, datetime
from uuid import uuid4

from ugjcs.domain.enums import EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.hashchain import GENESIS_HASH, append
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.mappers import (
    event_to_row,
    row_to_chained,
    to_domain,
    to_row,
)

AUTHOR = UserId(uuid4())
COAUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 12),
        title="Sparse Retrieval for Low-Resource Languages",
        abstract="A sparse retrieval baseline for Akan and Ewe corpora.",
        keywords=("information retrieval", "low-resource"),
        author_ids=(AUTHOR, COAUTHOR),
        corresponding_author_id=AUTHOR,
    )


def test_row_carries_every_scalar_field() -> None:
    manuscript = make_manuscript()
    row = to_row(manuscript)
    assert row.id == manuscript.id
    assert row.tracking_code == "SDJ-2026-0012"
    assert row.title == manuscript.title
    assert row.abstract == manuscript.abstract
    assert row.keywords == ["information retrieval", "low-resource"]
    assert row.status == "draft"
    assert row.version == 1
    assert row.corresponding_author_id == AUTHOR


def test_row_preserves_author_order() -> None:
    row = to_row(make_manuscript())
    assert [author.author_id for author in row.authors] == [AUTHOR, COAUTHOR]
    assert [author.position for author in row.authors] == [0, 1]


def test_round_trip_restores_the_aggregate() -> None:
    original = make_manuscript()
    restored = to_domain(to_row(original), last_sequence=0)
    assert restored.id == original.id
    assert restored.tracking_code == original.tracking_code
    assert restored.title == original.title
    assert restored.abstract == original.abstract
    assert restored.author_ids == original.author_ids
    assert restored.corresponding_author_id == original.corresponding_author_id
    assert restored.status is original.status
    assert restored.keywords == original.keywords
    assert restored.version == original.version
    assert restored.minimum_reviews == original.minimum_reviews
    assert restored.submitted_reviews == original.submitted_reviews
    assert restored.issue_id is None


def test_round_trip_restores_non_default_scalars() -> None:
    """The defaults happen to match the dataclass's, so only varied values prove the mapping."""
    original = make_manuscript()
    original.version = 3
    original.minimum_reviews = 4
    original.submitted_reviews = 2
    restored = to_domain(to_row(original), last_sequence=0)
    assert restored.version == 3
    assert restored.minimum_reviews == 4
    assert restored.submitted_reviews == 2


def test_round_trip_restores_a_populated_issue_id() -> None:
    """The `issue_id is not None` arm is otherwise never executed by any test."""
    original = make_manuscript()
    issue_id = IssueId(uuid4())
    original.issue_id = issue_id
    restored = to_domain(to_row(original), last_sequence=0)
    assert restored.issue_id == issue_id


def test_round_trip_restores_document_keys() -> None:
    original = make_manuscript()
    original.original_document_key = f"manuscripts/{original.id}/v1/original.pdf"
    original.anonymised_document_key = f"manuscripts/{original.id}/v1/anonymised.pdf"
    restored = to_domain(to_row(original), last_sequence=0)
    assert restored.original_document_key == original.original_document_key
    assert restored.anonymised_document_key == original.anonymised_document_key


def test_round_trip_with_no_document_attached_keeps_the_keys_none() -> None:
    restored = to_domain(to_row(make_manuscript()), last_sequence=0)
    assert restored.original_document_key is None
    assert restored.anonymised_document_key is None


def test_rehydration_seeds_the_sequence_counter() -> None:
    """Without this, the next event collides with one already in the chain."""
    restored = to_domain(to_row(make_manuscript()), last_sequence=7)
    restored.status = S.SUBMITTED
    event = restored.begin_screening(actor_id=UserId(uuid4()), occurred_at=NOW)
    assert event.sequence == 8


def test_a_fresh_aggregate_starts_its_sequence_at_one() -> None:
    restored = to_domain(to_row(make_manuscript()), last_sequence=0)
    event = restored.submit(actor_id=AUTHOR, occurred_at=NOW)
    assert event.sequence == 1


def test_event_round_trip_preserves_the_hash() -> None:
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    chained = append([], manuscript.pending_events[0])
    row = event_to_row(chained, manuscript.id)
    assert row.previous_hash == GENESIS_HASH
    assert row.event_hash == chained.event_hash
    assert row.event_type == EventType.MANUSCRIPT_SUBMITTED.value
    assert row_to_chained(row) == chained


def test_event_row_keeps_the_timestamp_timezone_aware() -> None:
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    row = event_to_row(append([], manuscript.pending_events[0]), manuscript.id)
    assert row.occurred_at.tzinfo is not None
    assert row_to_chained(row).event.occurred_at == NOW
