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

_DECISIONS_REQUIRING_REVIEWS = frozenset(
    {DecisionType.ACCEPT, DecisionType.REJECT, DecisionType.REQUEST_REVISION}
)


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
    _events: list[EditorialEvent] = field(default_factory=list, repr=False)

    @property
    def pending_events(self) -> tuple[EditorialEvent, ...]:
        return tuple(self._events)

    def pull_events(self) -> tuple[EditorialEvent, ...]:
        """Return buffered events and clear the buffer, for the caller to persist."""
        drained = tuple(self._events)
        self._events.clear()
        return drained

    def submit(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        return self._transition(
            S.SUBMITTED,
            EventType.MANUSCRIPT_SUBMITTED,
            actor_id,
            occurred_at,
            {"version": self.version},
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
                EventType.REVIEW_SUBMITTED,
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

    def resubmit(self, *, actor_id: UserId, occurred_at: datetime) -> EditorialEvent:
        if actor_id != self.corresponding_author_id:
            raise GuardViolationError("only the corresponding author may resubmit")
        event = self._transition(
            S.RESUBMITTED,
            EventType.REVISION_SUBMITTED,
            actor_id,
            occurred_at,
            {"version": self.version + 1},
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
        event = EditorialEvent(
            manuscript_id=self.id,
            sequence=len(self._events) + 1,
            event_type=event_type,
            payload=payload,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )
        self._events.append(event)
        return event
