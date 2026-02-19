"""Example 模块 notes 接口测试：创建、查询."""

from httpx import AsyncClient


class TestNoteApi:
    """POST /api/v1/notes、GET /api/v1/notes/{id}."""

    async def test_create_note_returns_201_and_id(self, api_client: AsyncClient) -> None:
        resp = await api_client.post(
            "/api/v1/notes",
            json={"title": "Hello", "content": "World"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["message"] == "Note created"
        assert "id" in body["data"]
        assert body["data"]["id"]

    async def test_get_note_after_create(self, api_client: AsyncClient) -> None:
        create = await api_client.post(
            "/api/v1/notes",
            json={"title": "Get me", "content": "Please"},
        )
        assert create.status_code == 200
        note_id = create.json()["data"]["id"]

        get_resp = await api_client.get(f"/api/v1/notes/{note_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "Get me"
        assert data["data"]["content"] == "Please"
        assert data["data"]["id"] == note_id

    async def test_create_note_validation_empty_title(self, api_client: AsyncClient) -> None:
        resp = await api_client.post(
            "/api/v1/notes",
            json={"title": "", "content": "Ok"},
        )
        assert resp.status_code == 422

    async def test_get_note_not_found_returns_404(self, api_client: AsyncClient) -> None:
        resp = await api_client.get("/api/v1/notes/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
