from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_uow
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor

AUTHOR = new_user_id()
OTHER_AUTHOR = new_user_id()


def make_client(actor: Actor) -> tuple[TestClient, FakeUnitOfWork]:
    app = create_app()
    uow = FakeUnitOfWork()

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    return TestClient(app), uow


def test_an_author_can_submit_a_manuscript() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, uow = make_client(actor)
    response = client.post(
        "/api/v1/manuscripts",
        json={"title": "Sparse Retrieval", "abstract": "An abstract.", "keywords": ["ir"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "submitted"
    assert body["author_ids"] == [str(AUTHOR)]
    assert body["corresponding_author_id"] == str(AUTHOR)
    assert len(uow.manuscripts.store) == 1


def test_a_reviewer_without_the_author_role_cannot_submit() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.REVIEWER}))
    client, _ = make_client(actor)
    response = client.post(
        "/api/v1/manuscripts", json={"title": "X", "abstract": "Y", "keywords": []}
    )
    assert response.status_code == 403


def test_mine_lists_only_the_callers_manuscripts() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    client.post("/api/v1/manuscripts", json={"title": "Mine", "abstract": "A.", "keywords": []})
    response = client.get("/api/v1/manuscripts/mine")
    assert response.status_code == 200
    assert [m["title"] for m in response.json()] == ["Mine"]


def test_retrieving_someone_elses_manuscript_is_forbidden() -> None:
    owner = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(owner)
    created = client.post(
        "/api/v1/manuscripts", json={"title": "Private", "abstract": "A.", "keywords": []}
    ).json()

    stranger = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: stranger  # type: ignore[attr-defined]
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 403


def test_the_owner_can_retrieve_their_own_manuscript() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    created = client.post(
        "/api/v1/manuscripts", json={"title": "Mine", "abstract": "A.", "keywords": []}
    ).json()
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Mine"


def test_an_editor_can_retrieve_any_manuscript() -> None:
    author = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(author)
    created = client.post(
        "/api/v1/manuscripts", json={"title": "Editor Visible", "abstract": "A.", "keywords": []}
    ).json()

    editor = Actor(id=new_user_id(), roles=frozenset({Role.EDITOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: editor  # type: ignore[attr-defined]
    response = client.get(f"/api/v1/manuscripts/{created['tracking_code']}")
    assert response.status_code == 200


def test_a_missing_tracking_code_is_404() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    response = client.get("/api/v1/manuscripts/UGJCS-2026-9999")
    assert response.status_code == 404


def test_a_malformed_tracking_code_is_404_not_a_500() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    response = client.get("/api/v1/manuscripts/not-a-tracking-code")
    assert response.status_code == 404


def test_the_corresponding_author_can_withdraw() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    created = client.post(
        "/api/v1/manuscripts", json={"title": "T", "abstract": "A.", "keywords": []}
    ).json()
    response = client.post(f"/api/v1/manuscripts/{created['tracking_code']}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_a_co_author_who_is_not_corresponding_cannot_withdraw() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    created = client.post(
        "/api/v1/manuscripts",
        json={
            "title": "T",
            "abstract": "A.",
            "keywords": [],
            "co_author_ids": [str(OTHER_AUTHOR)],
        },
    ).json()

    co_author = Actor(id=OTHER_AUTHOR, roles=frozenset({Role.AUTHOR}))
    client.app.dependency_overrides[get_current_actor] = lambda: co_author  # type: ignore[attr-defined]
    response = client.post(f"/api/v1/manuscripts/{created['tracking_code']}/withdraw")
    assert response.status_code == 403


def test_withdrawing_a_missing_manuscript_is_404() -> None:
    actor = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
    client, _ = make_client(actor)
    response = client.post("/api/v1/manuscripts/UGJCS-2026-9999/withdraw")
    assert response.status_code == 404
