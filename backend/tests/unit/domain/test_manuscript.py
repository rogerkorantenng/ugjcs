from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import DecisionType, EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import GuardViolationError, IllegalTransitionError
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript

AUTHOR = UserId(uuid4())
EDITOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 11, 0, tzinfo=UTC)


def status_of(manuscript: Manuscript) -> S:
    """Read status through a call so mypy cannot narrow the attribute in place.

    Asserting `manuscript.status is S.X` inline narrows the attribute to that literal for
    the rest of the function. mypy cannot see that a later method call mutates it, so a
    second assertion against a different status is rejected as a non-overlapping identity
    check. Reading through a call yields a fresh `S` each time.
    """
    return manuscript.status


def draft() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 1),
        title="Adinkra Symbol Classification with Vision Transformers",
        abstract="We evaluate transformer architectures on Adinkra symbol recognition.",
        keywords=("computer vision", "cultural heritage"),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


def submitted() -> Manuscript:
    manuscript = draft()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    return manuscript


def under_review() -> Manuscript:
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW,
        actor_id=EDITOR,
        rationale="In scope",
        occurred_at=NOW,
    )
    return manuscript


def test_new_manuscript_starts_in_draft() -> None:
    assert draft().status is S.DRAFT


def test_submit_moves_to_submitted_and_emits_an_event() -> None:
    manuscript = draft()
    event = manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    assert manuscript.status is S.SUBMITTED
    assert event.event_type is EventType.MANUSCRIPT_SUBMITTED
    assert event.sequence == 1


def test_events_are_sequenced_consecutively() -> None:
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    assert [event.sequence for event in manuscript.pending_events] == [1, 2]


def test_pull_events_drains_the_buffer() -> None:
    manuscript = submitted()
    assert len(manuscript.pull_events()) == 1
    assert manuscript.pending_events == ()


def test_cannot_submit_twice() -> None:
    manuscript = submitted()
    with pytest.raises(IllegalTransitionError):
        manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)


def test_desk_rejection_requires_no_reviews() -> None:
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.DESK_REJECT,
        actor_id=EDITOR,
        rationale="Out of scope",
        occurred_at=NOW,
    )
    assert manuscript.status is S.DESK_REJECTED


def test_desk_rejection_is_illegal_once_under_review() -> None:
    manuscript = under_review()
    with pytest.raises(IllegalTransitionError):
        manuscript.record_decision(
            decision=DecisionType.DESK_REJECT,
            actor_id=EDITOR,
            rationale="Too late",
            occurred_at=NOW,
        )


def test_acceptance_requires_the_minimum_review_count() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    with pytest.raises(GuardViolationError, match="requires 2 reviews, has 1"):
        manuscript.record_decision(
            decision=DecisionType.ACCEPT,
            actor_id=EDITOR,
            rationale="Strong",
            occurred_at=NOW,
        )


def test_review_quorum_closes_the_review_round() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    assert status_of(manuscript) is S.UNDER_REVIEW
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    assert status_of(manuscript) is S.REVIEWS_COMPLETE


def test_acceptance_succeeds_once_the_minimum_is_met() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT,
        actor_id=EDITOR,
        rationale="Strong contribution",
        occurred_at=NOW,
    )
    assert manuscript.status is S.ACCEPTED


def test_only_the_corresponding_author_may_resubmit() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION,
        actor_id=EDITOR,
        rationale="Clarify method",
        occurred_at=NOW,
    )
    with pytest.raises(GuardViolationError, match="corresponding author"):
        manuscript.resubmit(actor_id=UserId(uuid4()), occurred_at=NOW)


def test_resubmission_increments_the_version_and_resets_review_count() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION,
        actor_id=EDITOR,
        rationale="Clarify method",
        occurred_at=NOW,
    )
    manuscript.resubmit(actor_id=AUTHOR, occurred_at=NOW)
    assert manuscript.version == 2
    assert manuscript.submitted_reviews == 0


def test_publication_requires_an_issue() -> None:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT,
        actor_id=EDITOR,
        rationale="Strong",
        occurred_at=NOW,
    )
    with pytest.raises(IllegalTransitionError):
        manuscript.publish(actor_id=EDITOR, occurred_at=NOW)


def test_withdrawal_is_permitted_before_a_decision() -> None:
    manuscript = under_review()
    manuscript.withdraw(actor_id=AUTHOR, occurred_at=NOW)
    assert manuscript.status is S.WITHDRAWN


def accepted() -> Manuscript:
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT,
        actor_id=EDITOR,
        rationale="Strong contribution",
        occurred_at=NOW,
    )
    return manuscript


def test_accepted_manuscript_can_be_scheduled_then_published() -> None:
    """The terminal path. Everything else is preparation for this happening."""
    manuscript = accepted()
    issue_id = IssueId(uuid4())
    scheduled = manuscript.schedule(issue_id=issue_id, actor_id=EDITOR, occurred_at=NOW)
    assert status_of(manuscript) is S.SCHEDULED
    assert manuscript.issue_id == issue_id
    assert scheduled.event_type is EventType.SCHEDULED_FOR_ISSUE
    published = manuscript.publish(actor_id=EDITOR, occurred_at=NOW)
    assert status_of(manuscript) is S.PUBLISHED
    assert published.event_type is EventType.MANUSCRIPT_PUBLISHED


def test_reviews_are_refused_outside_the_review_stage() -> None:
    manuscript = submitted()
    with pytest.raises(GuardViolationError, match="only while under review"):
        manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)


def test_revision_may_be_requested_at_screening_without_any_reviews() -> None:
    """FR-07: an editor may return a manuscript for pre-review changes."""
    manuscript = submitted()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.REQUEST_REVISION,
        actor_id=EDITOR,
        rationale="Anonymise the manuscript before review",
        occurred_at=NOW,
    )
    assert manuscript.status is S.REVISION_REQUESTED


def test_closing_the_review_round_emits_a_distinct_event_type() -> None:
    """Counting REVIEW_SUBMITTED must not include the event that closes the round."""
    manuscript = under_review()
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    manuscript.record_review(reviewer_id=UserId(uuid4()), occurred_at=NOW)
    submitted_count = sum(
        1 for event in manuscript.pending_events if event.event_type is EventType.REVIEW_SUBMITTED
    )
    assert submitted_count == 2
    assert manuscript.pending_events[-1].event_type is EventType.REVIEW_ROUND_CLOSED


def test_sequence_numbers_continue_after_the_buffer_is_drained() -> None:
    """hashchain.append demands consecutive sequences across the manuscript's whole life.

    Draining the buffer is how a repository persists events, so numbering that restarts
    at 1 after a drain would collide with an event already in the chain.
    """
    manuscript = submitted()
    manuscript.pull_events()
    event = manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    assert event.sequence == 2


def test_decision_payload_carries_the_decision_and_rationale() -> None:
    """Payload keys are hashed into the audit chain, so their names are part of the contract."""
    manuscript = accepted()
    decision = manuscript.pending_events[-1]
    assert decision.payload["decision"] == "accept"
    assert decision.payload["rationale"] == "Strong contribution"
    assert decision.payload["status"] == "accepted"
