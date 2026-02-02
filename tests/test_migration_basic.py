import sqlite3

from plastic_memories.config import get_settings
from plastic_memories.ext.registry import get_storage


def test_migration_schema_version():
    get_storage()
    db_path = get_settings().db_path
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        assert row is not None
        assert row[0]
        cols = [r[1] for r in conn.execute("PRAGMA table_info(memory_items)").fetchall()]
        assert "status" in cols
        assert "source_type" in cols
