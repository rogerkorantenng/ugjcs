"""Screening, decisions, reviewer assignment and analytics — the editor's desk."""

from collections import Counter
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from ugjcs.api.deps import require as require_action
from ugjcs.api.routers.manuscripts import _get_or_404
from ugjcs.api.schemas import (
    AssignReviewerRequest,
    ManuscriptOut,
    RecordDecisionRequest,
    ReviewOut,
    ScheduleManuscriptRequest,
)
from ugjcs.api.schemas_analytics import (
    AssignmentDeadlineOut,
    EditorialAnalyticsOut,
    MonthlySubmissions,
    PipelineCounts,
    RankedReviewerCandidateOut,
    ReviewerPerformanceOut,
)
from ugjcs.api.wiring import DocumentStoreDep, UowDep
from ugjcs.application.ports import DEFAULT_APC_PESEWAS, UnitOfWork
from ugjcs.domain.account import Account
from ugjcs.domain.conflicts import exclusion_reason
from ugjcs.domain.enums import DecisionType, EventType, Role
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import UserId, mint_issue_id
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Action, Actor
from ugjcs.infrastructure.storage.fulltext import extract_pdf_text

router = APIRouter()

# Every status an editor can still act on, or is waiting on an action already taken —
# the full "open" set from `domain.transitions.LEGAL_TRANSITIONS`, minus the terminal
# states (`domain.transitions.TERMINAL_STATES`) and `DRAFT`, which never reaches an
# editor at all. A manuscript that has been screened must stay visible here, or an
# editor who screened it has no other way back to it — see the router's module note.
_QUEUE_STATUSES: frozenset[S] = frozenset(
    {
        S.SUBMITTED,
        S.UNDER_SCREENING,
        S.UNDER_REVIEW,
        S.REVIEWS_COMPLETE,
        S.REVISION_REQUESTED,
        S.RESUBMITTED,
        S.ACCEPTED,
    }
)

# Route-specific aliases, built the same way as `wiring.UowDep`/`deps.ActorDep`: ruff's
# B008 forbids `Depends(require(...))` as a bare default, so each role gate this router
# needs is a module-level `Annotated` alias instead.
ScreenDep = Annotated[Actor, Depends(require_action(Action.SCREEN))]
DecideDep = Annotated[Actor, Depends(require_action(Action.DECIDE))]
AssignReviewerDep = Annotated[Actor, Depends(require_action(Action.ASSIGN_REVIEWER))]
# `Action.PUBLISH` is granted to `Role.EDITOR_IN_CHIEF` alone (`domain/policies.py`), and
# it gates both routes below: scheduling and publishing are the same "the Editor-in-Chief
# commits this manuscript to an issue" authority split into two steps, not two separate
# permissions — there is no `Action.SCHEDULE` in the domain vocabulary to gate with instead.
PublishDep = Annotated[Actor, Depends(require_action(Action.PUBLISH))]
# `Action.VIEW_AUDIT` (editor + editor-in-chief, per `_ROLE_GRANTS`) gates the analytics
# routes: reading aggregate history over the whole desk is exactly the "inspect the
# record" authority that action names, and reusing it keeps the domain vocabulary closed
# rather than minting an `Action.VIEW_ANALYTICS` that would grant the identical role set.
AuditDep = Annotated[Actor, Depends(require_action(Action.VIEW_AUDIT))]


@router.get("/queue", response_model=list[ManuscriptOut])
async def screening_queue(actor: ScreenDep, uow: UowDep) -> list[ManuscriptOut]:
    """Every manuscript still awaiting some editorial action, not only fresh submissions —
    see `_QUEUE_STATUSES`. Published, rejected, desk-rejected and withdrawn manuscripts
    are excluded: none of them is work still owed to an editor."""
    manuscripts = await uow.manuscripts.list_by_statuses(_QUEUE_STATUSES)
    return [ManuscriptOut.from_domain(m) for m in manuscripts]


# Everything that has ever reached the editorial desk: the full status vocabulary minus
# DRAFT, which never leaves the author. Terminal states are deliberately included here,
# unlike `_QUEUE_STATUSES` — analytics is history, and history is mostly terminal.
_ANALYTICS_STATUSES: frozenset[S] = frozenset(S) - frozenset({S.DRAFT})

