import sqlite3
from pathlib import Path
from typing import Any

from ...config import get_settings
from ...db import ensure_db_dir
from ...logging import log_event
from ...migrations import PERSONAS_SQL, MESSAGES_SQL, MEMORY_SQL, META_SQL, FTS_MESSAGES_SQL, FTS_MEMORY_SQL
from ...utils import now_ts, dumps_json


class SQLiteStorage:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._db_path = Path(self._settings.db_path)
        self._fts_enabled = False

    def _connect(self) -> sqlite3.Connection:
        ensure_db_dir()
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(f"PRAGMA busy_timeout={self._settings.busy_timeout_ms};")
        return conn

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(PERSONAS_SQL)
            conn.executescript(MESSAGES_SQL)
            conn.executescript(MEMORY_SQL)
            conn.executescript(META_SQL)
            self._try_enable_fts(conn)
        log_event("db.init")

    def _try_enable_fts(self, conn: sqlite3.Connection) -> None:
        try:
            conn.executescript(FTS_MESSAGES_SQL)
            conn.executescript(FTS_MEMORY_SQL)
            self._fts_enabled = True
            conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("fts_enabled", "1"))
        except sqlite3.OperationalError:
            self._fts_enabled = False
            conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("fts_enabled", "0"))

    def fts_enabled(self) -> bool:
        return self._fts_enabled

    def create_persona(self, user_id: str, persona_id: str, display_name: str | None, description: str | None) -> None:
        now = now_ts()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO personas(user_id, persona_id, display_name, description, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?)",
                (user_id, persona_id, display_name, description, now, now),
            )

    def get_persona(self, user_id: str, persona_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM personas WHERE user_id=? AND persona_id=?", (user_id, persona_id)).fetchone()
            return dict(row) if row else None

    def append_message(self, data: dict) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO messages(user_id, persona_id, session_id, source_app, role, content, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (data["user_id"], data["persona_id"], data.get("session_id"), data.get("source_app"), data["role"], data["content"], data["created_at"]),
            )
            msg_id = int(cursor.lastrowid)
            if self._fts_enabled:
                conn.execute("INSERT INTO fts_messages(rowid, content, user_id, persona_id) VALUES(?, ?, ?, ?)", (msg_id, data["content"], data["user_id"], data["persona_id"]))
        log_event("messages.append", user_id=data["user_id"], persona_id=data["persona_id"])
        return msg_id

    def recent_messages(self, user_id: str, persona_id: str, limit: int, days: int | None) -> list[dict]:
        with self._connect() as conn:
            params: list[Any] = [user_id, persona_id]
            sql = "SELECT * FROM messages WHERE user_id=? AND persona_id=?"
            if days is not None:
                cutoff = now_ts() - days * 86400
                sql += " AND created_at >= ?"
                params.append(cutoff)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def purge_messages(self, user_id: str, persona_id: str, before_ts: int | None) -> int:
        with self._connect() as conn:
            if before_ts is None:
                return 0
            cursor = conn.execute("DELETE FROM messages WHERE user_id=? AND persona_id=? AND created_at < ?", (user_id, persona_id, before_ts))
            return cursor.rowcount

    def write_memory(self, data: dict) -> tuple[bool, int]:
        now = now_ts()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM memory_items WHERE user_id=? AND persona_id=? AND type=? AND mkey=?",
                (data["user_id"], data["persona_id"], data["type"], data["key"]),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE memory_items SET content=?, tags_json=?, ttl_seconds=?, updated_at=? WHERE id=?",
                    (data["content"], dumps_json(data.get("tags") or []), data.get("ttl_seconds"), now, existing["id"]),
                )
                mem_id = int(existing["id"])
                updated = True
            else:
                cursor = conn.execute(
                    "INSERT INTO memory_items(user_id, persona_id, type, mkey, content, tags_json, ttl_seconds, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data["user_id"], data["persona_id"], data["type"], data["key"], data["content"], dumps_json(data.get("tags") or []), data.get("ttl_seconds"), now, now),
                )
                mem_id = int(cursor.lastrowid)
                updated = False
            if self._fts_enabled:
                conn.execute("DELETE FROM fts_memory WHERE rowid=?", (mem_id,))
                conn.execute("INSERT INTO fts_memory(rowid, content, user_id, persona_id) VALUES(?, ?, ?, ?)", (mem_id, data["content"], data["user_id"], data["persona_id"]))
        return updated, mem_id

    def _valid_memory_clause(self) -> str:
        return "(ttl_seconds IS NULL OR created_at + ttl_seconds > ?)"

    def list_memory(self, user_id: str, persona_id: str) -> list[dict]:
        with self._connect() as conn:
            now = now_ts()
            rows = conn.execute(
                f"SELECT * FROM memory_items WHERE user_id=? AND persona_id=? AND {self._valid_memory_clause()} ORDER BY updated_at DESC",
                (user_id, persona_id, now),
            ).fetchall()
            return [dict(row) for row in rows]

    def recall_memory(self, user_id: str, persona_id: str, query: str, limit: int) -> list[dict]:
        with self._connect() as conn:
            now = now_ts()
            if self._fts_enabled:
                sql = (
                    "SELECT m.* FROM fts_memory f JOIN memory_items m ON m.id=f.rowid "
                    "WHERE fts_memory MATCH ? AND m.user_id=? AND m.persona_id=? AND " + self._valid_memory_clause() + " LIMIT ?"
                )
                rows = conn.execute(sql, (query, user_id, persona_id, now, limit)).fetchall()
            else:
                like = f"%{query}%"
                sql = "SELECT * FROM memory_items WHERE user_id=? AND persona_id=? AND content LIKE ? AND " + self._valid_memory_clause() + " LIMIT ?"
                rows = conn.execute(sql, (user_id, persona_id, like, now, limit)).fetchall()
            return [dict(row) for row in rows]

    def forget_memory(self, user_id: str, persona_id: str, mtype: str, key: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memory_items WHERE user_id=? AND persona_id=? AND type=? AND mkey=?", (user_id, persona_id, mtype, key))
            return cursor.rowcount

    def rebuild_fts(self, user_id: str, persona_id: str) -> None:
        if not self._fts_enabled:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM fts_memory WHERE user_id=? AND persona_id=?", (user_id, persona_id))
            conn.execute("DELETE FROM fts_messages WHERE user_id=? AND persona_id=?", (user_id, persona_id))
            rows = conn.execute("SELECT id, content FROM memory_items WHERE user_id=? AND persona_id=?", (user_id, persona_id)).fetchall()
            for row in rows:
                conn.execute("INSERT INTO fts_memory(rowid, content, user_id, persona_id) VALUES(?, ?, ?, ?)", (row["id"], row["content"], user_id, persona_id))
            rows = conn.execute("SELECT id, content FROM messages WHERE user_id=? AND persona_id=?", (user_id, persona_id)).fetchall()
            for row in rows:
                conn.execute("INSERT INTO fts_messages(rowid, content, user_id, persona_id) VALUES(?, ?, ?, ?)", (row["id"], row["content"], user_id, persona_id))

    def metrics(self) -> dict:
        with self._connect() as conn:
            personas = conn.execute("SELECT COUNT(*) as c FROM personas").fetchone()["c"]
            messages = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
            memory_items = conn.execute("SELECT COUNT(*) as c FROM memory_items").fetchone()["c"]
            return {"personas": int(personas), "messages": int(messages), "memory_items": int(memory_items)}
