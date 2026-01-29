from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import get_settings


@dataclass
class TemplateSeed:
    persona_md: str
    rules_md: str
    preferences_json: dict


def resolve_template_path(template_path: str) -> Path:
    if not template_path or not template_path.strip():
        raise ValueError("template_path 不能为空")
    rel = Path(template_path)
    if rel.is_absolute() or rel.drive:
        raise ValueError("template_path 必须为相对路径")
    if ".." in rel.parts:
        raise ValueError("禁止使用目录穿越路径")
    parts = list(rel.parts)
    if parts and parts[0] == "personas":
        parts = parts[1:]
    rel = Path(*parts)
    root = get_settings().template_root
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if root_resolved != candidate and root_resolved not in candidate.parents:
        raise ValueError("template_path 必须位于 personas 目录下")
    return candidate


def load_persona_template(path: Path) -> TemplateSeed:
    persona_file = path / "persona.md"
    if not persona_file.exists():
        raise FileNotFoundError("persona.md 不存在")
    persona_md = persona_file.read_text(encoding="utf-8")

    rules_file = path / "rules.md"
    rules_md = ""
    if rules_file.exists():
        rules_md = rules_file.read_text(encoding="utf-8")

    preferences_file = path / "preferences.json"
    preferences_json: dict[str, Any] = {}
    if preferences_file.exists():
        content = preferences_file.read_text(encoding="utf-8")
        preferences_json = json.loads(content)

    return TemplateSeed(persona_md=persona_md, rules_md=rules_md, preferences_json=preferences_json)
