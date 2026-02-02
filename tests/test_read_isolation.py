
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_read_isolation_list_recall_profile(client):
    payload = {
        "persona_id": "p1",
        "type": "preferences",
        "key": "pref1",
        "content": "loves jasmine tea",
        "tags": [],
    }
    res = client.post("/memory/write", json=payload, headers=auth_headers("testkey-a"))
    assert res.status_code == 200

    recall = client.post(
        "/memory/recall",
        json={"persona_id": "p1", "query": "jasmine", "limit": 10},
        headers=auth_headers("testkey-b"),
    )
    assert recall.status_code == 200
    recall_items = recall.json()["data"]["PERSONA_MEMORY"]
    assert recall_items == []

    listed = client.get(
        "/memory/list",
        params={"persona_id": "p1"},
        headers=auth_headers("testkey-b"),
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["items"] == []

    profile = client.get(
        "/persona/profile",
        params={"persona_id": "p1"},
        headers=auth_headers("testkey-b"),
    )
    assert profile.status_code == 200
    assert "jasmine" not in profile.json()["data"]["profile_markdown"]

    slots = client.post(
        "/persona/slots/get",
        json={"persona_id": "p1"},
        headers=auth_headers("testkey-b"),
    )
    assert slots.status_code == 200
    assert slots.json()["data"]["items"] == []
