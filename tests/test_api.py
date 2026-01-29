import pytest
from httpx import AsyncClient, ASGITransport

from plastic_memories.utils import now_ts

from plastic_memories.api import app


@pytest.mark.anyio
async def test_health_and_capabilities():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        res = await client.get("/capabilities")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True


@pytest.mark.anyio
async def test_memory_write_skip_and_recall():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/memory/write", json={
            "user_id": "u", "persona_id": "p", "type": "persona", "key": "name",
            "content": "temp", "temporary": True
        })
        assert res.json()["data"]["status"] == "skipped"
        res = await client.post("/memory/write", json={
            "user_id": "u", "persona_id": "p", "type": "persona", "key": "name",
            "content": "Alice"
        })
        assert res.status_code == 200
        res = await client.post("/memory/recall", json={
            "user_id": "u", "persona_id": "p", "query": "Alice", "limit": 5
        })
        body = res.json()["data"]
        assert "PERSONA_PROFILE" in body
        assert "PERSONA_MEMORY" in body
        assert "CHAT_SNIPPETS" in body


@pytest.mark.anyio
async def test_sensitive_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/memory/write", json={
            "user_id": "u", "persona_id": "p", "type": "rule", "key": "secret",
            "content": "password 123"
        })
        assert res.status_code == 400
        body = res.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "http_error"


@pytest.mark.anyio
async def test_invalid_memory_type_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/memory/write", json={
            "user_id": "u", "persona_id": "p", "type": "invalid", "key": "x",
            "content": "nope"
        })
        assert res.status_code == 422
        body = res.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "validation_error"


@pytest.mark.anyio
async def test_messages_memory_and_metrics_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/persona/create", json={
            "user_id": "u2", "persona_id": "default", "display_name": "Ava", "description": "Primary"
        })
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.post("/messages/append", json={
            "user_id": "u2", "persona_id": "default", "session_id": "s1",
            "source_app": "cli", "role": "user", "content": "Hello"
        })
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.get("/messages/recent", params={"user_id": "u2", "persona_id": "default", "limit": 10})
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.post("/messages/purge", json={
            "user_id": "u2", "persona_id": "default", "before_ts": now_ts() + 1
        })
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.post("/memory/write", json={
            "user_id": "u2", "persona_id": "default", "type": "preferences", "key": "tone",
            "content": "Short"
        })
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.get("/memory/list", params={"user_id": "u2", "persona_id": "default"})
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.post("/memory/forget", json={
            "user_id": "u2", "persona_id": "default", "type": "preferences", "key": "tone"
        })
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.post("/memory/rebuild", json={"user_id": "u2", "persona_id": "default"})
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.get("/persona/profile", params={"user_id": "u2", "persona_id": "default"})
        assert res.status_code == 200
        assert res.json()["ok"] is True
        res = await client.get("/metrics")
        assert res.status_code == 200
        assert res.json()["ok"] is True


@pytest.mark.anyio
async def test_request_id_header_and_error_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health", headers={"X-Request-Id": "rid-123"})
        assert res.headers.get("X-Request-Id") == "rid-123"
        res = await client.post("/memory/write", json={
            "user_id": "u", "persona_id": "p", "type": "rule", "key": "secret",
            "content": "password 123"
        }, headers={"X-Request-Id": "rid-456"})
        body = res.json()
        assert body["ok"] is False
        assert body["request_id"] == "rid-456"
