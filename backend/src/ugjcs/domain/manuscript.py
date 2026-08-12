"""The manuscript aggregate.

Every state change goes through `_transition`, which checks the lifecycle table and
emits exactly one event. There is no other write path, so the event log cannot drift
out of step with the materialised state.
"""

from dataclasses import dataclass, field
from datetime import datetime

from ugjcs.domain.enums import DecisionType, EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import GuardViolationError
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.transitions import assert_legal

_DECISION_TARGETS: dict[DecisionType, S] = {
    DecisionType.DESK_REJECT: S.DESK_REJECTED,
    DecisionType.SEND_TO_REVIEW: S.UNDER_REVIEW,
    DecisionType.REQUEST_REVISION: S.REVISION_REQUESTED,
    DecisionType.ACCEPT: S.ACCEPTED,
    DecisionType.REJECT: S.REJECTED,
}

# Only these need a quorum. REQUEST_REVISION is deliberately absent: FR-07 lets an editor
# return a manuscript for pre-review changes during screening, when no reviews exist yet.
# Post-review revision is already gated by the table, which reaches REVISION_REQUESTED from
# REVIEWS_COMPLETE and nowhere else after review begins.
_DECISIONS_REQUIRING_REVIEWS = frozenset({DecisionType.ACCEPT, DecisionType.REJECT})


