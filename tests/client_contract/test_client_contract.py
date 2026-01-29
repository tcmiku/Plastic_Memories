import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT_ROOT = ROOT / "clients" / "python"
if str(CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(CLIENT_ROOT))

import pytest
from httpx import ASGITransport
import httpx
import anyio

from plastic_memories.api import app
from plastic_memories.ext.registry import get_storage

from plastic_memories_client import PlasticMemoriesClient, Message
from plastic_memories_client.errors import PlasticMemoriesError


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return PlasticMemoriesClient(base_url="http://test", user_id="u1", persona_id="default", transport=transport)


def test_health_and_capabilities(client):
    data = client.health()
    assert "status" in data
    caps = client.capabilities()
    for key in ["backend", "recall", "judge", "profile", "sensitive", "events"]:
        assert key in caps


def test_persona_create_idempotent(client):
    client.persona_create(meta={"display_name": "Ava", "description": "Primary"})
    client.persona_create(meta={"display_name": "Ava", "description": "Primary"})


def test_write_and_recall_injection_block(client):
    client.append_messages([
        Message(role="user", content="请用默认中文"),
        Message(role="user", content="回答工程化"),
    ])
    client.write([
        Message(role="user", content="叫我 tcmiku"),
    ])
    client.write([
        Message(role="user", content="叫我 tcmiku"),
    ])
    result = client.recall("我喜欢什么风格的回答？")
    assert result.injection_block
    assert "PERSONA_PROFILE" in result.injection_block
    assert "PERSONA_MEMORY" in result.injection_block
    assert result.request_id is not None


def test_full_flow_and_listing(client):
    client.append_messages([
        Message(role="user", content="你好"),
    ])
    client.write([
        Message(role="user", content="我喜欢简洁"),
    ])
    profile = client.persona_profile()
    assert "profile_markdown" in profile
    listed = client.list_memory()
    assert "items" in listed
    if listed["items"]:
        item = listed["items"][0]
        client.forget_memory(match={"type": item.get("type"), "key": item.get("mkey")})
    client.purge_messages(older_than_days=1)
    client._request("POST", "/memory/rebuild", json_body={"user_id": "u1", "persona_id": "default"})


def test_fts_fallback_path(client):
    storage = get_storage()
    storage._fts_enabled = False
    client.recall("简洁")


def test_error_envelope_mapping(client):
    with pytest.raises(PlasticMemoriesError) as exc:
        client.recall(None)  # type: ignore[arg-type]
    assert exc.value.request_id is not None


def test_http_error_mapping(client):
    with pytest.raises(PlasticMemoriesError) as exc:
        client.write([Message(role="user", content="my password is 123")])
    assert exc.value.code == "http_error"


def test_index_page():
    transport = ASGITransport(app=app)
    async def _fetch():
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/")
            return res.text
    html = anyio.run(_fetch)
    assert "Plastic Memories API" in html
