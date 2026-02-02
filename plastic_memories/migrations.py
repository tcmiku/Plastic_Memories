SCHEMA_VERSION = "2"

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
    status TEXT NOT NULL DEFAULT 'active',
    scope TEXT NOT NULL DEFAULT 'persona',
    source_type TEXT NOT NULL DEFAULT 'user_explicit',
    source_ref TEXT,
    confidence REAL,
    expires_at INTEGER,
    supersedes_id INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(user_id, persona_id, type, mkey)
);
CREATE INDEX IF NOT EXISTS idx_memory_user_persona ON memory_items(user_id, persona_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_items(user_id, persona_id, status, expires_at);
"""

META_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

PERSONA_SLOTS_SQL = """
CREATE TABLE IF NOT EXISTS persona_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    value_json TEXT NOT NULL,
    provenance_json TEXT,
    updated_at INTEGER NOT NULL,
    UNIQUE(user_id, persona_id, slot_name)
);
CREATE INDEX IF NOT EXISTS idx_persona_slots_user_persona ON persona_slots(user_id, persona_id, updated_at DESC);
"""

GOALS_SQL = """
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    title TEXT NOT NULL,
    details TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goals_user_persona ON goals(user_id, persona_id, updated_at DESC);
"""

GOAL_LINKS_SQL = """
CREATE TABLE IF NOT EXISTS goal_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    goal_id INTEGER NOT NULL,
    memory_id INTEGER,
    note TEXT,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goal_links_user_persona ON goal_links(user_id, persona_id, created_at DESC);
"""


def _add_column(conn, table: str, column_def: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
    except Exception:
        return


def migrate(conn) -> None:
    conn.executescript(PERSONAS_SQL)
    conn.executescript(MESSAGES_SQL)
    conn.executescript(MEMORY_SQL)
    conn.executescript(META_SQL)
    conn.executescript(PERSONA_SLOTS_SQL)
    conn.executescript(GOALS_SQL)
    conn.executescript(GOAL_LINKS_SQL)
    _add_column(conn, "memory_items", "status TEXT NOT NULL DEFAULT 'active'")
    _add_column(conn, "memory_items", "scope TEXT NOT NULL DEFAULT 'persona'")
    _add_column(conn, "memory_items", "source_type TEXT NOT NULL DEFAULT 'user_explicit'")
    _add_column(conn, "memory_items", "source_ref TEXT")
    _add_column(conn, "memory_items", "confidence REAL")
    _add_column(conn, "memory_items", "expires_at INTEGER")
    _add_column(conn, "memory_items", "supersedes_id INTEGER")
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("schema_version", SCHEMA_VERSION))

FTS_MESSAGES_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_messages USING fts5(content, user_id, persona_id);
"""

FTS_MEMORY_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory USING fts5(content, user_id, persona_id);
"""
