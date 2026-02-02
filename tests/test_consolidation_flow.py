
def auth_headers(key: str) -> dict:
    return {"X-API-Key": key}


def test_model_inferred_confirm_flow(client):
    payload = {
        "persona_id": "p1",
        "type": "preferences",
        "key": "pref1",
        "content": "likes oolong",
        "tags": [],
        "source_type": "model_inferred",
    }
    res = client.post("/memory/write", json=payload, headers=auth_headers("testkey-a"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["memory_status"] == "candidate"
    mem_id = data["memory_id"]

    confirm = client.post(
        "/memory/confirm",
        json={"persona_id": "p1", "memory_id": mem_id},
        headers=auth_headers("testkey-a"),
    )
    assert confirm.status_code == 200
    cdata = confirm.json()["data"]
    assert cdata["memory_status"] == "active"
