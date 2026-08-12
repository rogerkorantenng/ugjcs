from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import Role
from ugjcs.domain.errors import AuthorizationDeniedError
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Action, Actor, authorize, can

AUTHOR_ID = UserId(uuid4())
OTHER_ID = UserId(uuid4())
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def actor(*roles: Role, user_id: UserId | None = None) -> Actor:
    return Actor(id=user_id or UserId(uuid4()), roles=frozenset(roles))


def manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 3),
        title="Federated Learning for Rural Clinics",
        abstract="A federated approach to clinical prediction under bandwidth limits.",
        keywords=("federated learning",),
        author_ids=(AUTHOR_ID,),
        corresponding_author_id=AUTHOR_ID,
    )


def test_editor_may_screen() -> None:
    assert can(actor(Role.EDITOR), Action.SCREEN, manuscript())


def test_author_may_not_screen() -> None:
    assert not can(actor(Role.AUTHOR), Action.SCREEN, manuscript())


def test_reviewer_may_not_decide() -> None:
    assert not can(actor(Role.REVIEWER), Action.DECIDE, manuscript())


def test_editor_in_chief_may_publish() -> None:
    assert can(actor(Role.EDITOR_IN_CHIEF), Action.PUBLISH, manuscript())


def test_editor_may_not_publish() -> None:
    assert not can(actor(Role.EDITOR), Action.PUBLISH, manuscript())


def test_corresponding_author_may_resubmit_own_manuscript() -> None:
    assert can(actor(Role.AUTHOR, user_id=AUTHOR_ID), Action.RESUBMIT, manuscript())


def test_another_author_may_not_resubmit_someone_elses_manuscript() -> None:
    assert not can(actor(Role.AUTHOR, user_id=OTHER_ID), Action.RESUBMIT, manuscript())


def test_administrator_may_manage_users() -> None:
    assert can(actor(Role.ADMINISTRATOR), Action.MANAGE_USERS)


def test_editor_may_not_manage_users() -> None:
    assert not can(actor(Role.EDITOR), Action.MANAGE_USERS)


def test_unknown_role_combination_is_denied_by_default() -> None:
    assert not can(actor(), Action.DECIDE, manuscript())


def test_multiple_roles_grant_the_union_of_permissions() -> None:
    dual = actor(Role.AUTHOR, Role.EDITOR, user_id=AUTHOR_ID)
    assert can(dual, Action.SCREEN, manuscript())
    assert can(dual, Action.RESUBMIT, manuscript())


def test_editor_may_view_any_manuscript() -> None:
    assert can(actor(Role.EDITOR), Action.VIEW, manuscript())


def test_administrator_may_view_any_manuscript() -> None:
    assert can(actor(Role.ADMINISTRATOR), Action.VIEW, manuscript())


def test_author_may_view_their_own_manuscript() -> None:
    assert can(actor(Role.AUTHOR, user_id=AUTHOR_ID), Action.VIEW, manuscript())


def test_author_may_not_view_someone_elses_manuscript() -> None:
    assert not can(actor(Role.AUTHOR, user_id=OTHER_ID), Action.VIEW, manuscript())


def test_reviewer_has_no_unblinded_view() -> None:
    """VIEW is denied to a bare reviewer, so no reviewer obtains the unblinded aggregate.

    VIEW yields the full aggregate including author identities, so if this ever returns
    True the double-blind guarantee is gone. What the policy layer does not yet do is
    grant reviewers the blinded projection: no `Action` maps to `blind()`, so this test
    proves the denial and nothing about the permitted path. Wiring `blinding.blind` to an
    authorisation action is future work.
    """
    assert not can(actor(Role.REVIEWER), Action.VIEW, manuscript())


def test_view_is_denied_when_no_manuscript_is_supplied() -> None:
    assert not can(actor(Role.EDITOR), Action.VIEW)


def test_authorize_is_silent_when_permitted() -> None:
    authorize(actor(Role.EDITOR), Action.SCREEN, manuscript())


def test_authorize_raises_when_denied() -> None:
    with pytest.raises(AuthorizationDeniedError, match="screen"):
        authorize(actor(Role.AUTHOR), Action.SCREEN, manuscript())
