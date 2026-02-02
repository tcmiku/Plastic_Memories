import json


def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_noise_does_not_mutate_slots_or_profile(client):
    write_id = client.post(
        "/memory/write",
        json={
            "persona_id": "p1",
            "type": "identity",
            "key": "id1",
            "content": "dev",
            "tags": [],
            "source_type": "user_explicit",
        },
        headers=auth_headers("testkey-a"),
    )
    assert write_id.status_code == 200
    mem_id = write_id.json()["data"]["memory_id"]
    confirm_id = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-a"),
    )
    assert confirm_id.status_code == 200

    for i in range(400):
        client.post(
            "/memory/write",
            json={
                "persona_id": "p1",
                "type": "note" if i % 2 == 0 else "fact",
                "key": f"n{i}",
                "content": f"noise-{i}" + ("x" * 20),
                "tags": [],
                "source_type": "user_explicit" if i % 3 == 0 else "model_inferred",
            },
            headers=auth_headers("testkey-a"),
        )

    slots = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    items = slots.json()["data"]["items"]
    identity = next(item for item in items if item["slot_name"] == "identity")
    assert json.loads(identity["value_json"])["text"] == "dev"

    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "noise", "limit": 5},
        headers=auth_headers("testkey-a"),
    )
    profile = recall.json()["data"]["PERSONA_PROFILE"]
    assert len(profile) <= 2000