# The two sides of the acceptance rate, by *current* status. SCHEDULED and PUBLISHED
# count as accepted — every one of them passed through an accept decision to get there,
# and counting only manuscripts still sitting at ACCEPTED would make the rate fall every
# time the Editor-in-Chief publishes something.
_ACCEPTED_OUTCOMES: frozenset[S] = frozenset({S.ACCEPTED, S.SCHEDULED, S.PUBLISHED})
_REJECTED_OUTCOMES: frozenset[S] = frozenset({S.REJECTED, S.DESK_REJECTED})

# Decision-time is measured to the accept/reject that ends peer review, matching the
# ACCEPTED/REJECTED anchor the metric is defined against. `desk_reject` is deliberately
# not here: a screening-stage rejection takes days, not months, and averaging it in
# would flatter the peer-review pipeline this number exists to describe.
_TERMINAL_DECISIONS: frozenset[str] = frozenset({"accept", "reject"})

_SECONDS_PER_DAY = 86400.0


def _days_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / _SECONDS_PER_DAY


@router.get("/analytics", response_model=EditorialAnalyticsOut)
async def analytics(actor: AuditDep, uow: UowDep) -> EditorialAnalyticsOut:
    """Aggregate desk metrics, computed from manuscripts and their event chains.

    Definitions, stated precisely because each had alternatives:

    - `pipeline`: manuscripts per *current* status; `desk_rejected` folds into
      `rejected` and drafts are absent — see `PipelineCounts`.
    - `submissions_by_month`: `MANUSCRIPT_SUBMITTED` events bucketed by UTC `YYYY-MM`.
      One per manuscript; resubmissions emit `REVISION_SUBMITTED` and are not recounted.
    - `acceptance_rate`: accepted-side statuses over all finally-decided manuscripts
      (`_ACCEPTED_OUTCOMES` / (`_ACCEPTED_OUTCOMES` + `_REJECTED_OUTCOMES`)), rounded to
      two decimals. Desk rejections count as rejections here (the journal declined the
      paper), even though they are excluded from the decision-time average below.
    - `avg_days_submission_to_decision`: mean days from the `MANUSCRIPT_SUBMITTED` event
      to the first `DECISION_RECORDED` event whose decision is accept/reject
      (`_TERMINAL_DECISIONS`), rounded to one decimal.
    - `avg_days_review_turnaround`: mean days from `assigned_at` to `submitted_at` over
      every submitted review assignment, rounded to one decimal. Assignment-to-submission
      is what this schema records honestly; there is no per-round clock to measure
      instead, because rounds exist only as events, not as an entity with its own dates.

    Every rate/average is `None` when its denominator is empty. Event chains are read
    per manuscript through the same `chain_for` the audit endpoint trusts — an O(n)
    sequence of queries that is deliberate: this journal's corpus is dozens of papers,
    and a bespoke aggregate SQL path would be a second, unverified implementation of
    the chain's meaning.
    """
    manuscripts = await uow.manuscripts.list_by_statuses(_ANALYTICS_STATUSES)
    status_counts = Counter(m.status for m in manuscripts)
    monthly: Counter[str] = Counter()
    decision_days: list[float] = []
    for manuscript in manuscripts:
        submitted_at: datetime | None = None
        for link in await uow.manuscripts.chain_for(manuscript.id):
            event = link.event
            if event.event_type is EventType.MANUSCRIPT_SUBMITTED and submitted_at is None:
                submitted_at = event.occurred_at
                monthly[event.occurred_at.astimezone(UTC).strftime("%Y-%m")] += 1
            elif (
                event.event_type is EventType.DECISION_RECORDED
                and event.payload.get("decision") in _TERMINAL_DECISIONS
                and submitted_at is not None
            ):
                decision_days.append(_days_between(submitted_at, event.occurred_at))
                # At most one terminal decision exists per manuscript (the lifecycle
                # table permits no path out of ACCEPTED/REJECTED back to another
                # decision), and MANUSCRIPT_SUBMITTED always precedes it, so nothing
                # later in this chain can change either number.
                break

    accepted = sum(status_counts[outcome] for outcome in _ACCEPTED_OUTCOMES)
    rejected = sum(status_counts[outcome] for outcome in _REJECTED_OUTCOMES)
    decided = accepted + rejected

    turnaround_days = [
        _days_between(record.assigned_at, record.submitted_at)
        for record in await uow.assignments.list_all()
        if record.status == "submitted" and record.submitted_at is not None
    ]

    return EditorialAnalyticsOut(
        pipeline=PipelineCounts(
            submitted=status_counts[S.SUBMITTED],
            under_screening=status_counts[S.UNDER_SCREENING],
            under_review=status_counts[S.UNDER_REVIEW],
            reviews_complete=status_counts[S.REVIEWS_COMPLETE],
            revision_requested=status_counts[S.REVISION_REQUESTED],
            resubmitted=status_counts[S.RESUBMITTED],
            accepted=status_counts[S.ACCEPTED],
            scheduled=status_counts[S.SCHEDULED],
            published=status_counts[S.PUBLISHED],
            rejected=status_counts[S.REJECTED] + status_counts[S.DESK_REJECTED],
            withdrawn=status_counts[S.WITHDRAWN],
        ),
        submissions_by_month=[
            MonthlySubmissions(month=month, count=count) for month, count in sorted(monthly.items())
        ],
        acceptance_rate=round(accepted / decided, 2) if decided else None,
        avg_days_submission_to_decision=(
            round(sum(decision_days) / len(decision_days), 1) if decision_days else None
        ),
        avg_days_review_turnaround=(
            round(sum(turnaround_days) / len(turnaround_days), 1) if turnaround_days else None
        ),
    )


