from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Message:
    role: str
    content: str
    created_at: Optional[int] = None


@dataclass
class RecallResult:
    raw: dict
    injection_block: str
    persona_profile: Optional[str]
    memory_items: list[dict]
    chat_snippets: list[dict]
    request_id: Optional[str] = None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def build_injection_block(data: dict) -> str:
    if "injection_block" in data and isinstance(data["injection_block"], str):
        return data["injection_block"]
    persona_profile = data.get("PERSONA_PROFILE") or ""
    memory_items = data.get("PERSONA_MEMORY") or []
    chat_snippets = data.get("CHAT_SNIPPETS") or []

    persona_profile = _truncate(str(persona_profile), 1200)

    trimmed_memory = []
    for item in memory_items[:8]:
        content = _truncate(str(item.get("content", "")), 120)
        trimmed_memory.append({**item, "content": content})

    trimmed_snippets = []
    for item in chat_snippets[:5]:
        content = _truncate(str(item.get("content", "")), 160)
        trimmed_snippets.append({**item, "content": content})

    memory_lines = "\n".join([f"- {m.get('type','')}: {m.get('mkey','')} {m.get('content','')}" for m in trimmed_memory])
    snippet_lines = "\n".join([f"- {s.get('role','')}: {s.get('content','')}" for s in trimmed_snippets])

    return (
        f"[PERSONA_PROFILE]\n{persona_profile}\n[/PERSONA_PROFILE]\n"
        f"[PERSONA_MEMORY]\n{memory_lines}\n[/PERSONA_MEMORY]\n"
        f"[CHAT_SNIPPETS]\n{snippet_lines}\n[/CHAT_SNIPPETS]"
    )
