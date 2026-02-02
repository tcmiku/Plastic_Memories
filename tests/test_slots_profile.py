import json


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_slots_and_profile_from_slots(client):
    payload = {
        "persona_id": "p1",
        "type": "identity",
        "key": "id1",
        "content": "I am unit-test persona",
        "tags": [],
        "source_type": "model_inferred",
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

    slots = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    assert slots.status_code == 200
    items = slots.json()["data"]["items"]
    assert any(item["slot_name"] == "identity" for item in items)
    identity = next(item for item in items if item["slot_name"] == "identity")
    assert json.loads(identity["value_json"])["text"] == "I am unit-test persona"

    for i in range(30):
        client.post(
            "/memory/write",
            json={
                "persona_id": "p1",
                "type": "glossary",
                "key": f"g{i}",
                "content": "x" * 120,
                "tags": [],
            },
            headers=auth_headers("testkey-a"),
        )

    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "zzzz", "limit": 10},
        headers=auth_headers("testkey-a"),
    )
    assert recall.status_code == 200
    profile = recall.json()["data"]["PERSONA_PROFILE"]
    assert len(profile) <= 2000
