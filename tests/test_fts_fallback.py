from plastic_memories.ext.backends.sqlite import SQLiteStorage
from plastic_memories.ext.profile.markdown import MarkdownProfileBuilder
from plastic_memories.ext.recall.keyword import KeywordRecallEngine


def test_fts_fallback():
    storage = SQLiteStorage()
    storage.init()
    storage._fts_enabled = False
    storage.write_memory({"user_id": "u", "persona_id": "p", "type": "glossary", "key": "k", "content": "hello world", "tags": [], "ttl_seconds": None})
    recall = KeywordRecallEngine(storage, MarkdownProfileBuilder())
    result = recall.recall("u", "p", "hello", 5)
    assert result["PERSONA_MEMORY"]
