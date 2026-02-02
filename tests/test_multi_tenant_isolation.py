
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_multi_tenant_isolation_confirm_revoke(client):
    payload = {
        "persona_id": "p1",
        "type": "preferences",
        "key": "pref-iso",
        "content": "likes tea",
        "tags": [],
        "source_type": "model_inferred",
    }
    res = client.post("/memory/write", json=payload, headers=auth_headers("testkey-a"))
    assert res.status_code == 200
    mem_id = res.json()["data"]["memory_id"]

    other_confirm = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-b"),
    )
    assert other_confirm.status_code in (403, 404)

    other_revoke = client.post(
        "/memory/revoke",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-b"),
    )
    assert other_revoke.status_code in (403, 404)
