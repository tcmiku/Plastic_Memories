import json


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_conflict_resolution_supersedes_chain(client):
    from plastic_memories.ext.registry import get_storage

    write_a = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "pref-a",
            "content": "A",
            "tags": [],
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_a.status_code == 200
    mem_a = write_a.json()["data"]["memory_id"]

    confirm_a = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_a},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_a.status_code == 200

    write_b = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "pref-b",
            "content": "B",
            "tags": [],
            "source_type": "user_explicit",
            "supersedes_id": mem_a,
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_b.status_code == 200
    mem_b = write_b.json()["data"]["memory_id"]

    confirm_b = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_b, "supersedes_id": mem_a},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_b.status_code == 200

    slots = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    items = slots.json()["data"]["items"]
    pref = next(item for item in items if item["slot_name"] == "preferences")
    assert json.loads(pref["value_json"])["text"] == "B"

    storage = get_storage()
    row_a = storage.get_memory_by_id("userA", "p1", mem_a)
    row_b = storage.get_memory_by_id("userA", "p1", mem_b)
    assert row_a["status"] == "revoked"
    assert row_b["status"] == "active"
    assert row_b["supersedes_id"] == mem_a

    listed = client.get(
        "/memory/list",
        params={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    prefs = [item for item in listed.json()["data"]["items"] if item["type"] == "preferences"]
    assert len(prefs) == 1
    assert prefs[0]["content"] == "B"


def test_conflict_requires_supersedes(client):
    from plastic_memories.ext.registry import get_storage

    write_a = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "pref-a",
            "content": "A",
            "tags": [],
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_a.status_code == 200
    mem_a = write_a.json()["data"]["memory_id"]
    confirm_a = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_a},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_a.status_code == 200

    write_b = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "pref-b",
            "content": "B",
            "tags": [],
            "source_type": "user_explicit",
            "supersedes_id": mem_a,
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_b.status_code == 200
    mem_b = write_b.json()["data"]["memory_id"]
    confirm_b = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_b, "supersedes_id": mem_a},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_b.status_code == 200

    write_c = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "pref-c",
            "content": "C",
            "tags": [],
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_c.status_code == 200
    mem_c = write_c.json()["data"]["memory_id"]

    confirm_c = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_c},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_c.status_code == 409
    body = confirm_c.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "conflict_requires_supersedes"

    slots = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    pref = next(item for item in slots.json()["data"]["items"] if item["slot_name"] == "preferences")
    assert json.loads(pref["value_json"])["text"] == "B"

    storage = get_storage()
    row_c = storage.get_memory_by_id("userA", "p1", mem_c)
    assert row_c["status"] != "active"
