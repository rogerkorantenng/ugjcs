from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeAccount, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, mint_issue_id
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

EDITOR = new_user_id()
AUTHOR = new_user_id()
REVIEWER = new_user_id()
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_client(actor: Actor, *manuscripts: Manuscript) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for manuscript in manuscripts:
        uow.manuscripts.store[manuscript.id] = manuscript

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def submitted_manuscript(sequence: int = 71) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    return manuscript


def test_the_queue_lists_submitted_manuscripts_for_an_editor() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, submitted_manuscript())
    response = client.get("/api/v1/editorial/queue")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_the_queue_includes_manuscripts_at_every_stage_needing_editorial_attention() -> None:
    """The gap this closes: an editor who has already screened a manuscript must still be
    able to find it, all the way through to ACCEPTED where the Editor-in-Chief schedules
    it — see `_QUEUE_STATUSES` in `ugjcs.api.routers.editorial`."""
    under_screening = submitted_manuscript(101)
    under_screening.begin_screening(actor_id=EDITOR, occurred_at=NOW)

    under_review = submitted_manuscript(102)
    under_review.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    under_review.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )

    reviews_complete = submitted_manuscript(103)
    reviews_complete.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    reviews_complete.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    for _ in range(reviews_complete.minimum_reviews):
        reviews_complete.record_review(reviewer_id=REVIEWER, occurred_at=NOW)

    accepted = submitted_manuscript(104)
    accepted.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    accepted.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    for _ in range(accepted.minimum_reviews):
        accepted.record_review(reviewer_id=REVIEWER, occurred_at=NOW)
    accepted.record_decision(
        decision=DecisionType.ACCEPT, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )

    rejected = submitted_manuscript(105)
    rejected.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    rejected.record_decision(
        decision=DecisionType.DESK_REJECT, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )

    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(
        actor,
        submitted_manuscript(100),
        under_screening,
        under_review,
        reviews_complete,
        accepted,
        rejected,
    )
    response = client.get("/api/v1/editorial/queue")
    assert response.status_code == 200
    statuses = {m["status"] for m in response.json()}
    assert statuses == {
        "submitted",
        "under_screening",
        "under_review",
        "reviews_complete",
        "accepted",
    }
    assert "desk_rejected" not in statuses


def test_an_editor_can_list_the_reviews_recorded_for_a_manuscript() -> None:
    manuscript = submitted_manuscript(106)
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviews")
    assert response.status_code == 200
    assert response.json() == []


def test_an_editor_sees_the_confidential_comments_a_reviewer_wrote() -> None:
    """FR-11: confidential comments to the editor are recorded and are visible to the
    editor who requests this manuscript's reviews — see `ReviewOut`."""
    manuscript = submitted_manuscript(107)
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.assignments.assignments.append((manuscript.id, REVIEWER))
    reviewer_actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: reviewer_actor
    reviewer_client = TestClient(app)
    reviewer_client.post(
        f"/api/v1/reviews/{manuscript.tracking_code.value}/submit",
        json={
            "recommendation": "accept",
            "originality_score": 5,
            "rigour_score": 4,
            "clarity_score": 4,
            "significance_score": 5,
            "comments_to_author": "Nice work.",
            "confidential_comments_to_editor": "I know this author; disclosing for the record.",
        },
    )

    app.dependency_overrides[get_current_actor] = lambda: Actor(
        id=EDITOR, roles=frozenset({Role.EDITOR})
    )
    editor_client = TestClient(app)
    response = editor_client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviews")
    assert response.status_code == 200
    [review] = response.json()
    assert review["originality_score"] == 5
    assert review["comments_to_author"] == "Nice work."
    assert (
        review["confidential_comments_to_editor"]
        == "I know this author; disclosing for the record."
    )


def test_a_reviewer_may_not_see_the_screening_queue() -> None:
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, submitted_manuscript())
    response = client.get("/api/v1/editorial/queue")
    assert response.status_code == 403


