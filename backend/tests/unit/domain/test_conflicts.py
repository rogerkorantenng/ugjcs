"""Exhaustive, DB-free tests for the conflict-of-interest domain rule.

`exclusion_reason` is a pure function: no repository, no FastAPI, no database. Every
exclusion rule from the spec is covered individually, plus the priority ordering between
rules when more than one applies at once.
"""

from uuid import uuid4

from ugjcs.domain.conflicts import (
    AFFILIATION_REASON,
    ALREADY_ASSIGNED_REASON,
    AT_CAPACITY_REASON,
    AUTHOR_REASON,
    exclusion_reason,
)
from ugjcs.domain.ids import UserId

AUTHOR_A = UserId(uuid4())
AUTHOR_B = UserId(uuid4())
CANDIDATE = UserId(uuid4())


def _reason(**overrides: object) -> str | None:
    defaults: dict[str, object] = {
        "candidate_id": CANDIDATE,
        "candidate_affiliation": "Independent Researcher",
        "author_ids": frozenset({AUTHOR_A, AUTHOR_B}),
        "author_affiliations": frozenset({"University of Ghana", "KNUST"}),
        "already_assigned_reviewer_ids": frozenset(),
        "active_assignments": 0,
        "reviewer_capacity": 3,
    }
    return exclusion_reason(**(defaults | overrides))  # type: ignore[arg-type]


def test_an_unrelated_reviewer_under_capacity_is_eligible() -> None:
    assert _reason() is None


def test_an_author_of_the_manuscript_is_excluded() -> None:
    assert _reason(candidate_id=AUTHOR_A) == AUTHOR_REASON


def test_sharing_an_affiliation_with_an_author_is_excluded() -> None:
    assert _reason(candidate_affiliation="University of Ghana") == AFFILIATION_REASON


def test_affiliation_comparison_is_case_insensitive() -> None:
    assert _reason(candidate_affiliation="UNIVERSITY OF GHANA") == AFFILIATION_REASON


def test_affiliation_comparison_ignores_surrounding_whitespace() -> None:
    assert _reason(candidate_affiliation="  University of Ghana  ") == AFFILIATION_REASON


def test_a_different_affiliation_is_not_excluded_on_that_ground() -> None:
    assert _reason(candidate_affiliation="A Different University") is None


def test_a_candidate_already_assigned_to_this_manuscript_is_excluded() -> None:
    assert _reason(already_assigned_reviewer_ids=frozenset({CANDIDATE})) == ALREADY_ASSIGNED_REASON


def test_being_assigned_elsewhere_does_not_trigger_already_assigned() -> None:
    other = UserId(uuid4())
    assert _reason(already_assigned_reviewer_ids=frozenset({other})) is None


def test_a_candidate_at_capacity_is_excluded() -> None:
    assert _reason(active_assignments=3, reviewer_capacity=3) == AT_CAPACITY_REASON


def test_a_candidate_over_capacity_is_excluded() -> None:
    assert _reason(active_assignments=5, reviewer_capacity=3) == AT_CAPACITY_REASON


def test_a_candidate_under_capacity_is_not_excluded_on_that_ground() -> None:
    assert _reason(active_assignments=2, reviewer_capacity=3) is None


def test_zero_capacity_excludes_even_with_no_active_assignments() -> None:
    assert _reason(active_assignments=0, reviewer_capacity=0) == AT_CAPACITY_REASON


def test_being_an_author_takes_priority_over_sharing_an_affiliation() -> None:
    assert (
        _reason(candidate_id=AUTHOR_A, candidate_affiliation="University of Ghana") == AUTHOR_REASON
    )


def test_being_an_author_takes_priority_over_already_assigned() -> None:
    assert (
        _reason(candidate_id=AUTHOR_A, already_assigned_reviewer_ids=frozenset({AUTHOR_A}))
        == AUTHOR_REASON
    )


def test_being_an_author_takes_priority_over_at_capacity() -> None:
    assert (
        _reason(candidate_id=AUTHOR_A, active_assignments=9, reviewer_capacity=1) == AUTHOR_REASON
    )


def test_sharing_an_affiliation_takes_priority_over_already_assigned() -> None:
    assert (
        _reason(
            candidate_affiliation="University of Ghana",
            already_assigned_reviewer_ids=frozenset({CANDIDATE}),
        )
        == AFFILIATION_REASON
    )


def test_sharing_an_affiliation_takes_priority_over_at_capacity() -> None:
    assert (
        _reason(
            candidate_affiliation="University of Ghana",
            active_assignments=9,
            reviewer_capacity=1,
        )
        == AFFILIATION_REASON
    )


def test_already_assigned_takes_priority_over_at_capacity() -> None:
    assert (
        _reason(
            already_assigned_reviewer_ids=frozenset({CANDIDATE}),
            active_assignments=9,
            reviewer_capacity=1,
        )
        == ALREADY_ASSIGNED_REASON
    )
