"""The editorial decision certificate's gates: roles, missing decision, missing paper.

Content assertions live in `test_certificate_router.py`; shared fixtures in
`certificate_fixtures.py`.
"""

from tests.unit.api.certificate_fixtures import (
    AUTHOR,
    EDITOR,
    NOW,
    REVIEWER_ONE,
    accepted_manuscript,
    bare_manuscript,
    fetch,
    make_client,
)
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor


def test_an_author_may_not_fetch_a_certificate() -> None:
    manuscript = accepted_manuscript(404)
    client, _ = make_client(manuscript, Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR})))
    assert fetch(client, manuscript.tracking_code.value).status_code == 403


def test_a_reviewer_may_not_fetch_a_certificate() -> None:
    manuscript = accepted_manuscript(405)
    actor = Actor(id=REVIEWER_ONE, roles=frozenset({Role.REVIEWER}))
    client, _ = make_client(manuscript, actor)
    assert fetch(client, manuscript.tracking_code.value).status_code == 403


def test_a_manuscript_without_a_final_decision_is_409() -> None:
    manuscript = bare_manuscript(406, title="Undecided")
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    client, _ = make_client(manuscript, Actor(id=EDITOR, roles=frozenset({Role.EDITOR})))
    assert fetch(client, manuscript.tracking_code.value).status_code == 409


def test_a_missing_tracking_code_is_404() -> None:
    manuscript = accepted_manuscript(407)
    client, _ = make_client(manuscript, Actor(id=EDITOR, roles=frozenset({Role.EDITOR})))
    assert fetch(client, "SDJ-2026-9999").status_code == 404
