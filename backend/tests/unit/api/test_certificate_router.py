"""The editorial decision certificate's content: PDF shape and blind-safety.

Authorisation and conflict gating live in `test_certificate_auth.py`; the fixtures both
files share live in `certificate_fixtures.py`.
"""

from tests.unit.api.certificate_fixtures import (
    CONFIDENTIAL_SENTINEL,
    EDITOR,
    REVIEWER_ONE,
    REVIEWER_TWO,
    accepted_manuscript,
    add_submitted_reviews,
    fetch,
    make_client,
    pdf_text,
)
from tests.unit.api.fakes import new_user_id
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor


def test_an_editor_receives_a_pdf_certificate() -> None:
    manuscript = accepted_manuscript()
    client, uow = make_client(manuscript, Actor(id=EDITOR, roles=frozenset({Role.EDITOR})))
    add_submitted_reviews(uow, manuscript)
    response = fetch(client, manuscript.tracking_code.value)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    text = pdf_text(response.content)
    assert "Editorial Decision Certificate" in text
    assert manuscript.tracking_code.value in text
    assert "Certified Findings" in text
    assert "Decision: accept" in text
    assert "Strong contribution to scheduling." in text
    assert "Reviewer 1" in text
    assert "Reviewer 2" in text
    assert uow.manuscripts.chains[manuscript.id][-1].event_hash in text


def test_the_editor_in_chief_may_also_fetch_a_certificate() -> None:
    manuscript = accepted_manuscript(402)
    actor = Actor(id=new_user_id(), roles=frozenset({Role.EDITOR_IN_CHIEF}))
    client, uow = make_client(manuscript, actor)
    add_submitted_reviews(uow, manuscript)
    assert fetch(client, manuscript.tracking_code.value).status_code == 200


def test_the_certificate_never_names_a_reviewer_or_leaks_confidential_comments() -> None:
    manuscript = accepted_manuscript(403)
    client, uow = make_client(manuscript, Actor(id=EDITOR, roles=frozenset({Role.EDITOR})))
    add_submitted_reviews(uow, manuscript)
    response = fetch(client, manuscript.tracking_code.value)
    assert response.status_code == 200
    text = pdf_text(response.content)
    for forbidden in (str(REVIEWER_ONE), str(REVIEWER_TWO), CONFIDENTIAL_SENTINEL):
        assert forbidden.encode() not in response.content
        assert forbidden not in text
