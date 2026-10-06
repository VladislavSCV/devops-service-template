import pytest
from fastapi.testclient import TestClient

from app import db


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_ready_fails_when_db_is_down(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_ping() -> None:
        raise ConnectionError("db is down")

    monkeypatch.setattr(db, "ping", broken_ping)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_request_id_header(client: TestClient) -> None:
    assert client.get("/health").headers["x-request-id"]
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["x-request-id"] == "abc123"


def test_metrics_exposes_request_metrics(client: TestClient) -> None:
    client.post("/api/items", json={"title": "metrics"})
    client.get("/api/items/12345")  # 404, recorded under the route template
    client.get("/openapi.json")  # plain Starlette route
    client.get("/no/such/path")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text

    assert "http_requests_in_progress" in body
    assert "http_request_duration_seconds_bucket" in body
    assert 'http_requests_total{handler="/api/items",method="POST",status="201"}' in body
    assert 'http_requests_total{handler="/api/items/{item_id}",method="GET",status="404"}' in body
    assert 'handler="/openapi.json",method="GET",status="200"' in body
    assert 'handler="__unmatched__",method="GET",status="404"' in body
    assert "/api/items/12345" not in body  # no raw paths -> bounded label cardinality
    assert "/no/such/path" not in body
