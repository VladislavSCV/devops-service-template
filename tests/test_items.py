from fastapi.testclient import TestClient


def _create(client: TestClient, **fields) -> dict:
    payload = {"title": "Example", "url": "https://example.com/", "note": "hello"} | fields
    response = client.post("/api/items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get(client: TestClient) -> None:
    created = _create(client)
    assert created["id"] > 0
    assert created["title"] == "Example"
    assert created["url"] == "https://example.com/"

    response = client.get(f"/api/items/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_list_paginates_newest_first(client: TestClient) -> None:
    ids = [_create(client, title=f"item {i}")["id"] for i in range(3)]

    page = client.get("/api/items", params={"limit": 2}).json()
    assert page["total"] == 3
    assert page["limit"] == 2
    assert [i["id"] for i in page["items"]] == [ids[2], ids[1]]

    page2 = client.get("/api/items", params={"limit": 2, "offset": 2}).json()
    assert [i["id"] for i in page2["items"]] == [ids[0]]


def test_list_limit_is_capped(client: TestClient) -> None:
    assert client.get("/api/items", params={"limit": 10_000}).json()["limit"] == 100


def test_update(client: TestClient) -> None:
    item = _create(client)
    response = client.patch(f"/api/items/{item['id']}", json={"title": "Renamed", "url": None})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed"
    assert body["url"] is None
    assert body["note"] == "hello"  # untouched


def test_delete(client: TestClient) -> None:
    item = _create(client)
    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.get(f"/api/items/{item['id']}").status_code == 404
    assert client.delete(f"/api/items/{item['id']}").status_code == 404


def test_validation_errors(client: TestClient) -> None:
    assert client.post("/api/items", json={"title": ""}).status_code == 422
    assert client.post("/api/items", json={"title": "x", "url": "not-a-url"}).status_code == 422
    assert client.get("/api/items/abc").status_code == 422


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/items/999").status_code == 404
    assert client.patch("/api/items/999", json={"title": "x"}).status_code == 404
