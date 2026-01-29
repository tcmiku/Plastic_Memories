PERSONAS_SQL = """
CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    display_name TEXT,
    description TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(user_id, persona_id)
);
"""

MESSAGES_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    session_id TEXT,
    source_app TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_user_persona ON messages(user_id, persona_id, created_at DESC);
"""

MEMORY_SQL = """
CREATE TABLE IF NOT EXISTS memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    type TEXT NOT NULL,
    mkey TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json TEXT,
    ttl_seconds INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(user_id, persona_id, type, mkey)
);
CREATE INDEX IF NOT EXISTS idx_memory_user_persona ON memory_items(user_id, persona_id, updated_at DESC);
"""

META_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

FTS_MESSAGES_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_messages USING fts5(content, user_id, persona_id);
"""

FTS_MEMORY_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory USING fts5(content, user_id, persona_id);
"""
