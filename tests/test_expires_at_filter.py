import time


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_expires_at_filtered(client):
    past = int(time.time()) - 10
    res = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "exp1",
            "content": "expired content",
            "tags": [],
            "expires_at": past,
        },
        headers=auth_headers("testkey-a"),
    )
    assert res.status_code == 200
    mem_id = res.json()["data"]["memory_id"]

    listed = client.get(
        "/memory/list",
        params={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    assert listed.status_code == 200
    assert all(item["id"] != mem_id for item in listed.json()["data"]["items"])

    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "expired", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert recall.status_code == 200
    items = recall.json()["data"]["PERSONA_MEMORY"]
    assert all(item["id"] != mem_id for item in items)
