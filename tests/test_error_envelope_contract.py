
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def _assert_envelope(body: dict):
    assert body.get("ok") is False
    assert body.get("request_id")
    err = body.get("error") or {}
    assert err.get("code")
    assert err.get("message")


def test_envelope_401(client):
    res = client.post("/memory/write", json={"persona_id": "p1"})
    assert res.status_code in (401, 403)
    _assert_envelope(res.json())


def test_envelope_422(client):
    res = client.post(
        "/memory/write",
        json={"persona_id": "p1", "type": "preferences"},
        headers=auth_headers("testkey-a"),
    )
    assert res.status_code == 422
    _assert_envelope(res.json())


def test_envelope_500(client):
    from fastapi.testclient import TestClient
    from plastic_memories.api import app

    local_client = TestClient(app, raise_server_exceptions=False)
    res = local_client.post("/_test/boom", headers=auth_headers("testkey-a"))
    assert res.status_code == 500
    _assert_envelope(res.json())