def test_an_editor_can_begin_screening() -> None:
    manuscript = submitted_manuscript()
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/screen")
    assert response.status_code == 200
    assert response.json()["status"] == "under_screening"


def test_screening_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor)
    response = client.post("/api/v1/editorial/SDJ-2026-9999/screen")
    assert response.status_code == 404


def test_a_decision_moves_the_manuscript_to_review() -> None:
    manuscript = submitted_manuscript()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "send_to_review", "rationale": "Fits scope, well written."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_a_reviewer_cannot_record_a_decision() -> None:
    manuscript = submitted_manuscript()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "send_to_review", "rationale": "x"},
    )
    assert response.status_code == 403


def test_assigning_a_reviewer_records_it() -> None:
    manuscript = submitted_manuscript()
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewers",
        json={"reviewer_id": str(REVIEWER)},
    )
    assert response.status_code == 204


def test_assigning_a_reviewer_to_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor)
    response = client.post(
        "/api/v1/editorial/SDJ-2026-9999/reviewers",
        json={"reviewer_id": str(REVIEWER)},
    )
    assert response.status_code == 404


def accepted_manuscript(sequence: int = 61) -> Manuscript:
    manuscript = submitted_manuscript(sequence)
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    for _ in range(manuscript.minimum_reviews):
        manuscript.record_review(reviewer_id=REVIEWER, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.ACCEPT, actor_id=EDITOR, rationale="Accepted", occurred_at=NOW
    )
    return manuscript


EIC = new_user_id()


def test_the_editor_in_chief_can_schedule_an_accepted_manuscript() -> None:
    manuscript = accepted_manuscript()
    actor = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/schedule",
        json={"volume": 3, "number": 1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"
    assert manuscript.issue_id == mint_issue_id(3, 1)


def test_a_plain_editor_cannot_schedule() -> None:
    manuscript = accepted_manuscript()
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/schedule",
        json={"volume": 3, "number": 1},
    )
    assert response.status_code == 403


def test_scheduling_the_same_volume_and_number_twice_yields_the_same_issue_id() -> None:
    first = accepted_manuscript(sequence=62)
    second = accepted_manuscript(sequence=63)
    actor = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client = make_client(actor, first, second)
    client.post(
        f"/api/v1/editorial/{first.tracking_code.value}/schedule",
        json={"volume": 5, "number": 2},
    )
    client.post(
        f"/api/v1/editorial/{second.tracking_code.value}/schedule",
        json={"volume": 5, "number": 2},
    )
    assert first.issue_id == second.issue_id


def test_the_editor_in_chief_can_publish_a_scheduled_manuscript() -> None:
    manuscript = accepted_manuscript(sequence=64)
    actor = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client = make_client(actor, manuscript)
    client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/schedule",
        json={"volume": 1, "number": 1},
    )
    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/publish")
    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_publishing_without_scheduling_first_is_a_conflict() -> None:
    manuscript = accepted_manuscript(sequence=65)
    actor = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client = make_client(actor, manuscript)
    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/publish")
    assert response.status_code == 409


def test_a_plain_editor_cannot_publish() -> None:
    manuscript = accepted_manuscript(sequence=66)
    manuscript.schedule(issue_id=mint_issue_id(1, 1), actor_id=EIC, occurred_at=NOW)
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor, manuscript)
    response = client.post(f"/api/v1/editorial/{manuscript.tracking_code.value}/publish")
    assert response.status_code == 403


def test_scheduling_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client = make_client(actor)
    response = client.post(
        "/api/v1/editorial/SDJ-2026-9999/schedule", json={"volume": 1, "number": 1}
    )
    assert response.status_code == 404


def test_a_reviewer_cannot_see_reviewer_candidates() -> None:
    manuscript = submitted_manuscript(150)
    actor = Actor(id=REVIEWER, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, manuscript)
    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewer-candidates")
    assert response.status_code == 403


