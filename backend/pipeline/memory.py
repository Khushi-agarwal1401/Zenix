"""
Conversation Memory Module for Zenix AI.
Stores and retrieves user facts, preferences, and learned information across sessions.

Supports:
- "Remember this" / "Remember my name is X"
- User corrections ("Actually, my city is Mumbai, not Delhi")
- Cross-session fact retrieval
- Automatic fact injection into context
"""

import os
import json
import sqlite3
import threading
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationMemory:
    """SQLite-backed conversation memory store for persisting user facts."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "memory.db")
        self.db_path = os.path.realpath(db_path)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                confidence REAL DEFAULT 1.0,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(session_id, fact_key)
            );
            CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_facts(session_id);
            CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_facts(fact_key);

            CREATE TABLE IF NOT EXISTS memory_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                original_key TEXT,
                original_value TEXT,
                corrected_key TEXT,
                corrected_value TEXT,
                created_at TEXT
            );
        """)
        conn.commit()

    def remember(self, session_id: str, key: str, value: str, source: str = "user") -> bool:
        """Store a fact in memory. Overwrites existing fact with same key."""
        try:
            now = datetime.now().isoformat()
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO memory_facts (session_id, fact_key, fact_value, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, fact_key) DO UPDATE SET
                    fact_value = excluded.fact_value,
                    source = excluded.source,
                    updated_at = excluded.updated_at
            """, (session_id, key.lower().strip(), value.strip(), source, now, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to remember fact: {e}")
            return False

    def recall(self, session_id: str, key: str = None) -> Dict[str, str]:
        """Recall facts from memory. If key is provided, return specific fact."""
        conn = self._get_conn()
        if key:
            cursor = conn.execute(
                "SELECT fact_key, fact_value, source, updated_at FROM memory_facts WHERE session_id = ? AND fact_key = ?",
                (session_id, key.lower().strip()),
            )
        else:
            cursor = conn.execute(
                "SELECT fact_key, fact_value, source, updated_at FROM memory_facts WHERE session_id = ? ORDER BY updated_at DESC",
                (session_id,),
            )

        facts = {}
        for row in cursor.fetchall():
            facts[row["fact_key"]] = {
                "value": row["fact_value"],
                "source": row["source"],
                "updated_at": row["updated_at"],
            }
        return facts

    def forget(self, session_id: str, key: str) -> bool:
        """Remove a specific fact from memory."""
        try:
            conn = self._get_conn()
            conn.execute(
                "DELETE FROM memory_facts WHERE session_id = ? AND fact_key = ?",
                (session_id, key.lower().strip()),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to forget fact: {e}")
            return False

    def correct(self, session_id: str, old_key: str, old_value: str, new_key: str, new_value: str) -> bool:
        """Record a correction (user fixing a previously stored fact)."""
        try:
            now = datetime.now().isoformat()
            conn = self._get_conn()

            # Log the correction
            conn.execute("""
                INSERT INTO memory_corrections
                    (session_id, original_key, original_value, corrected_key, corrected_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, old_key, old_value, new_key, new_value, now))

            # Update the fact
            conn.execute("""
                INSERT INTO memory_facts (session_id, fact_key, fact_value, source, created_at, updated_at)
                VALUES (?, ?, ?, 'correction', ?, ?)
                ON CONFLICT(session_id, fact_key) DO UPDATE SET
                    fact_value = excluded.fact_value,
                    source = 'correction',
                    updated_at = excluded.updated_at
            """, (session_id, new_key.lower().strip(), new_value.strip(), now, now))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record correction: {e}")
            return False

    def get_all_facts(self, session_id: str) -> List[Dict[str, str]]:
        """Get all facts for a session as a list of dicts."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT fact_key, fact_value, source FROM memory_facts WHERE session_id = ? ORDER BY updated_at DESC",
            (session_id,),
        )
        return [
            {"key": row["fact_key"], "value": row["fact_value"], "source": row["source"]}
            for row in cursor.fetchall()
        ]

    def get_context_string(self, session_id: str) -> str:
        """Get a formatted string of all remembered facts for injecting into LLM context."""
        facts = self.get_all_facts(session_id)
        if not facts:
            return ""

        lines = ["[User Memory - Facts I remember about this user]"]
        for f in facts:
            lines.append(f"- {f['key'].title()}: {f['value']}")
        lines.append("[End of User Memory]")
        return "\n".join(lines)

    def parse_remember_intent(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Parse user text to extract 'remember' intent.
        Returns (key, value) if found, None otherwise.

        Examples:
            "remember my name is Rahul" -> ("name", "Rahul")
            "remember I live in Mumbai" -> ("city", "Mumbai")
            "my name is Priya" -> ("name", "Priya")
            "I am a farmer" -> ("occupation", "farmer")
            "remember my mother's name is Sita" -> ("mother_name", "Sita")
        """
        text_lower = text.lower().strip()

        # Pattern: "remember <something>"
        remember_patterns = [
            # "remember my name is X"
            (r"remember\s+(?:my\s+)?name\s+is\s+(.+)", "name"),
            (r"remember\s+(?:my\s+)?city\s+is\s+(.+)", "city"),
            (r"remember\s+(?:my\s+)?state\s+is\s+(.+)", "state"),
            (r"remember\s+(?:my\s+)?village\s+is\s+(.+)", "village"),
            (r"remember\s+(?:my\s+)?occupation\s+(?:is|are)\s+(.+)", "occupation"),
            (r"remember\s+(?:i\s+)?(?:am|work\s+as)\s+(?:a\s+)?(.+)", "occupation"),
            (r"remember\s+(?:my\s+)?age\s+(?:is|am)\s+(.+)", "age"),
            (r"remember\s+(?:my\s+)?phone\s+(?:is|number\s+is)\s+(.+)", "phone"),
            (r"remember\s+(?:my\s+)?family\s+(?:size|has)\s+(.+)", "family_size"),
            (r"remember\s+(?:my\s+)?(?:son|daughter|child|kids?)\s+(?:is|name|are)\s+(.+)", "children"),
            (r"remember\s+(?:my\s+)?(?:wife|husband|spouse|partner)\s+(?:is|name)\s+(.+)", "spouse"),
            (r"remember\s+(?:my\s+)?(?:mother|mom|mummy|amma)\s+(?:is|name)\s+(.+)", "mother_name"),
            (r"remember\s+(?:my\s+)?(?:father|dad|papa|appa)\s+(?:is|name)\s+(.+)", "father_name"),
            # "remember that I have..."
            (r"remember\s+that\s+i\s+have\s+(.+)", "notes"),
            # "remember <general>"
            (r"remember\s+(.+)", "notes"),
        ]

        for pattern, key in remember_patterns:
            import re
            match = re.match(pattern, text_lower)
            if match:
                value = match.group(1).strip().rstrip(".")
                return (key, value)

        # Implicit learning patterns (no "remember" keyword)
        implicit_patterns = [
            (r"my\s+name\s+is\s+(.+)", "name"),
            (r"i\s+(?:am|live)\s+(?:in\s+)?(.+)", "city"),
            (r"i\s+work\s+(?:as|in)\s+(?:a\s+)?(.+)", "occupation"),
            (r"i\s+am\s+(?:a\s+)?(.+)", "occupation"),
            (r"my\s+city\s+is\s+(.+)", "city"),
            (r"my\s+state\s+is\s+(.+)", "state"),
            (r"i\s+live\s+in\s+(.+)", "city"),
        ]

        for pattern, key in implicit_patterns:
            import re
            match = re.match(pattern, text_lower)
            if match:
                value = match.group(1).strip().rstrip(".")
                # Skip common false positives
                if value in ["fine", "good", "ok", "here", "looking", "trying", "searching", "asking", "wanting"]:
                    continue
                return (key, value)

        return None

    def parse_forget_intent(self, text: str) -> Optional[str]:
        """Parse 'forget' intent from user text."""
        import re
        text_lower = text.lower().strip()

        patterns = [
            r"forget\s+(?:my\s+)?(.+)",
            r"delete\s+(?:my\s+)?(.+)",
            r"remove\s+(?:my\s+)?(.+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, text_lower)
            if match:
                key = match.group(1).strip().rstrip(".")
                # Map common terms
                key_map = {
                    "name": "name", "city": "city", "state": "state",
                    "age": "age", "occupation": "occupation", "everything": "__all__",
                }
                return key_map.get(key, key)

        return None

    def stats(self) -> Dict[str, Any]:
        """Return memory store statistics."""
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) as cnt FROM memory_facts").fetchone()["cnt"]
        sessions = conn.execute("SELECT COUNT(DISTINCT session_id) as cnt FROM memory_facts").fetchone()["cnt"]
        corrections = conn.execute("SELECT COUNT(*) as cnt FROM memory_corrections").fetchone()["cnt"]

        return {
            "total_facts": count,
            "total_sessions": sessions,
            "total_corrections": corrections,
            "db_path": self.db_path,
        }


# Singleton
conversation_memory = ConversationMemory()
