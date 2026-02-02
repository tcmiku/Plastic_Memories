
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_goals_flow(client):
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
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert any(item["id"] == goal_id for item in items)

    update = client.post(
        "/goals/update_status",
        json={"persona_id": "p1", "goal_id": goal_id, "status": "done"},
        headers=auth_headers("testkey-a"),
    )
    assert update.status_code == 200

    listed2 = client.get(
        "/goals/list",
        params={"persona_id": "p1"},
        headers=auth_headers("testkey-a"),
    )
    assert listed2.status_code == 200
    item = next(item for item in listed2.json()["data"]["items"] if item["id"] == goal_id)
    assert item["status"] == "done"

    link = client.post(
        "/goals/link",
        json={"persona_id": "p1", "goal_id": goal_id, "memory_id": None, "note": "start"},
        headers=auth_headers("testkey-a"),
    )
    assert link.status_code == 200