def test_reviewer_candidates_for_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    client = make_client(actor)
    response = client.get("/api/v1/editorial/SDJ-2026-9999/reviewer-candidates")
    assert response.status_code == 404


def test_reviewer_candidates_is_accessible_to_the_editor_in_chief_too() -> None:
    manuscript = submitted_manuscript(151)
    actor = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client = make_client(actor, manuscript)
    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewer-candidates")
    assert response.status_code == 200
    assert response.json() == []


def test_reviewer_candidates_omits_unverified_inactive_and_non_reviewer_accounts() -> None:
    manuscript = submitted_manuscript(152)
    inactive_reviewer = new_user_id()
    unverified_reviewer = new_user_id()
    non_reviewer = new_user_id()
    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.accounts.accounts[inactive_reviewer] = FakeAccount(
        id=inactive_reviewer,
        email="inactive@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        is_active=False,
    )
    uow.accounts.accounts[unverified_reviewer] = FakeAccount(
        id=unverified_reviewer,
        email="unverified@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        is_verified=False,
    )
    uow.accounts.accounts[non_reviewer] = FakeAccount(
        id=non_reviewer, email="noreviewer@sdj.test", roles=frozenset({Role.EDITOR})
    )

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    client = TestClient(app)

    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewer-candidates")
    assert response.status_code == 200
    assert response.json() == []


def test_reviewer_candidates_lists_eligible_and_excluded_with_their_reasons() -> None:
    """One of each conflict-of-interest rule, plus two clean candidates whose ordering
    proves the load tiebreak: eligible before excluded, and — with every expertise list
    empty, so every `match_score` is 0 — lowest current load first."""
    conflicted_author_reviewer = new_user_id()
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 153),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR, conflicted_author_reviewer),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)

    same_affiliation = new_user_id()
    already_assigned = new_user_id()
    at_capacity = new_user_id()
    eligible_low_load = new_user_id()
    eligible_high_load = new_user_id()
    elsewhere_manuscript_id = ManuscriptId(uuid4())
    another_elsewhere_manuscript_id = ManuscriptId(uuid4())

    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.accounts.accounts[AUTHOR] = FakeAccount(
        id=AUTHOR,
        email="author@sdj.test",
        roles=frozenset({Role.AUTHOR}),
        affiliation="University of Ghana",
    )
    uow.accounts.accounts[conflicted_author_reviewer] = FakeAccount(
        id=conflicted_author_reviewer,
        email="conflicted@sdj.test",
        roles=frozenset({Role.AUTHOR, Role.REVIEWER}),
        affiliation="Independent",
    )
    uow.accounts.accounts[same_affiliation] = FakeAccount(
        id=same_affiliation,
        email="same-affiliation@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="university of ghana",
    )
    uow.accounts.accounts[already_assigned] = FakeAccount(
        id=already_assigned,
        email="already-assigned@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
    )
    uow.accounts.accounts[at_capacity] = FakeAccount(
        id=at_capacity,
        email="at-capacity@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
        reviewer_capacity=1,
    )
    uow.accounts.accounts[eligible_low_load] = FakeAccount(
        id=eligible_low_load,
        email="low-load@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
    )
    uow.accounts.accounts[eligible_high_load] = FakeAccount(
        id=eligible_high_load,
        email="high-load@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
    )

    uow.assignments.assignments.append((manuscript.id, already_assigned))
    uow.assignments.assignments.append((elsewhere_manuscript_id, at_capacity))
    uow.assignments.assignments.append((another_elsewhere_manuscript_id, eligible_high_load))

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    client = TestClient(app)

    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewer-candidates")
    assert response.status_code == 200
    body = response.json()
    by_id = {c["id"]: c for c in body}

    assert by_id[str(conflicted_author_reviewer)]["excluded_reason"] == (
        "is an author of this manuscript"
    )
    assert by_id[str(same_affiliation)]["excluded_reason"] == (
        "shares an affiliation with an author"
    )
    assert by_id[str(already_assigned)]["excluded_reason"] == "already assigned"
    assert by_id[str(at_capacity)]["excluded_reason"] == "at capacity"
    assert by_id[str(eligible_low_load)]["excluded_reason"] is None
    assert by_id[str(eligible_high_load)]["excluded_reason"] is None
    assert by_id[str(eligible_low_load)]["active_assignments"] == 0
    assert by_id[str(eligible_high_load)]["active_assignments"] == 1

    ids_in_order = [c["id"] for c in body]
    assert ids_in_order[:2] == [str(eligible_low_load), str(eligible_high_load)]
    assert all(c["excluded_reason"] is not None for c in body[2:])
    # With no expertise declared anywhere, every candidate scores 0 — and the field is
    # present on excluded candidates too, by design (see `RankedReviewerCandidateOut`).
    assert all(c["match_score"] == 0 for c in body)


