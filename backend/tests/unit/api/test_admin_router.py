"""The admin console: roster listing, role grants, capacity, activation — and the two
refusals that define it (no administrator-role changes, no self-deactivation).

These tests plant real domain `Account` aggregates in the fake repository rather than
`FakeAccount`s: the admin routes exercise `grant`/`revoke`/`deactivate`/`reactivate`,
which only the aggregate carries, and `AdminAccountOut.from_domain` reads the
`EmailAddress` value object. The `type: ignore` on each plant is the price of reusing
the shared fake, already paid the same way by `FakeAccountRepository.add`.
"""

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.domain.policies import Actor

ADMIN = new_user_id()
ADMIN_ACTOR = Actor(id=ADMIN, roles=frozenset({Role.ADMINISTRATOR}))


def domain_account(email: str, *roles: Role, user_id: UserId | None = None) -> Account:
    account = Account(
        id=user_id if user_id is not None else new_user_id(),
        email=EmailAddress(email),
        password_hash="argon2-hash",
        full_name="Ama Mensah",
        affiliation="University of Ghana",
        is_verified=True,
    )
    for role in roles:
        account.grant(role)
    return account


def make_client(actor: Actor, *accounts: Account) -> TestClient:
    app = create_app()
    uow = FakeUnitOfWork()
    for account in accounts:
        uow.accounts.accounts[account.id] = account  # type: ignore[assignment]

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app)


# --- authorization guards ------------------------------------------------------------


def test_every_admin_route_is_forbidden_to_non_administrators() -> None:
    """Each editorial and authoring role in turn: MANAGE_USERS is granted to
    administrators alone, and every route in the console is behind it."""
    target = domain_account("target@sdj.test", Role.AUTHOR)
    for role in (Role.AUTHOR, Role.REVIEWER, Role.EDITOR, Role.EDITOR_IN_CHIEF):
        client = make_client(Actor(id=new_user_id(), roles=frozenset({role})), target)
        assert client.get("/api/v1/admin/accounts").status_code == 403
        assert (
            client.post(
                f"/api/v1/admin/accounts/{target.id}/roles",
                json={"role": "reviewer", "grant": True},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/admin/accounts/{target.id}/capacity", json={"reviewer_capacity": 3}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/admin/accounts/{target.id}/active", json={"is_active": False}
            ).status_code
            == 403
        )


def test_admin_routes_require_authentication() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/admin/accounts").status_code == 401


# --- the roster ----------------------------------------------------------------------


def test_the_roster_lists_every_account_with_its_administrative_shape() -> None:
    reviewer = domain_account("reviewer@sdj.test", Role.AUTHOR, Role.REVIEWER)
    inactive = domain_account("inactive@sdj.test", Role.AUTHOR)
    inactive.deactivate()
    client = make_client(ADMIN_ACTOR, reviewer, inactive)

    response = client.get("/api/v1/admin/accounts")
    assert response.status_code == 200
    body = response.json()
    by_email = {entry["email"]: entry for entry in body}
    assert set(by_email) == {"reviewer@sdj.test", "inactive@sdj.test"}
    entry = by_email["reviewer@sdj.test"]
    assert entry["id"] == str(reviewer.id)
    assert entry["full_name"] == "Ama Mensah"
    assert entry["affiliation"] == "University of Ghana"
    assert entry["roles"] == ["author", "reviewer"]  # sorted, stable
    assert entry["reviewer_capacity"] == 3
    assert entry["is_active"] is True
    assert entry["is_verified"] is True
    # The console must see the accounts it exists to fix — inactive ones included.
    assert by_email["inactive@sdj.test"]["is_active"] is False


# --- roles ---------------------------------------------------------------------------


