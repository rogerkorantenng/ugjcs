"""Wire shapes for the editorial analytics surface.

A separate module from `ugjcs.api.schemas` on purpose: that file carries the manuscript
lifecycle's contract shapes, which change with the domain, while these are aggregate
read models that change with what the editorial dashboard wants to chart. Keeping them
apart also keeps this feature's churn out of a file other work depends on.

Every numeric aggregate here follows one rule, stated once: a rate or an average whose
denominator is empty is `None` on the wire, never `0` — "no decisions yet" and "decisions
arrive instantly" must be distinguishable to a reader of the JSON.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ugjcs.api.schemas import ReviewerCandidateOut
from ugjcs.domain.account import Account


class PipelineCounts(BaseModel):
    """How many manuscripts sit at each stage of the editorial pipeline, right now.

    Keyed by current status, with two deliberate departures from
    `ugjcs.domain.enums.ManuscriptStatus`: `draft` is absent (a draft has never reached
    the editorial desk, so it is not pipeline work), and `desk_rejected` is folded into
    `rejected` — both are the journal declining the paper, and the dashboard's pipeline
    view has no reason to distinguish at which desk that happened.
    """

    submitted: int
    under_screening: int
    under_review: int
    reviews_complete: int
    revision_requested: int
    resubmitted: int
    accepted: int
    scheduled: int
    published: int
    rejected: int
    withdrawn: int


class MonthlySubmissions(BaseModel):
    """Original submissions in one calendar month. `month` is `YYYY-MM` in UTC, taken
    from the `MANUSCRIPT_SUBMITTED` event's `occurred_at`; resubmissions emit
    `REVISION_SUBMITTED` and are deliberately not counted a second time."""

    month: str
    count: int


class EditorialAnalyticsOut(BaseModel):
    """The editorial dashboard's aggregate view — see `editorial.analytics` for how each
    number is computed and which events anchor the averages."""

    pipeline: PipelineCounts
    submissions_by_month: list[MonthlySubmissions]
    acceptance_rate: float | None
    avg_days_submission_to_decision: float | None
    avg_days_review_turnaround: float | None


class ReviewerPerformanceOut(BaseModel):
    """One reviewer's workload and track record, for the editor deciding whom to ask next.

    `avg_turnaround_days` and `last_activity_at` are both `None` until the reviewer has
    completed at least one review: an editor must be able to tell "new to the pool" apart
    from "turns reviews around instantly", and only a null can carry that distinction.
    """

    id: UUID
    full_name: str
    affiliation: str
    active_assignments: int
    reviewer_capacity: int
    reviews_completed: int
    avg_turnaround_days: float | None
    last_activity_at: datetime | None


class AssignmentDeadlineOut(BaseModel):
    """One reviewer's assignment on a manuscript, deadline included — editor-facing only.

    Carrying `reviewer_name` here is deliberate and correct: the blind this journal
    enforces is author↔reviewer (see `ugjcs.domain.blinding`), not editor↔reviewer — the
    editor chose this reviewer by name in the first place. The route serving this model
    is gated by `Action.ASSIGN_REVIEWER`, which no author-reachable route carries.

    `overdue` is computed server-side (not left to the client) so every consumer agrees
    on the rule: not yet submitted AND `due_at` in the past. A submitted review is never
    overdue, however late it arrived, and a `None` deadline never counts as overdue.
    """

    reviewer_id: UUID
    reviewer_name: str
    assigned_at: datetime
    due_at: datetime | None
    submitted: bool
    overdue: bool


class RankedReviewerCandidateOut(ReviewerCandidateOut):
    """`ReviewerCandidateOut` plus how well the reviewer's expertise matches the
    manuscript — a subclass, not a copy, so the candidate shape stays defined in exactly
    one place and this model can never silently drift from it.

    `match_score` is the number of the manuscript's keywords that appear, case-
    insensitively, in the reviewer's `expertise` list — see `editorial._match_score` for
    the comparison rule. It is present on excluded candidates too: an editor reading
    "excluded, but a 3-keyword match" learns something ("recruit someone like this
    externally") that stripping the score would hide.
    """

    match_score: int

    @classmethod
    def from_account(
        cls,
        account: Account,
        *,
        active_assignments: int,
        excluded_reason: str | None,
        match_score: int,
    ) -> "RankedReviewerCandidateOut":
        """Named `from_account`, not an override of `from_domain`: adding a required
        keyword to an inherited classmethod's signature would break substitutability
        (and mypy strict rightly rejects it), so the ranked variant gets its own
        constructor instead."""
        return cls(
            id=UUID(str(account.id)),
            full_name=account.full_name,
            affiliation=account.affiliation,
            active_assignments=active_assignments,
            reviewer_capacity=account.reviewer_capacity,
            excluded_reason=excluded_reason,
            match_score=match_score,
        )