def test_reviewer_candidates_are_ranked_by_expertise_match_then_load() -> None:
    """The expertise ranking, isolated: a better keyword match outranks a lighter load,
    load only breaks score ties, and a strongly-matching excluded candidate still sinks
    below every eligible one."""
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 154),
        title="T",
        abstract="A.",
        keywords=("edge computing", "renewable energy", "rural connectivity"),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)

    unmatched_idle = new_user_id()
    specialist_busy = new_user_id()
    specialist_idle = new_user_id()
    excluded_expert = new_user_id()
    elsewhere_manuscript_id = ManuscriptId(uuid4())

    actor = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
    app = create_app()
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    uow.accounts.accounts[AUTHOR] = FakeAccount(
        id=AUTHOR,
        email="author@sdj.test",
        roles=frozenset({Role.AUTHOR}),
        affiliation="University of Ghana",
    )
    uow.accounts.accounts[unmatched_idle] = FakeAccount(
        id=unmatched_idle,
        email="unmatched@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
        expertise=("blockchain",),
    )
    # Case-insensitive whole-phrase matching, and no substring credit: "EDGE Computing"
    # and "Renewable Energy" both count; "connectivity" alone does not.
    uow.accounts.accounts[specialist_busy] = FakeAccount(
        id=specialist_busy,
        email="specialist-busy@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
        expertise=("EDGE Computing", "Renewable Energy", "connectivity"),
    )
    uow.accounts.accounts[specialist_idle] = FakeAccount(
        id=specialist_idle,
        email="specialist-idle@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="Elsewhere University",
        expertise=("edge computing", "renewable energy"),
    )
    uow.accounts.accounts[excluded_expert] = FakeAccount(
        id=excluded_expert,
        email="excluded-expert@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        affiliation="University of Ghana",  # same as the author: conflict, excluded
        expertise=("edge computing", "renewable energy", "rural connectivity"),
    )
    uow.assignments.assignments.append((elsewhere_manuscript_id, specialist_busy))

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    client = TestClient(app)

    response = client.get(f"/api/v1/editorial/{manuscript.tracking_code.value}/reviewer-candidates")
    assert response.status_code == 200
    body = response.json()
    by_id = {c["id"]: c for c in body}

    assert by_id[str(specialist_idle)]["match_score"] == 2
    assert by_id[str(specialist_busy)]["match_score"] == 2
    assert by_id[str(unmatched_idle)]["match_score"] == 0
    assert by_id[str(excluded_expert)]["match_score"] == 3
    assert by_id[str(excluded_expert)]["excluded_reason"] == (
        "shares an affiliation with an author"
    )

    # Best match first; the 2-2 tie broken by lower load; the zero-match idle reviewer
    # after both specialists despite their heavier loads; the excluded expert last of
    # all, its 3-keyword score notwithstanding.
    assert [c["id"] for c in body] == [
        str(specialist_idle),
        str(specialist_busy),
        str(unmatched_idle),
        str(excluded_expert),
    ]
