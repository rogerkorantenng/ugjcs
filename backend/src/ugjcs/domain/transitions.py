"""The manuscript lifecycle, expressed as data rather than as branching code.

Keeping the table separate from the aggregate means editorial policy can change
without touching aggregate behaviour, and the table can be exhaustively tested.
"""

from collections.abc import Mapping

from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.errors import IllegalTransitionError

TERMINAL_STATES: frozenset[S] = frozenset({S.DESK_REJECTED, S.REJECTED, S.PUBLISHED, S.WITHDRAWN})

_WITHDRAWABLE_FROM = (
    S.SUBMITTED,
    S.UNDER_SCREENING,
    S.UNDER_REVIEW,
    S.REVIEWS_COMPLETE,
    S.REVISION_REQUESTED,
)

LEGAL_TRANSITIONS: Mapping[S, frozenset[S]] = {
    S.DRAFT: frozenset({S.SUBMITTED}),
    S.SUBMITTED: frozenset({S.UNDER_SCREENING, S.WITHDRAWN}),
    S.UNDER_SCREENING: frozenset(
        {S.DESK_REJECTED, S.UNDER_REVIEW, S.REVISION_REQUESTED, S.WITHDRAWN}
    ),
    S.UNDER_REVIEW: frozenset({S.REVIEWS_COMPLETE, S.WITHDRAWN}),
    S.REVIEWS_COMPLETE: frozenset({S.ACCEPTED, S.REJECTED, S.REVISION_REQUESTED, S.WITHDRAWN}),
    S.REVISION_REQUESTED: frozenset({S.RESUBMITTED, S.WITHDRAWN}),
    S.RESUBMITTED: frozenset({S.UNDER_REVIEW, S.UNDER_SCREENING}),
    S.ACCEPTED: frozenset({S.SCHEDULED}),
    S.SCHEDULED: frozenset({S.PUBLISHED}),
    S.DESK_REJECTED: frozenset(),
    S.REJECTED: frozenset(),
    S.PUBLISHED: frozenset(),
    S.WITHDRAWN: frozenset(),
}


def is_legal(source: S, target: S) -> bool:
    """Whether the lifecycle permits moving from `source` to `target`."""
    return target in LEGAL_TRANSITIONS[source]


def assert_legal(source: S, target: S) -> None:
    """Raise `IllegalTransitionError` unless the move is permitted."""
    if not is_legal(source, target):
        raise IllegalTransitionError(
            f"cannot move manuscript from {source.value} to {target.value}"
        )
