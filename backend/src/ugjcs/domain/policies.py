"""Authorisation, expressed once and denied by default.

Role grants cover actions that depend only on who the actor is. Actions that also
depend on the actor's relationship to a specific manuscript are handled by explicit
predicates, because encoding ownership in a role table silently over-grants.

What this does NOT do, stated plainly so no caller assumes more than it provides:
`REVIEW` is a role grant with no per-manuscript predicate. There is no assignment to
check against yet, so the policy cannot ask whether this reviewer was invited to this
manuscript, nor whether they are one of its authors. Conflict-of-interest exclusion and
assignment checking arrive with reviewer assignment in a later plan; until then an actor
holding both AUTHOR and REVIEWER is not prevented here from reviewing their own work.
That gap is recorded in the technical debt register.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ugjcs.domain.enums import Role
from ugjcs.domain.errors import AuthorizationDeniedError
from ugjcs.domain.ids import UserId
from ugjcs.domain.manuscript import Manuscript


class Action(StrEnum):
    VIEW = "view"
    SUBMIT = "submit"
    SCREEN = "screen"
    ASSIGN_REVIEWER = "assign_reviewer"
    REVIEW = "review"
    DECIDE = "decide"
    RESUBMIT = "resubmit"
    PUBLISH = "publish"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT = "view_audit"


@dataclass(frozen=True, slots=True)
class Actor:
    id: UserId
    roles: frozenset[Role]


_ROLE_GRANTS: Mapping[Action, frozenset[Role]] = {
    Action.SUBMIT: frozenset({Role.AUTHOR}),
    Action.SCREEN: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
    Action.ASSIGN_REVIEWER: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
    Action.REVIEW: frozenset({Role.REVIEWER}),
    Action.DECIDE: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
    Action.PUBLISH: frozenset({Role.EDITOR_IN_CHIEF}),
    Action.MANAGE_USERS: frozenset({Role.ADMINISTRATOR}),
    Action.VIEW_AUDIT: frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF}),
}

_OWNERSHIP_ACTIONS = frozenset({Action.RESUBMIT})


def can(actor: Actor, action: Action, manuscript: Manuscript | None = None) -> bool:
    """Whether `actor` may perform `action`, optionally against `manuscript`."""
    if action in _OWNERSHIP_ACTIONS:
        return (
            manuscript is not None
            and Role.AUTHOR in actor.roles
            and actor.id == manuscript.corresponding_author_id
        )
    if action is Action.VIEW:
        return _can_view(actor, manuscript)
    return bool(actor.roles & _ROLE_GRANTS.get(action, frozenset()))


def _can_view(actor: Actor, manuscript: Manuscript | None) -> bool:
    if manuscript is None:
        return False
    if actor.roles & {Role.EDITOR, Role.EDITOR_IN_CHIEF, Role.ADMINISTRATOR}:
        return True
    return actor.id in manuscript.author_ids


def authorize(actor: Actor, action: Action, manuscript: Manuscript | None = None) -> None:
    """Raise `AuthorizationDeniedError` unless the action is permitted."""
    if not can(actor, action, manuscript):
        raise AuthorizationDeniedError(f"actor {actor.id} may not {action.value}")