@router.get("/reviewer-performance", response_model=list[ReviewerPerformanceOut])
async def reviewer_performance(actor: AuditDep, uow: UowDep) -> list[ReviewerPerformanceOut]:
    """Workload and track record for every reviewer in the current pool.

    Built over `AccountRepository.list_by_role`, so it shows exactly the reviewers an
    editor could assign today — an account that was deactivated or lost the REVIEWER
    role is absent, which is the roster an editor planning assignments actually needs
    (its historical reviews still count in `analytics`' turnaround average, which reads
    the assignment table directly). Sorted by name for a stable, human-scannable list.
    """
    performance: list[ReviewerPerformanceOut] = []
    for account in await uow.accounts.list_by_role(Role.REVIEWER):
        records = await uow.assignments.list_for_reviewer(account.id)
        completed = [
            record
            for record in records
            if record.status == "submitted" and record.submitted_at is not None
        ]
        turnarounds = [
            _days_between(record.assigned_at, record.submitted_at)
            for record in completed
            if record.submitted_at is not None  # re-narrow for the type checker
        ]
        performance.append(
            ReviewerPerformanceOut(
                id=UUID(str(account.id)),
                full_name=account.full_name,
                affiliation=account.affiliation,
                active_assignments=sum(1 for r in records if r.status == "assigned"),
                reviewer_capacity=account.reviewer_capacity,
                reviews_completed=len(completed),
                avg_turnaround_days=(
                    round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else None
                ),
                last_activity_at=(
                    max(record.submitted_at for record in completed if record.submitted_at)
                    if completed
                    else None
                ),
            )
        )
    performance.sort(key=lambda entry: entry.full_name)
    return performance


