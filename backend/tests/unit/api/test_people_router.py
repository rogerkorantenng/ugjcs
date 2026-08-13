"""Unit tests for `GET /api/v1/people/lookup`."""

from collections.abc import AsyncIterator, Iterable

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeAccount, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor

ANY_ACTOR = new_user_id()


def make_client(actor: Actor, accounts: Iterable[FakeAccount] = ()) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for account in accounts:
        uow.accounts.accounts[account.id] = account

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


def test_looking_up_a_known_email_returns_the_person() -> None:
    person = FakeAccount(
        id=new_user_id(),
        email="colleague@sdj.test",
        roles=frozenset({Role.AUTHOR}),
        full_name="Ada Boateng",
        affiliation="University of Ghana",
    )
    actor = Actor(id=ANY_ACTOR, roles=frozenset({Role.AUTHOR}))
    client = make_client(actor, [person])

    response = client.get("/api/v1/people/lookup", params={"email": "COLLEAGUE@SDJ.TEST"})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": str(person.id),
        "full_name": "Ada Boateng",
        "affiliation": "University of Ghana",
    }
    assert "email" not in body


def test_looking_up_an_unknown_email_is_404() -> None:
    actor = Actor(id=ANY_ACTOR, roles=frozenset({Role.AUTHOR}))
    client = make_client(actor)

    response = client.get("/api/v1/people/lookup", params={"email": "nobody@sdj.test"})

    assert response.status_code == 404


def test_a_malformed_email_is_also_404_not_a_validation_error() -> None:
    """No hint at all about what makes an address valid — the same 404 a well-formed but
    unregistered address gets, so a malformed guess reveals nothing extra."""
    actor = Actor(id=ANY_ACTOR, roles=frozenset({Role.AUTHOR}))
    client = make_client(actor)

    response = client.get("/api/v1/people/lookup", params={"email": "not-an-email"})

    assert response.status_code == 404


def test_any_authenticated_role_may_look_someone_up() -> None:
    person = FakeAccount(
        id=new_user_id(),
        email="reviewer-target@sdj.test",
        roles=frozenset({Role.REVIEWER}),
        full_name="Kojo Mensah",
        affiliation="KNUST",
    )
    actor = Actor(id=ANY_ACTOR, roles=frozenset({Role.REVIEWER}))
    client = make_client(actor, [person])

    response = client.get("/api/v1/people/lookup", params={"email": "reviewer-target@sdj.test"})

    assert response.status_code == 200
