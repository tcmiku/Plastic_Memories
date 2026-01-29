import json
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from plastic_memories.api import app


def _write_template(base: Path, name: str, *, invalid_prefs: bool = False):
    tdir = base / name
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "persona.md").write_text("# Persona\n你好", encoding="utf-8")
    (tdir / "rules.md").write_text("- 规则", encoding="utf-8")
    if invalid_prefs:
        (tdir / "preferences.json").write_text("{bad json}", encoding="utf-8")
    else:
        (tdir / "preferences.json").write_text(json.dumps({"language": "zh"}, ensure_ascii=False), encoding="utf-8")
    return tdir


@pytest.mark.anyio
async def test_create_from_template_ok(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    _write_template(root, "persona_x")
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/persona/create_from_template", json={
            "user_id": "local",
            "persona_id": "persona_x",
            "template_path": "personas/persona_x",
            "allow_overwrite": False
        })
        body = res.json()
        assert body["ok"] is True
        assert body["data"]["applied"] is True
        assert body["data"]["skipped"] is False


@pytest.mark.anyio
async def test_create_from_template_idempotent_skip(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    _write_template(root, "persona_x")
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/persona/create_from_template", json={
            "user_id": "local",
            "persona_id": "persona_x",
            "template_path": "personas/persona_x",
            "allow_overwrite": False
        })
        res = await client.post("/persona/create_from_template", json={
            "user_id": "local",
            "persona_id": "persona_x",
            "template_path": "personas/persona_x",
            "allow_overwrite": False
        })
        body = res.json()
        assert body["ok"] is True
        assert body["data"]["skipped"] is True


@pytest.mark.anyio
async def test_create_from_template_overwrite(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    _write_template(root, "persona_x")
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/persona/create_from_template", json={
            "user_id": "local",
            "persona_id": "persona_x",
            "template_path": "personas/persona_x",
            "allow_overwrite": True
        })
        body = res.json()
        assert body["ok"] is True
        assert body["data"]["overwritten"] is True
        assert body["data"]["applied"] is True


@pytest.mark.anyio
async def test_create_from_template_path_traversal(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/persona/create_from_template", json={
            "user_id": "local",
            "persona_id": "persona_x",
            "template_path": "../secret",
            "allow_overwrite": False
        })
        body = res.json()
        assert body["ok"] is False


@pytest.mark.anyio
async def test_create_from_template_invalid_preferences(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    _write_template(root, "persona_x", invalid_prefs=True)
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/persona/create_from_template", json={
            "user_id": "local",
            "persona_id": "persona_x",
            "template_path": "personas/persona_x",
            "allow_overwrite": False
        })
        body = res.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "validation_error"
