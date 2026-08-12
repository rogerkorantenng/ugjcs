from fastapi.testclient import TestClient

from ugjcs.api.app import create_app


def test_health_reports_ok_without_touching_the_database() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_document_is_served_so_docs_can_render() -> None:
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]
