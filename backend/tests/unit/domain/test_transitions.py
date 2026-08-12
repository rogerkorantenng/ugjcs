import pytest

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import IllegalTransitionError
from ugjcs.domain.transitions import (
    LEGAL_TRANSITIONS,
    TERMINAL_STATES,
    assert_legal,
    is_legal,
)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.DRAFT, S.SUBMITTED),
        (S.SUBMITTED, S.UNDER_SCREENING),
        (S.UNDER_SCREENING, S.DESK_REJECTED),
        (S.UNDER_SCREENING, S.UNDER_REVIEW),
        (S.UNDER_SCREENING, S.REVISION_REQUESTED),
        (S.UNDER_REVIEW, S.REVIEWS_COMPLETE),
        (S.REVIEWS_COMPLETE, S.ACCEPTED),
        (S.REVIEWS_COMPLETE, S.REJECTED),
        (S.REVIEWS_COMPLETE, S.REVISION_REQUESTED),
        (S.REVISION_REQUESTED, S.RESUBMITTED),
        (S.RESUBMITTED, S.UNDER_REVIEW),
        (S.ACCEPTED, S.SCHEDULED),
        (S.SCHEDULED, S.PUBLISHED),
        (S.SUBMITTED, S.WITHDRAWN),
        (S.UNDER_REVIEW, S.WITHDRAWN),
    ],
)
def test_lifecycle_permits_expected_transitions(source: S, target: S) -> None:
    assert is_legal(source, target)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.DRAFT, S.PUBLISHED),
        (S.SUBMITTED, S.ACCEPTED),
        (S.UNDER_SCREENING, S.PUBLISHED),
        (S.UNDER_REVIEW, S.ACCEPTED),
        (S.ACCEPTED, S.PUBLISHED),
        (S.REJECTED, S.ACCEPTED),
        (S.DRAFT, S.DRAFT),
    ],
)
def test_lifecycle_forbids_shortcut_transitions(source: S, target: S) -> None:
    assert not is_legal(source, target)


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STATES))
def test_terminal_states_have_no_outgoing_transitions(terminal: S) -> None:
    assert LEGAL_TRANSITIONS[terminal] == frozenset()


def test_every_status_appears_in_the_table() -> None:
    assert set(LEGAL_TRANSITIONS) == set(S)


def test_assert_legal_is_silent_for_a_legal_transition() -> None:
    assert_legal(S.DRAFT, S.SUBMITTED)


def test_assert_legal_raises_naming_both_states() -> None:
    with pytest.raises(IllegalTransitionError, match=r"draft.*published"):
        assert_legal(S.DRAFT, S.PUBLISHED)