@dataclass(slots=True)
class Manuscript:
    id: ManuscriptId
    tracking_code: TrackingCode
    title: str
    abstract: str
    keywords: tuple[str, ...]
    author_ids: tuple[UserId, ...]
    corresponding_author_id: UserId
    status: S = S.DRAFT
    version: int = 1
    minimum_reviews: int = 2
    submitted_reviews: int = 0
    issue_id: IssueId | None = None
    original_document_key: str | None = None
    """Where the current version's unmodified upload lives in object storage.

    Never served to a reviewer — see `anonymised_document_key`. `None` until a document
    has been attached, which happens in the same request as `submit()`/`resubmit()`, not
    as a separate transition of its own."""
    anonymised_document_key: str | None = None
    """Where the metadata-stripped derivative reviewers are served lives.

    Produced by `infrastructure.storage.anonymize.strip_pdf_metadata`, which strips
    DocInfo and XMP only — it cannot remove an author's name printed in the visible body
    text (TD-05)."""
    _sequence: int = 0
    _events: list[EditorialEvent] = field(default_factory=list, repr=False)

    @property
    def pending_events(self) -> tuple[EditorialEvent, ...]:
        return tuple(self._events)

    def pull_events(self) -> tuple[EditorialEvent, ...]:
        """Return buffered events and clear the buffer, for the caller to persist.

        `_sequence` is deliberately NOT reset. Sequence numbers must stay monotonic across
        the whole lifetime of the manuscript, not just the current buffer, because
        `hashchain.append` requires each event to follow its predecessor consecutively.
        A repository rehydrating this aggregate must seed `_sequence` from the last
        persisted event, otherwise the next event collides with one already in the chain.
        """
        drained = tuple(self._events)
        self._events.clear()
        return drained

    def submit(
        self,
        *,
        actor_id: UserId,
        occurred_at: datetime,
        original_document_key: str | None = None,
        anonymised_document_key: str | None = None,
    ) -> EditorialEvent:
        """Move to SUBMITTED, optionally attaching this version's document keys.

        Both key arguments default to `None` so every existing caller that submits
        without a document — the seed script, and every domain/API test that predates
        upload support — keeps working unchanged. A caller that does supply them gets
        both the aggregate fields set and the keys recorded in the event payload, so the
        attachment is part of the auditable history, not merely a side-channel update.
        """
        payload: dict[str, PayloadValue] = {"version": self.version}
        if original_document_key is not None:
            self.original_document_key = original_document_key
            payload["original_document_key"] = original_document_key
        if anonymised_document_key is not None:
            self.anonymised_document_key = anonymised_document_key
            payload["anonymised_document_key"] = anonymised_document_key
        return self._transition(
            S.SUBMITTED, EventType.MANUSCRIPT_SUBMITTED, actor_id, occurred_at, payload
        )

    def begin_screening(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.UNDER_SCREENING, EventType.SCREENING_STARTED, actor_id, occurred_at, {}
        )

    def record_review(self, *, reviewer_id: UserId, occurred_at: datetime) -> EditorialEvent:
        """Count a submitted review, completing the round once the quorum is met.

        The automatic move to REVIEWS_COMPLETE is what makes a decision reachable:
        ACCEPTED and REJECTED are deliberately unreachable from UNDER_REVIEW, so an
        editor cannot decide while reviews are still outstanding.

        What this does NOT do: `submitted_reviews` is a counter, not a set of reviewers.
        `reviewer_id` is recorded on the event but is checked against nothing — not
        against an assignment, not against `author_ids`, and not against reviewers who
        have already submitted. One reviewer calling this twice therefore reaches the
        quorum alone. Assignment tracking, which is what makes identity checkable here,
        arrives with reviewer assignment in a later plan; the fix belongs there rather
        than in a counter.
        """
        if self.status is not S.UNDER_REVIEW:
            raise GuardViolationError(
                f"reviews accepted only while under review, not in {self.status.value}"
            )
        self.submitted_reviews += 1
        event = self._emit(
            EventType.REVIEW_SUBMITTED,
            reviewer_id,
            occurred_at,
            {"submitted_reviews": self.submitted_reviews},
        )
        if self.submitted_reviews >= self.minimum_reviews:
            self._transition(
                S.REVIEWS_COMPLETE,
                EventType.REVIEW_ROUND_CLOSED,
                reviewer_id,
                occurred_at,
                {"reviews_complete": True},
            )
        return event

    def record_decision(
        self,
        *,
        decision: DecisionType,
        actor_id: UserId,
        rationale: str,
        occurred_at: datetime,
    ) -> EditorialEvent:
        if (
            decision in _DECISIONS_REQUIRING_REVIEWS
            and self.submitted_reviews < self.minimum_reviews
        ):
            raise GuardViolationError(
                f"{decision.value} requires {self.minimum_reviews} reviews, "
                f"has {self.submitted_reviews}"
            )
        return self._transition(
            _DECISION_TARGETS[decision],
            EventType.DECISION_RECORDED,
            actor_id,
            occurred_at,
            {"decision": decision.value, "rationale": rationale},
        )

    def resubmit(
        self,
        *,
        actor_id: UserId,
        occurred_at: datetime,
        original_document_key: str | None = None,
        anonymised_document_key: str | None = None,
        response_to_reviewers: str | None = None,
    ) -> EditorialEvent:
        """Move to RESUBMITTED, optionally attaching the revised document and a letter.

        See `submit()` for why the new keyword arguments default to `None` rather than
        being required: every caller that predates upload support must keep working.
        `response_to_reviewers` has nowhere else to live — there is no separate entity
        for it — so it is recorded in the event payload only, which is exactly where an
        editor reviewing the resubmission's history would look for it.
        """
        if actor_id != self.corresponding_author_id:
            raise GuardViolationError("only the corresponding author may resubmit")
        payload: dict[str, PayloadValue] = {"version": self.version + 1}
        if original_document_key is not None:
            self.original_document_key = original_document_key
            payload["original_document_key"] = original_document_key
        if anonymised_document_key is not None:
            self.anonymised_document_key = anonymised_document_key
            payload["anonymised_document_key"] = anonymised_document_key
        if response_to_reviewers is not None:
            payload["response_to_reviewers"] = response_to_reviewers
        event = self._transition(
            S.RESUBMITTED, EventType.REVISION_SUBMITTED, actor_id, occurred_at, payload
        )
        self.version += 1
        self.submitted_reviews = 0
        return event

    def schedule(
        self, *, issue_id: IssueId, actor_id: UserId, occurred_at: datetime
    ) -> EditorialEvent:
        event = self._transition(
            S.SCHEDULED,
            EventType.SCHEDULED_FOR_ISSUE,
            actor_id,
            occurred_at,
            {"issue_id": str(issue_id)},
        )
        self.issue_id = issue_id
        return event

    def publish(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.PUBLISHED, EventType.MANUSCRIPT_PUBLISHED, actor_id, occurred_at, {}
        )

    def withdraw(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.WITHDRAWN, EventType.MANUSCRIPT_WITHDRAWN, actor_id, occurred_at, {}
        )

    def _transition(
        self,
        target: S,
        event_type: EventType,
        actor_id: UserId,
        occurred_at: datetime,
        payload: dict[str, PayloadValue],
    ) -> EditorialEvent:
        assert_legal(self.status, target)
        self.status = target
        return self._emit(event_type, actor_id, occurred_at, payload | {"status": target.value})

    def _emit(
        self,
        event_type: EventType,
        actor_id: UserId,
        occurred_at: datetime,
        payload: dict[str, PayloadValue],
    ) -> EditorialEvent:
        self._sequence += 1
        event = EditorialEvent(
            manuscript_id=self.id,
            sequence=self._sequence,
            event_type=event_type,
            payload=payload,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )
        self._events.append(event)
        return event