@router.post("/{tracking_code}/screen", response_model=ManuscriptOut)
async def screen(tracking_code: str, actor: ScreenDep, uow: UowDep) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.begin_screening(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/decision", response_model=ManuscriptOut)
async def record_decision(
    tracking_code: str,
    body: RecordDecisionRequest,
    actor: DecideDep,
    uow: UowDep,
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.record_decision(
        decision=body.decision,
        actor_id=UserId(actor.id),
        rationale=body.rationale,
        occurred_at=datetime.now(UTC),
    )
    await uow.manuscripts.save(manuscript)
    if body.decision is DecisionType.ACCEPT:
        # Acceptance is the moment the APC becomes owed, so the invoice is opened in
        # the same transaction that records the decision — never one without the
        # other. `create_if_absent` keeps a re-recorded accept (or a race) from
        # double-billing; settlement is the billing router's business, not this one's.
        await uow.invoices.create_if_absent(
            manuscript.id, amount_pesewas=DEFAULT_APC_PESEWAS, created_at=datetime.now(UTC)
        )
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/reviewers", status_code=status.HTTP_204_NO_CONTENT)
async def assign_reviewer(
    tracking_code: str,
    body: AssignReviewerRequest,
    actor: AssignReviewerDep,
    uow: UowDep,
) -> None:
    manuscript = await _get_or_404(uow, tracking_code)
    await uow.assignments.assign(
        manuscript.id, UserId(body.reviewer_id), occurred_at=datetime.now(UTC)
    )
    await uow.commit()


@router.get("/{tracking_code}/assignments", response_model=list[AssignmentDeadlineOut])
async def list_assignments(
    tracking_code: str, actor: AssignReviewerDep, uow: UowDep
) -> list[AssignmentDeadlineOut]:
    """Every reviewer asked to review this manuscript, with deadline status.

    Gated by `Action.ASSIGN_REVIEWER` — the same grant that let the editor create these
    assignments — because chasing an overdue review is part of managing the assignment,
    not a separate privilege. Reviewer names are served openly here: the blind this
    journal enforces is author↔reviewer (`ugjcs.domain.blinding`), never
    editor↔reviewer, and no author-reachable route builds `AssignmentDeadlineOut`.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    now = datetime.now(UTC)
    deadlines: list[AssignmentDeadlineOut] = []
    for record in await uow.assignments.list_for_manuscript(manuscript.id):
        reviewer = await uow.accounts.get(record.reviewer_id)
        submitted = record.status == "submitted"
        deadlines.append(
            AssignmentDeadlineOut(
                reviewer_id=UUID(str(record.reviewer_id)),
                # A vanished account (deactivated after assignment) still owes context to
                # the editor chasing the review, so the row stays with a placeholder name
                # rather than disappearing.
                reviewer_name=reviewer.full_name if reviewer is not None else "Unknown reviewer",
                assigned_at=record.assigned_at,
                due_at=record.due_at,
                submitted=submitted,
                # A submitted review is never overdue however late it landed, and a
                # NULL deadline (pre-backfill row) never counts as overdue — see
                # `AssignmentDeadlineOut`'s docstring.
                overdue=not submitted and record.due_at is not None and record.due_at < now,
            )
        )
    return deadlines


def _match_score(keywords: tuple[str, ...], expertise: tuple[str, ...]) -> int:
    """How many of the manuscript's keywords appear in the reviewer's expertise list.

    Case-insensitive whole-token comparison: `"Fraud Detection"` matches
    `"fraud detection"`, but deliberately not the bare substring `"fraud"` — keyword
    vocabularies here are curated phrases (see the seed's `REVIEWER_PROFILES`, which
    echo manuscript keywords verbatim), and substring matching would invent expertise
    from coincidences like "systems" ⊂ "ecosystems". Scored over the manuscript's
    keywords, so the ceiling is how much of *this paper* the reviewer covers, not how
    long their expertise list is.
    """
    expertise_tokens = {entry.strip().lower() for entry in expertise}
    return sum(1 for keyword in keywords if keyword.strip().lower() in expertise_tokens)


@router.get("/{tracking_code}/reviewer-candidates", response_model=list[RankedReviewerCandidateOut])
async def reviewer_candidates(
    tracking_code: str, actor: AssignReviewerDep, uow: UowDep
) -> list[RankedReviewerCandidateOut]:
    """Every verified, active `REVIEWER`, conflict-of-interest verdict included, ranked
    by how well their declared expertise matches this manuscript's keywords.

    Excluded candidates are returned in the list with their reason rather than filtered
    out — see `ugjcs.domain.conflicts.exclusion_reason`, the pure function that decides
    it; this handler only gathers the data it needs. An account that is not verified,
    not active, or lacks the `REVIEWER` role is never fetched in the first place (see
    `AccountRepository.list_by_role`), so it never appears here at all.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    authors = [a for a in await _authors_for(uow, manuscript.author_ids) if a is not None]
    author_affiliations = frozenset(a.affiliation for a in authors)
    author_ids = frozenset(manuscript.author_ids)
    assigned_here = frozenset(
        UserId(record.reviewer_id)
        for record in await uow.assignments.list_for_manuscript(manuscript.id)
    )
    candidates: list[RankedReviewerCandidateOut] = []
    for account in await uow.accounts.list_by_role(Role.REVIEWER):
        active = await _active_assignment_count(uow, account.id)
        reason = exclusion_reason(
            candidate_id=account.id,
            candidate_affiliation=account.affiliation,
            author_ids=author_ids,
            author_affiliations=author_affiliations,
            already_assigned_reviewer_ids=assigned_here,
            active_assignments=active,
            reviewer_capacity=account.reviewer_capacity,
        )
        candidates.append(
            RankedReviewerCandidateOut.from_account(
                account,
                active_assignments=active,
                excluded_reason=reason,
                match_score=_match_score(manuscript.keywords, account.expertise),
            )
        )
    # Eligible before excluded (`False < True`), then best expertise match first, then
    # by lowest current load so equal matches naturally spread work — see the route's
    # docstring. Excluded candidates sink to the bottom but keep the same internal
    # ordering, so the reason an editor reads there is attached to the likeliest
    # near-miss first.
    candidates.sort(
        key=lambda c: (c.excluded_reason is not None, -c.match_score, c.active_assignments)
    )
    return candidates


async def _authors_for(uow: UnitOfWork, author_ids: tuple[UserId, ...]) -> list[Account | None]:
    return [await uow.accounts.get(author_id) for author_id in author_ids]


async def _active_assignment_count(uow: UnitOfWork, reviewer_id: UserId) -> int:
    """Assignments not yet submitted — the reviewer's current outstanding workload."""
    records = await uow.assignments.list_for_reviewer(reviewer_id)
    return sum(1 for record in records if record.status == "assigned")


@router.get("/{tracking_code}/reviews", response_model=list[ReviewOut])
async def list_reviews(tracking_code: str, actor: DecideDep, uow: UowDep) -> list[ReviewOut]:
    """The one place `confidential_comments_to_editor` (FR-11) is ever served: gated by
    `Action.DECIDE`, the same grant `record_decision` requires, so no route an author can
    reach ever returns this list — `ugjcs.api.routers.manuscripts`/`reviews` build no
    response model that includes it, structurally, the same way `BlindedManuscriptOut`
    has no author field to leak.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    records = await uow.assignments.list_for_manuscript(manuscript.id)
    return [ReviewOut.from_record(record) for record in records]


@router.post("/{tracking_code}/schedule", response_model=ManuscriptOut)
async def schedule(
    tracking_code: str,
    body: ScheduleManuscriptRequest,
    actor: PublishDep,
    uow: UowDep,
) -> ManuscriptOut:
    """`IssueId` is derived deterministically from `(volume, number)` — see
    `ugjcs.domain.ids.mint_issue_id` for why: issues are not a persisted entity, so this
    is the identifier scheduling has to work with instead of a lookup.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.schedule(
        issue_id=mint_issue_id(body.volume, body.number),
        actor_id=UserId(actor.id),
        occurred_at=datetime.now(UTC),
    )
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/publish", response_model=ManuscriptOut)
async def publish(
    tracking_code: str, actor: PublishDep, uow: UowDep, documents: DocumentStoreDep
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.publish(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await _index_fulltext(uow, manuscript, documents)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


async def _index_fulltext(
    uow: UnitOfWork, manuscript: Manuscript, documents: DocumentStoreDep
) -> None:
    """Extract the freshly published PDF's text into `manuscripts.fulltext`.

    Best-effort by design: publication is an editorial act, search indexing a
    convenience derived from it, so no storage hiccup or unreadable PDF may roll the
    publish back — hence the deliberately broad `except Exception`. A paper that slips
    through unindexed is picked up by the entrypoint backfill
    (`ugjcs.scripts.backfill_fulltext`) on the next deploy, which is the same code
    path serving papers published before this feature existed.
    """
    if manuscript.original_document_key is None:
        return
    try:
        text = extract_pdf_text(await documents.get(manuscript.original_document_key))
    except Exception:  # deliberately broad - see docstring: indexing never blocks publishing
        return
    if text:
        await uow.manuscripts.store_fulltext(manuscript.id, text)
