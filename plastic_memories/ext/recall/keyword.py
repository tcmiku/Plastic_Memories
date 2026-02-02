import json

from ...config import get_settings
from ...logging import log_event
from ..interfaces import StorageBackend, ProfileBuilder


class KeywordRecallEngine:
    def __init__(self, storage: StorageBackend, profile_builder: ProfileBuilder) -> None:
        self._storage = storage
        self._profile_builder = profile_builder

    def recall(self, user_id: str, persona_id: str, query: str, limit: int) -> dict:
        persona = self._storage.get_persona(user_id, persona_id)
        memory_items = self._storage.recall_memory(user_id, persona_id, query, limit)
        settings = get_settings()
        snippets = self._storage.recent_messages(user_id, persona_id, settings.max_snippets, settings.message_snippet_days)
        slots = self._storage.get_slots(user_id, persona_id)
        profile = build_profile_from_slots(persona, slots, settings.profile_max_chars)
        log_event("memory.recall", user_id=user_id, persona_id=persona_id)
        return {
            "PERSONA_PROFILE": profile,
            "PERSONA_MEMORY": memory_items,
            "CHAT_SNIPPETS": snippets,
        }


def _slot_value_text(value_json: str) -> str:
    try:
        parsed = json.loads(value_json)
    except Exception:
        return value_json
    if isinstance(parsed, dict) and "text" in parsed:
        return str(parsed["text"])
    return json.dumps(parsed, ensure_ascii=False)


def build_profile_from_slots(persona: dict | None, slots: list[dict], max_chars: int) -> str:
    lines = ["# Persona Profile"]
    if persona:
        lines.append(f"- User: {persona['user_id']}")
        lines.append(f"- Persona: {persona['persona_id']}")
        if persona.get("display_name"):
            lines.append(f"- Name: {persona['display_name']}")
        if persona.get("description"):
            lines.append(f"- Description: {persona['description']}")
    if slots:
        lines.append("")
        lines.append("## Slots")
        for slot in slots:
            value_text = _slot_value_text(slot.get("value_json") or "")
            lines.append(f"- [{slot.get('slot_name')}] {value_text}")
    profile = "\n".join(lines)
    if len(profile) > max_chars:
        profile = profile[:max_chars]
    return profile
