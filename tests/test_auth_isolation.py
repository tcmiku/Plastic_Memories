import pytest


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_memory_write_requires_auth(client):
    payload = {
        "persona_id": "p1",
        "type": "preferences",
        "key": "k1",
        "content": "likes tea",
        "tags": [],
    }
    res = client.post("/memory/write", json=payload)
    assert res.status_code in (401, 403)
    body = res.json()
    assert body.get("ok") is False


def test_memory_write_with_auth(client):
    payload = {
        "persona_id": "p1",
        "type": "preferences",
        "key": "k1",
        "content": "likes tea",
        "tags": [],
    }
    res = client.post("/memory/write", json=payload, headers=auth_headers("testkey-a"))
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is True
