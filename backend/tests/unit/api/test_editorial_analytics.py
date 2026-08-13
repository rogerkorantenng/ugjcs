"""Routing, authorisation and serialisation for the editorial analytics surface:
`GET /editorial/analytics`, `GET /editorial/reviewer-performance` and
`GET /editorial/{tracking_code}/assignments`.

The aggregate arithmetic is asserted against a corpus built through the same domain
methods production uses (`submit`/`record_decision`/...), with hand-picked timestamps,
so every expected number below is derivable by eye from the corpus builder — no fixture
file, no snapshot.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import (
    NOW,
    FakeAccount,
    FakeReviewContent,
    FakeUnitOfWork,
    new_user_id,
)
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

EDITOR = new_user_id()
AUTHOR = new_user_id()
REVIEWER = new_user_id()
JULY = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)


def make_client(actor: Actor, uow: FakeUnitOfWork) -> TestClient:
    app = create_app()

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def editor_actor() -> Actor:
    return Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))


def manuscript_shell(sequence: int) -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


def analytics_corpus(uow: FakeUnitOfWork) -> None:
    """Three manuscripts whose aggregate numbers are all computable by eye:

    - `fresh`: submitted in August, still SUBMITTED.
    - `accepted`: submitted 1 July, accept decision 11 July — 10.0 days to decision.
      Its one review assignment is marked submitted 3 days after assignment.
    - `desk_rejected`: submitted in August, desk-rejected — a rejection for the
      acceptance rate (1 accept / 2 decided = 0.5) but, being a screening-stage
      decision, excluded from the days-to-decision average by design.
    """
    fresh = manuscript_shell(201)
    fresh.submit(actor_id=AUTHOR, occurred_at=NOW)
    uow.manuscripts.ingest(fresh)

    accepted = manuscript_shell(202)
    accepted.submit(actor_id=AUTHOR, occurred_at=JULY)
    accepted.begin_screening(actor_id=EDITOR, occurred_at=JULY)
    accepted.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=JULY
    )
    for _ in range(accepted.minimum_reviews):
        accepted.record_review(reviewer_id=REVIEWER, occurred_at=JULY + timedelta(days=9))
    accepted.record_decision(
        decision=DecisionType.ACCEPT,
        actor_id=EDITOR,
        rationale="ok",
        occurred_at=JULY + timedelta(days=10),
    )
    uow.manuscripts.ingest(accepted)
    uow.assignments.assignments.append((accepted.id, REVIEWER))
    uow.assignments.submitted[(accepted.id, REVIEWER)] = _submitted_review(
        submitted_at=NOW + timedelta(days=3)
    )

    desk_rejected = manuscript_shell(203)
    desk_rejected.submit(actor_id=AUTHOR, occurred_at=NOW)
    desk_rejected.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    desk_rejected.record_decision(
        decision=DecisionType.DESK_REJECT,
        actor_id=EDITOR,
        rationale="out of scope",
        occurred_at=NOW + timedelta(days=1),
    )
    uow.manuscripts.ingest(desk_rejected)


def _submitted_review(*, submitted_at: datetime) -> FakeReviewContent:
    return FakeReviewContent(
        recommendation="accept",
        originality_score=4,
        rigour_score=4,
        clarity_score=4,
        significance_score=4,
        comments_to_author="Fine.",
        confidential_comments_to_editor="Fine.",
        submitted_at=submitted_at,
    )


def test_analytics_reports_pipeline_months_rate_and_averages() -> None:
    uow = FakeUnitOfWork()
    analytics_corpus(uow)
    client = make_client(editor_actor(), uow)
    response = client.get("/api/v1/editorial/analytics")
    assert response.status_code == 200
    body = response.json()
    # Exact dict equality on purpose: the pipeline's key set is part of the contract —
    # no `draft`, no separate `desk_rejected` (folded into `rejected`).
    assert body["pipeline"] == {
        "submitted": 1,
        "under_screening": 0,
        "under_review": 0,
        "reviews_complete": 0,
        "revision_requested": 0,
        "resubmitted": 0,
        "accepted": 1,
        "scheduled": 0,
        "published": 0,
        "rejected": 1,
        "withdrawn": 0,
    }
    assert body["submissions_by_month"] == [
        {"month": "2026-07", "count": 1},
        {"month": "2026-08", "count": 2},
    ]
    assert body["acceptance_rate"] == 0.5
    assert body["avg_days_submission_to_decision"] == 10.0
    assert body["avg_days_review_turnaround"] == 3.0


def test_analytics_over_an_empty_desk_reports_zeros_and_nulls_not_zero_rates() -> None:
    """The null-vs-zero rule: with nothing decided, the rate and both averages must be
    `null`, never `0` — an empty desk has no acceptance rate, not a 0% one."""
    client = make_client(editor_actor(), FakeUnitOfWork())
    response = client.get("/api/v1/editorial/analytics")
    assert response.status_code == 200
    body = response.json()
    assert all(count == 0 for count in body["pipeline"].values())
    assert body["submissions_by_month"] == []
    assert body["acceptance_rate"] is None
    assert body["avg_days_submission_to_decision"] is None
    assert body["avg_days_review_turnaround"] is None


def test_a_reviewer_may_not_read_analytics() -> None:
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, FakeUnitOfWork())
    assert client.get("/api/v1/editorial/analytics").status_code == 403


def _reviewer_account(reviewer_id: UserId, *, name: str, email: str) -> FakeAccount:
    return FakeAccount(
        id=reviewer_id, email=email, roles=frozenset({Role.REVIEWER}), full_name=name
    )


def test_reviewer_performance_reports_workload_and_turnaround_per_reviewer() -> None:
    veteran = new_user_id()
    newcomer = new_user_id()
    uow = FakeUnitOfWork()
    uow.accounts.accounts[veteran] = _reviewer_account(
        veteran, name="Ama Veteran", email="veteran@sdj.test"
    )
    uow.accounts.accounts[newcomer] = _reviewer_account(
        newcomer, name="Ben Newcomer", email="newcomer@sdj.test"
    )
    first, second, pending = ManuscriptId(uuid4()), ManuscriptId(uuid4()), ManuscriptId(uuid4())
    uow.assignments.assignments.extend(
        [(first, veteran), (second, veteran), (pending, veteran)]
    )
    # Two completed reviews, 3 and 5 days after the fake's fixed `assigned_at` (NOW),
    # plus one still outstanding: average 4.0 days, latest activity NOW + 5 days.
    uow.assignments.submitted[(first, veteran)] = _submitted_review(
        submitted_at=NOW + timedelta(days=3)
    )
    uow.assignments.submitted[(second, veteran)] = _submitted_review(
        submitted_at=NOW + timedelta(days=5)
    )

    client = make_client(editor_actor(), uow)
    response = client.get("/api/v1/editorial/reviewer-performance")
    assert response.status_code == 200
    body = response.json()
    assert [entry["full_name"] for entry in body] == ["Ama Veteran", "Ben Newcomer"]

    veteran_row, newcomer_row = body
    assert veteran_row["id"] == str(veteran)
    assert veteran_row["affiliation"] == "Test University"
    assert veteran_row["active_assignments"] == 1
    assert veteran_row["reviewer_capacity"] == 3
    assert veteran_row["reviews_completed"] == 2
    assert veteran_row["avg_turnaround_days"] == 4.0
    assert datetime.fromisoformat(veteran_row["last_activity_at"]) == NOW + timedelta(days=5)

    # No completed reviews: both time-based fields are null, not zero — "new to the
    # pool" must be distinguishable from "instant turnaround".
    assert newcomer_row["reviews_completed"] == 0
    assert newcomer_row["active_assignments"] == 0
    assert newcomer_row["avg_turnaround_days"] is None
    assert newcomer_row["last_activity_at"] is None


def test_a_reviewer_may_not_read_reviewer_performance() -> None:
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, FakeUnitOfWork())
    assert client.get("/api/v1/editorial/reviewer-performance").status_code == 403


def test_assignments_lists_deadlines_names_and_the_overdue_flag() -> None:
    manuscript = manuscript_shell(204)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    punctual, tardy = new_user_id(), new_user_id()
    uow = FakeUnitOfWork()
    uow.manuscripts.ingest(manuscript)
    uow.accounts.accounts[punctual] = _reviewer_account(
        punctual, name="Punctual Reviewer", email="punctual@sdj.test"
    )
    uow.accounts.accounts[tardy] = _reviewer_account(
        tardy, name="Tardy Reviewer", email="tardy@sdj.test"
    )
    uow.assignments.assignments.extend([(manuscript.id, punctual), (manuscript.id, tardy)])
    # Deadlines planted relative to the real clock, because `overdue` is judged against
    # `datetime.now` in the route: the punctual reviewer submitted (past deadline —
    # proving submitted rows are never overdue), the tardy one has not.
    past = datetime.now(UTC) - timedelta(days=2)
    uow.assignments.due_dates[(manuscript.id, punctual)] = past
    uow.assignments.due_dates[(manuscript.id, tardy)] = past
    uow.assignments.submitted[(manuscript.id, punctual)] = _submitted_review(
        submitted_at=NOW + timedelta(days=4)
    )

    client = make_client(editor_actor(), uow)
    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/assignments")
    assert response.status_code == 200
    by_id = {entry["reviewer_id"]: entry for entry in response.json()}

    submitted_row = by_id[str(punctual)]
    assert submitted_row["reviewer_name"] == "Punctual Reviewer"
    assert submitted_row["submitted"] is True
    assert submitted_row["overdue"] is False
    assert datetime.fromisoformat(submitted_row["assigned_at"]) == NOW
    assert datetime.fromisoformat(submitted_row["due_at"]) == past

    overdue_row = by_id[str(tardy)]
    assert overdue_row["reviewer_name"] == "Tardy Reviewer"
    assert overdue_row["submitted"] is False
    assert overdue_row["overdue"] is True


def test_an_assignment_before_its_deadline_is_not_overdue() -> None:
    manuscript = manuscript_shell(205)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    reviewer = new_user_id()
    uow = FakeUnitOfWork()
    uow.manuscripts.ingest(manuscript)
    uow.assignments.assignments.append((manuscript.id, reviewer))
    uow.assignments.due_dates[(manuscript.id, reviewer)] = datetime.now(UTC) + timedelta(days=5)

    client = make_client(editor_actor(), uow)
    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/assignments")
    assert response.status_code == 200
    [row] = response.json()
    assert row["submitted"] is False
    assert row["overdue"] is False
    # No account on file for this reviewer id: the row survives with a placeholder
    # rather than vanishing from the editor's chase list.
    assert row["reviewer_name"] == "Unknown reviewer"


def test_assignments_for_a_missing_manuscript_is_404() -> None:
    client = make_client(editor_actor(), FakeUnitOfWork())
    assert client.get("/api/v1/editorial/SDJ-2026-9999/assignments").status_code == 404


def test_a_reviewer_may_not_list_assignments() -> None:
    manuscript = manuscript_shell(206)
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    uow = FakeUnitOfWork()
    uow.manuscripts.ingest(manuscript)
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, uow)
    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/assignments")
    assert response.status_code == 403
