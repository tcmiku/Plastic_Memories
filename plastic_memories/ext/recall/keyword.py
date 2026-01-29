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
        profile = self._profile_builder.build(persona, self._storage.list_memory(user_id, persona_id))
        log_event("recall.run", user_id=user_id, persona_id=persona_id)
        return {
            "PERSONA_PROFILE": profile,
            "PERSONA_MEMORY": memory_items,
            "CHAT_SNIPPETS": snippets,
        }
