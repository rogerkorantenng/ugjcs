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


def test_the_base_url_is_a_signpost_not_a_404() -> None:
    """An API client at `/` learns the service is up and where the application lives."""
    client = TestClient(create_app())
    response = client.get("/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["application"].startswith("http")
    assert body["documentation"] == "/docs"


def test_a_browser_at_the_base_url_gets_a_page_pointing_at_the_application() -> None:
    """The same address answers a browser's Accept header with HTML, not raw JSON."""
    client = TestClient(create_app())
    response = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "The API is running" in response.text
    assert "Open the SDJ Editorial Portal" in response.text