def test_granting_the_reviewer_role_adds_it() -> None:
    target = domain_account("author@sdj.test", Role.AUTHOR)
    client = make_client(ADMIN_ACTOR, target)
    response = client.post(
        f"/api/v1/admin/accounts/{target.id}/roles", json={"role": "reviewer", "grant": True}
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["author", "reviewer"]
    assert Role.REVIEWER in target.roles


def test_revoking_a_held_role_removes_it() -> None:
    target = domain_account("both@sdj.test", Role.AUTHOR, Role.REVIEWER)
    client = make_client(ADMIN_ACTOR, target)
    response = client.post(
        f"/api/v1/admin/accounts/{target.id}/roles", json={"role": "reviewer", "grant": False}
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["author"]


def test_revoking_a_role_the_account_does_not_hold_is_a_400() -> None:
    target = domain_account("author@sdj.test", Role.AUTHOR)
    client = make_client(ADMIN_ACTOR, target)
    response = client.post(
        f"/api/v1/admin/accounts/{target.id}/roles", json={"role": "editor", "grant": False}
    )
    assert response.status_code == 400  # AccountError via the problem-details handler


def test_the_administrator_role_can_be_neither_granted_nor_revoked() -> None:
    admin_account = domain_account("admin@sdj.test", Role.ADMINISTRATOR, user_id=ADMIN)
    target = domain_account("target@sdj.test", Role.AUTHOR)
    client = make_client(ADMIN_ACTOR, admin_account, target)
    for grant in (True, False):
        response = client.post(
            f"/api/v1/admin/accounts/{target.id}/roles",
            json={"role": "administrator", "grant": grant},
        )
        assert response.status_code == 403
    assert Role.ADMINISTRATOR not in target.roles


def test_an_unknown_role_is_a_422() -> None:
    target = domain_account("author@sdj.test", Role.AUTHOR)
    client = make_client(ADMIN_ACTOR, target)
    response = client.post(
        f"/api/v1/admin/accounts/{target.id}/roles", json={"role": "supervisor", "grant": True}
    )
    assert response.status_code == 422


def test_changing_roles_on_a_missing_account_is_a_404() -> None:
    client = make_client(ADMIN_ACTOR)
    response = client.post(
        f"/api/v1/admin/accounts/{uuid4()}/roles", json={"role": "reviewer", "grant": True}
    )
    assert response.status_code == 404


# --- capacity ------------------------------------------------------------------------


def test_capacity_can_be_set_within_one_to_ten() -> None:
    target = domain_account("reviewer@sdj.test", Role.REVIEWER)
    client = make_client(ADMIN_ACTOR, target)
    response = client.post(
        f"/api/v1/admin/accounts/{target.id}/capacity", json={"reviewer_capacity": 7}
    )
    assert response.status_code == 200
    assert response.json()["reviewer_capacity"] == 7
    assert target.reviewer_capacity == 7


def test_capacity_outside_one_to_ten_is_a_422() -> None:
    target = domain_account("reviewer@sdj.test", Role.REVIEWER)
    client = make_client(ADMIN_ACTOR, target)
    for capacity in (0, 11, -1):
        response = client.post(
            f"/api/v1/admin/accounts/{target.id}/capacity",
            json={"reviewer_capacity": capacity},
        )
        assert response.status_code == 422
    assert target.reviewer_capacity == 3  # untouched


# --- activation ----------------------------------------------------------------------


def test_an_administrator_can_deactivate_and_reactivate_another_account() -> None:
    target = domain_account("target@sdj.test", Role.AUTHOR)
    client = make_client(ADMIN_ACTOR, target)
    deactivated = client.post(
        f"/api/v1/admin/accounts/{target.id}/active", json={"is_active": False}
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert target.is_active is False

    reactivated = client.post(
        f"/api/v1/admin/accounts/{target.id}/active", json={"is_active": True}
    )
    assert reactivated.status_code == 200
    assert target.is_active is True


def test_an_administrator_cannot_deactivate_their_own_account() -> None:
    admin_account = domain_account("admin@sdj.test", Role.ADMINISTRATOR, user_id=ADMIN)
    client = make_client(ADMIN_ACTOR, admin_account)
    response = client.post(
        f"/api/v1/admin/accounts/{UUID(str(ADMIN))}/active", json={"is_active": False}
    )
    assert response.status_code == 409
    assert admin_account.is_active is True
