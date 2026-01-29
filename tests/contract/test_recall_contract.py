from plastic_memories.ext.backends.sqlite import SQLiteStorage
from plastic_memories.ext.profile.markdown import MarkdownProfileBuilder
from plastic_memories.ext.recall.keyword import KeywordRecallEngine
from plastic_memories.utils import now_ts


class RecallContract:
    def test_recall_contains_profile_memory_snippets(self):
        storage = SQLiteStorage()
        storage.init()
        storage.create_persona("u", "p", "name", "desc")
        storage.write_memory({"user_id": "u", "persona_id": "p", "type": "persona", "key": "name", "content": "Alice", "tags": [], "ttl_seconds": None})
        storage.append_message({"user_id": "u", "persona_id": "p", "session_id": "s", "source_app": "cli", "role": "user", "content": "hello world", "created_at": now_ts()})
        recall = KeywordRecallEngine(storage, MarkdownProfileBuilder())
        result = recall.recall("u", "p", "Alice", 5)
        assert "PERSONA_PROFILE" in result
        assert "PERSONA_MEMORY" in result
        assert "CHAT_SNIPPETS" in result


class TestRecallContract(RecallContract):
    pass
