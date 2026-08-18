"""
SQLite-backed session store for Zenix AI.
Persists conversation history across server restarts.
"""

import os
import json
import sqlite3
import threading
from typing import List, Dict, Optional
from datetime import datetime


class SessionStore:
    """
    Thread-safe SQLite-backed session store.
    Stores conversation history with automatic cleanup of old sessions.
    """

    def __init__(self, db_path: str = None, max_messages: int = 40, max_age_hours: int = 24):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "sessions.db")
        self.db_path = os.path.realpath(db_path)
        self.max_messages = max_messages
        self.max_age_hours = max_age_hours
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Create the sessions table if it doesn't exist."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                persona TEXT DEFAULT 'desi',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)
        """)
        conn.commit()

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve conversation history for a session."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the session."""
        now = datetime.now().isoformat()
        conn = self._get_conn()

        # Ensure session exists
        conn.execute(
            """INSERT OR IGNORE INTO sessions (session_id, created_at, updated_at)
               VALUES (?, ?, ?)""",
            (session_id, now, now),
        )

        # Add message
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )

        # Update session timestamp
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        conn.commit()

        # Trim if too many messages
        self._trim_session(session_id)

    def _trim_session(self, session_id: str):
        """Remove oldest messages if session exceeds max_messages."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            (session_id,),
        )
        count = cursor.fetchone()["cnt"]

        if count > self.max_messages:
            # Keep the most recent max_messages
            conn.execute(
                """DELETE FROM messages WHERE session_id = ?
                   AND id NOT IN (
                       SELECT id FROM messages WHERE session_id = ?
                       ORDER BY id DESC LIMIT ?
                   )""",
                (session_id, session_id, self.max_messages),
            )
            conn.commit()

    def replace_history(self, session_id: str, history: List[Dict[str, str]]):
        """Replace entire session history (used after summarization)."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        now = datetime.now().isoformat()
        for msg in history:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, msg["role"], msg["content"], now),
            )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        conn.commit()

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        )
        return cursor.fetchone() is not None

    def cleanup_old_sessions(self):
        """Remove sessions older than max_age_hours."""
        conn = self._get_conn()
        cutoff = datetime.now().isoformat()
        # Simple approach: delete sessions with no recent messages
        conn.execute(
            """DELETE FROM messages WHERE session_id IN (
                   SELECT session_id FROM sessions
                   WHERE updated_at < datetime(?, '-' || ? || ' hours')
               )""",
            (cutoff, self.max_age_hours),
        )
        conn.execute(
            "DELETE FROM sessions WHERE updated_at < datetime(?, '-' || ? || ' hours')",
            (cutoff, self.max_age_hours),
        )
        conn.commit()

    def stats(self) -> Dict:
        """Return store statistics."""
        conn = self._get_conn()
        sessions = conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()["cnt"]
        messages = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()["cnt"]
        return {
            "db_path": self.db_path,
            "total_sessions": sessions,
            "total_messages": messages,
            "max_messages_per_session": self.max_messages,
            "max_age_hours": self.max_age_hours,
        }


# Module-level singleton
session_store = SessionStore()
