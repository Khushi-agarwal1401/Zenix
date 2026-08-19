"""
Multi-User Profiles — family sharing, profile switching, personalized experiences.

Each profile has its own:
- Language preference
- Persona preference
- Location
- Conversation history
- Interests
- Accessibility settings
"""

import json
import os
import sqlite3
import threading
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProfileManager:
    """SQLite-backed multi-user profile store."""

    DEFAULT_AVATARS = ["👨", "👩", "👦", "👧", "👴", "👵", "🧑", "👶"]

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "profiles.db")
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
            CREATE TABLE IF NOT EXISTS profiles (
                profile_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                avatar TEXT DEFAULT '🧑',
                preferred_language TEXT DEFAULT 'hi',
                preferred_persona TEXT DEFAULT 'desi',
                location_city TEXT DEFAULT '',
                location_state TEXT DEFAULT '',
                interests TEXT DEFAULT '[]',
                accessibility TEXT DEFAULT '{}',
                is_primary INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            );
        """)
        conn.commit()

        # Create default profile if none exist
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM profiles")
        if cursor.fetchone()["cnt"] == 0:
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO profiles
                   (profile_id, name, avatar, is_primary, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("default", "Primary User", "🧑", 1, now, now)
            )
            conn.commit()

    def create_profile(self, name: str, avatar: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new user profile."""
        import uuid
        profile_id = str(uuid.uuid4())[:8]

        if not avatar:
            # Auto-assign avatar
            existing = self.list_profiles()
            used_avatars = {p.get("avatar") for p in existing}
            for av in self.DEFAULT_AVATARS:
                if av not in used_avatars:
                    avatar = av
                    break
            if not avatar:
                avatar = "🧑"

        now = datetime.now().isoformat()
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO profiles
               (profile_id, name, avatar, preferred_language, preferred_persona,
                location_city, location_state, interests, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id, name, avatar,
                kwargs.get("language", "hi"),
                kwargs.get("persona", "desi"),
                kwargs.get("city", ""),
                kwargs.get("state", ""),
                json.dumps(kwargs.get("interests", [])),
                now, now,
            )
        )
        conn.commit()
        return self.get_profile(profile_id)

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a profile by ID."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM profiles ORDER BY is_primary DESC, name ASC")
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update_profile(self, profile_id: str, **kwargs) -> bool:
        """Update profile fields."""
        try:
            conn = self._get_conn()
            updates = []
            values = []

            field_map = {
                "name": "name",
                "avatar": "avatar",
                "language": "preferred_language",
                "persona": "preferred_persona",
                "city": "location_city",
                "state": "location_state",
            }

            for key, db_field in field_map.items():
                if key in kwargs:
                    updates.append(f"{db_field} = ?")
                    values.append(kwargs[key])

            if "interests" in kwargs:
                updates.append("interests = ?")
                values.append(json.dumps(kwargs["interests"]))

            if "accessibility" in kwargs:
                updates.append("accessibility = ?")
                values.append(json.dumps(kwargs["accessibility"]))

            if not updates:
                return False

            updates.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(profile_id)

            conn.execute(
                f"UPDATE profiles SET {', '.join(updates)} WHERE profile_id = ?",
                values
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
            return False

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile (cannot delete primary)."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT is_primary FROM profiles WHERE profile_id = ?", (profile_id,))
        row = cursor.fetchone()
        if not row or row["is_primary"]:
            return False
        conn.execute("DELETE FROM profiles WHERE profile_id = ?", (profile_id,))
        conn.commit()
        return True

    def get_active_profile(self) -> Dict[str, Any]:
        """Get the primary/active profile."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM profiles WHERE is_primary = 1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        # Fallback: get first profile
        profiles = self.list_profiles()
        return profiles[0] if profiles else {"profile_id": "default", "name": "User"}

    def switch_profile(self, profile_id: str) -> bool:
        """Switch active profile (set as primary)."""
        conn = self._get_conn()
        # Unset current primary
        conn.execute("UPDATE profiles SET is_primary = 0 WHERE is_primary = 1")
        # Set new primary
        conn.execute("UPDATE profiles SET is_primary = 1 WHERE profile_id = ?", (profile_id,))
        conn.commit()
        return True

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "profile_id": row["profile_id"],
            "name": row["name"],
            "avatar": row["avatar"],
            "language": row["preferred_language"],
            "persona": row["preferred_persona"],
            "city": row["location_city"],
            "state": row["location_state"],
            "interests": json.loads(row["interests"] or "[]"),
            "accessibility": json.loads(row["accessibility"] or "{}"),
            "is_primary": bool(row["is_primary"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


# Singleton
profile_manager = ProfileManager()
