import threading

from plastic_memories.ext.backends.sqlite import SQLiteStorage
from plastic_memories.utils import now_ts


class StorageContract:
    def test_init_idempotent(self):
        storage = SQLiteStorage()
        storage.init()
        storage.init()

    def test_write_and_update(self):
        storage = SQLiteStorage()
        storage.init()
        storage.write_memory({"user_id": "u", "persona_id": "p", "type": "persona", "key": "name", "content": "A", "tags": [], "ttl_seconds": None})
        updated, _ = storage.write_memory({"user_id": "u", "persona_id": "p", "type": "persona", "key": "name", "content": "B", "tags": [], "ttl_seconds": None})
        assert updated is True
        items = storage.list_memory("u", "p")
        assert items[0]["content"] == "B"

    def test_ttl_expire(self, monkeypatch):
        storage = SQLiteStorage()
        storage.init()
        storage.write_memory({"user_id": "u", "persona_id": "p", "type": "rule", "key": "temp", "content": "A", "tags": [], "ttl_seconds": 1})
        base = now_ts()
        monkeypatch.setattr("plastic_memories.utils.time.time", lambda: base + 2)
        items = storage.list_memory("u", "p")
        assert items == []

    def test_concurrent_write(self):
        storage = SQLiteStorage()
        storage.init()

        def worker(idx):
            storage.append_message({
                "user_id": "u",
                "persona_id": "p",
                "session_id": "s",
                "source_app": "cli",
                "role": "user",
                "content": f"hi {idx}",
                "created_at": now_ts(),
            })

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        msgs = storage.recent_messages("u", "p", 10, None)
        assert len(msgs) == 5


class TestStorageContract(StorageContract):
    pass
