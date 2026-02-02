
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_recall_after_revoke_no_ghost(client):
    payload = {
        "persona_id": "p1",
        "type": "preferences",
        "key": "pref-ghost",
        "content": "orchid tea is great",
        "tags": [],
    }
    res = client.post("/memory/write", json=payload, headers=auth_headers("testkey-a"))
    assert res.status_code == 200
    mem_id = res.json()["data"]["memory_id"]
    confirm = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-a"),
    )
    assert confirm.status_code == 200

    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "orchid", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert recall.status_code == 200
    items = recall.json()["data"]["PERSONA_MEMORY"]
    assert any(item["id"] == mem_id for item in items)

    revoke = client.post(
        "/memory/revoke",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-a"),
    )
    assert revoke.status_code == 200

    recall2 = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "orchid", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert recall2.status_code == 200
    items2 = recall2.json()["data"]["PERSONA_MEMORY"]
    assert all(item["id"] != mem_id for item in items2)
