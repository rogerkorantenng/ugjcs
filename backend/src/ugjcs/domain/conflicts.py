"""Conflict-of-interest rules for reviewer assignment.

A pure function, deliberately: no repository, no FastAPI, no database. The caller
(`ugjcs.api.routers.editorial.reviewer_candidates`) gathers the manuscript's authors,
their affiliations, the candidate's current load, and any existing assignment on this
manuscript, then hands all of it here as plain values. This module decides; it never
fetches. That split is what makes conflict-of-interest a stated, exhaustively unit-tested
property of the system rather than an incidental effect of a SQL `WHERE` clause.

Checked in order, and the order is the priority when more than one rule applies at once:
being an author outranks sharing an affiliation, which outranks an existing assignment,
which outranks capacity — each check below documents why.
"""

from ugjcs.domain.ids import UserId

AUTHOR_REASON = "is an author of this manuscript"
AFFILIATION_REASON = "shares an affiliation with an author"
ALREADY_ASSIGNED_REASON = "already assigned"
AT_CAPACITY_REASON = "at capacity"


def exclusion_reason(
    *,
    candidate_id: UserId,
    candidate_affiliation: str,
    author_ids: frozenset[UserId],
    author_affiliations: frozenset[str],
    already_assigned_reviewer_ids: frozenset[UserId],
    active_assignments: int,
    reviewer_capacity: int,
) -> str | None:
    """Why `candidate_id` must not be assigned to review this manuscript, or `None`.

    `author_affiliations` and `candidate_affiliation` are compared case- and
    whitespace-insensitively — affiliation is free text an account holder typed, and two
    spellings of the same institution must not defeat the check.
    """
    if candidate_id in author_ids:
        return AUTHOR_REASON
    if _normalise(candidate_affiliation) in {_normalise(a) for a in author_affiliations}:
        return AFFILIATION_REASON
    if candidate_id in already_assigned_reviewer_ids:
        return ALREADY_ASSIGNED_REASON
    if active_assignments >= reviewer_capacity:
        return AT_CAPACITY_REASON
    return None


def _normalise(value: str) -> str:
    return value.strip().casefold()
