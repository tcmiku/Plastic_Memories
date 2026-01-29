import json
from pathlib import Path
import pytest

from plastic_memories.templates import resolve_template_path, load_persona_template


def test_resolve_template_path(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    path = resolve_template_path("personas/demo")
    assert path.name == "demo"
    assert path.parent.name == "personas"
    path2 = resolve_template_path("demo")
    assert path2.name == "demo"
    assert path2.parent.name == "personas"


def test_resolve_template_path_traversal(tmp_path, monkeypatch):
    root = tmp_path / "personas"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PLASTIC_MEMORIES_TEMPLATE_ROOT", str(root))
    import plastic_memories.config as config
    config._settings = None

    with pytest.raises(ValueError):
        resolve_template_path("../secret")


def test_load_persona_template(tmp_path):
    tdir = tmp_path / "personas" / "demo"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "persona.md").write_text("# Persona", encoding="utf-8")
    (tdir / "rules.md").write_text("- 规则", encoding="utf-8")
    (tdir / "preferences.json").write_text(json.dumps({"k": "v"}), encoding="utf-8")
    seed = load_persona_template(tdir)
    assert seed.persona_md
    assert seed.rules_md
    assert seed.preferences_json.get("k") == "v"


def test_load_persona_template_missing_persona(tmp_path):
    tdir = tmp_path / "personas" / "demo"
    tdir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        load_persona_template(tdir)


def test_load_persona_template_invalid_json(tmp_path):
    tdir = tmp_path / "personas" / "demo"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "persona.md").write_text("# Persona", encoding="utf-8")
    (tdir / "preferences.json").write_text("{bad json}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_persona_template(tdir)
