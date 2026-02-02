
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_forget_vs_revoke_semantics(client):
    from plastic_memories.ext.registry import get_storage

    res = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "r1",
            "content": "revoke me",
            "tags": [],
        },
        headers=auth_headers("testkey-a"),
    )
    assert res.status_code == 200
    mem_id = res.json()["data"]["memory_id"]

    revoke = client.post(
        "/memory/revoke",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-a"),
    )
    assert revoke.status_code == 200

    storage = get_storage()
    row = storage.get_memory_by_id("userA", "p1", mem_id)
    assert row is not None
    assert row["status"] == "revoked"

    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "revoke", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert recall.status_code == 200
    assert all(item["id"] != mem_id for item in recall.json()["data"]["PERSONA_MEMORY"])

    res2 = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "f1",
            "content": "forget me",
            "tags": [],
        },
        headers=auth_headers("testkey-a"),
    )
    assert res2.status_code == 200
    mem_id2 = res2.json()["data"]["memory_id"]

    forget = client.post(
        "/memory/forget",
        json={"persona_id": "p1", "type": "preferences", "key": "f1"},
        headers=auth_headers("testkey-a"),
    )
    assert forget.status_code == 200

    row2 = storage.get_memory_by_id("userA", "p1", mem_id2)
    assert row2 is None

    recall2 = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "forget", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert recall2.status_code == 200
    assert all(item["id"] != mem_id2 for item in recall2.json()["data"]["PERSONA_MEMORY"])
