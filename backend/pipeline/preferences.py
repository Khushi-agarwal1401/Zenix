"""
User Preferences Module for Zenix AI.
Persists language, persona, location, and topics of interest per session.
"""

import os
import json
import sqlite3
import threading
from typing import Dict, Any, Optional
from datetime import datetime


class UserPreferences:
    """SQLite-backed user preferences store."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "preferences.db"
            )
        self.db_path = os.path.realpath(db_path)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Create preferences table if it doesn't exist."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                session_id TEXT PRIMARY KEY,
                preferred_language TEXT DEFAULT 'hi',
                preferred_persona TEXT DEFAULT 'desi',
                location_city TEXT DEFAULT '',
                location_state TEXT DEFAULT '',
                topics_of_interest TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

    def get(self, session_id: str) -> Dict[str, Any]:
        """Get preferences for a session."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM user_preferences WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()

        if row:
            return {
                "session_id": row["session_id"],
                "preferred_language": row["preferred_language"] or "hi",
                "preferred_persona": row["preferred_persona"] or "desi",
                "location_city": row["location_city"] or "",
                "location_state": row["location_state"] or "",
                "topics_of_interest": json.loads(row["topics_of_interest"] or "[]"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

        # Return defaults
        return {
            "session_id": session_id,
            "preferred_language": "hi",
            "preferred_persona": "desi",
            "location_city": "",
            "location_state": "",
            "topics_of_interest": [],
            "created_at": None,
            "updated_at": None,
        }

    def update(self, session_id: str, **kwargs) -> bool:
        """
        Update preferences for a session.

        Supported fields:
            - preferred_language: str (hi, bn, te, mr, ta, gu, ur, kn, ml, or, pa, en)
            - preferred_persona: str (desi, sarkari)
            - location_city: str
            - location_state: str
            - topics_of_interest: list of str
        """
        try:
            now = datetime.now().isoformat()
            conn = self._get_conn()

            # Check if session exists
            cursor = conn.execute(
                "SELECT 1 FROM user_preferences WHERE session_id = ?",
                (session_id,),
            )
            exists = cursor.fetchone() is not None

            if not exists:
                # Insert new record
                conn.execute(
                    """INSERT INTO user_preferences
                       (session_id, preferred_language, preferred_persona,
                        location_city, location_state, topics_of_interest,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        session_id,
                        kwargs.get("preferred_language", "hi"),
                        kwargs.get("preferred_persona", "desi"),
                        kwargs.get("location_city", ""),
                        kwargs.get("location_state", ""),
                        json.dumps(kwargs.get("topics_of_interest", [])),
                        now,
                        now,
                    ),
                )
            else:
                # Update existing record
                updates = []
                values = []
                for key in [
                    "preferred_language",
                    "preferred_persona",
                    "location_city",
                    "location_state",
                ]:
                    if key in kwargs:
                        updates.append(f"{key} = ?")
                        values.append(kwargs[key])

                if "topics_of_interest" in kwargs:
                    updates.append("topics_of_interest = ?")
                    values.append(json.dumps(kwargs["topics_of_interest"]))

                if updates:
                    updates.append("updated_at = ?")
                    values.append(now)
                    values.append(session_id)
                    conn.execute(
                        f"UPDATE user_preferences SET {', '.join(updates)} WHERE session_id = ?",
                        values,
                    )

            conn.commit()
            return True
        except Exception as e:
            print(f"Failed to update preferences: {e}")
            return False

    def set_language(self, session_id: str, language: str) -> bool:
        """Set preferred language for a session."""
        return self.update(session_id, preferred_language=language)

    def set_persona(self, session_id: str, persona: str) -> bool:
        """Set preferred persona for a session."""
        return self.update(session_id, preferred_persona=persona)

    def set_location(self, session_id: str, city: str, state: str = "") -> bool:
        """Set user location for local weather/news."""
        return self.update(session_id, location_city=city, location_state=state)

    def add_topic(self, session_id: str, topic: str) -> bool:
        """Add a topic of interest."""
        prefs = self.get(session_id)
        topics = prefs.get("topics_of_interest", [])
        if topic not in topics:
            topics.append(topic)
            # Keep only last 10 topics
            topics = topics[-10:]
            return self.update(session_id, topics_of_interest=topics)
        return True

    def stats(self) -> Dict[str, Any]:
        """Return preference store statistics."""
        conn = self._get_conn()
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM user_preferences"
        ).fetchone()["cnt"]

        return {
            "total_sessions": count,
            "db_path": self.db_path,
        }


# Singleton
user_preferences = UserPreferences()
