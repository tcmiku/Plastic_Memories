import json


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_docs_examples_contract(client):
    from plastic_memories.ext.registry import get_storage

    write_id = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "identity",
            "key": "id1",
            "content": "dev",
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_id.status_code == 200
    data = write_id.json()["data"]
    assert data["memory_status"] == "candidate"
    mem_id = data["memory_id"]

    confirm_id = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_id.status_code == 200
    assert confirm_id.json()["data"]["memory_status"] == "active"

    slots = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    items = slots.json()["data"]["items"]
    identity = next(item for item in items if item["slot_name"] == "identity")
    assert json.loads(identity["value_json"])["text"] == "dev"

    write_a = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "preferences",
            "key": "pref-a",
            "content": "A",
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
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
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    mem_b = write_b.json()["data"]["memory_id"]

    conflict = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_b},
        headers=auth_headers("testkey-a"),
    )
    assert conflict.status_code == 409
    body = conflict.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "conflict_requires_supersedes"

    confirm_b = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_b, "supersedes_id": mem_a},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_b.status_code == 200

    storage = get_storage()
    row_a = storage.get_memory_by_id("userA", "p1", mem_a)
    row_b = storage.get_memory_by_id("userA", "p1", mem_b)
    assert row_a["status"] == "revoked"
    assert row_b["status"] == "active"

    slots2 = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    pref = next(item for item in slots2.json()["data"]["items"] if item["slot_name"] == "preferences")
    assert json.loads(pref["value_json"])["text"] == "B"

    revoke = client.post(
        "/memory/revoke",
        json={"persona_id": "p1", "memory_id": mem_b},
        headers=auth_headers("testkey-a"),
    )
    assert revoke.status_code == 200
    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "B", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert all(item["id"] != mem_b for item in recall.json()["data"]["PERSONA_MEMORY"])

    write_f = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "glossary",
            "key": "g1",
            "content": "forget me",
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    mem_f = write_f.json()["data"]["memory_id"]
    confirm_f = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_f},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_f.status_code == 200

    forget = client.post(
        "/memory/forget",
        json={"persona_id": "p1", "type": "glossary", "key": "g1"},
        headers=auth_headers("testkey-a"),
    )
    assert forget.status_code == 200
    assert storage.get_memory_by_id("userA", "p1", mem_f) is None

    recall2 = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "forget", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert all(item["id"] != mem_f for item in recall2.json()["data"]["PERSONA_MEMORY"])

    create = client.post(
        "/goals/create",
        json={"persona_id": "p1", "title": "Learn Rust", "details": "practice"},
        headers=auth_headers("testkey-a"),
    )
    assert create.status_code == 200
    goal_id = create.json()["data"]["goal_id"]

    listed = client.get(
        "/goals/list",
        params={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    items = listed.json()["data"]["items"]
    assert any(item["id"] == goal_id for item in items)

    update = client.post(
        "/goals/update_status",
        json={"persona_id": "p1", "goal_id": goal_id, "status": "done"},
        headers=auth_headers("testkey-a"),
    )
    assert update.status_code == 200

    link = client.post(
        "/goals/link",
        json={"persona_id": "p1", "goal_id": goal_id, "memory_id": None, "note": "start"},
        headers=auth_headers("testkey-a"),
    )
    assert link.status_code == 200
