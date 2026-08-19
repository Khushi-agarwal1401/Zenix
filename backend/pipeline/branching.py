"""
Conversation Branching — allows users to go back to any point and fork conversations.

Tree-based message storage where each message can have children (branches).
Users can branch off from any message to explore different conversation paths.
"""

import json
import logging
import sqlite3
import os
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationBranch:
    """Represents a single node in the conversation tree."""

    def __init__(self, message_id: str, content: str, role: str, parent_id: str = None,
                 branch_id: str = "main", timestamp: str = None, persona: str = "desi",
                 metadata: Dict = None):
        self.message_id = message_id
        self.content = content
        self.role = role  # 'user' or 'assistant'
        self.parent_id = parent_id
        self.branch_id = branch_id
        self.timestamp = timestamp or datetime.now().isoformat()
        self.persona = persona
        self.metadata = metadata or {}
        self.children: List[str] = []  # message_ids of child branches


class BranchingConversationStore:
    """SQLite-backed conversation tree with branching support."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "conversations.db")
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
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                content TEXT,
                role TEXT,
                parent_id TEXT,
                branch_id TEXT DEFAULT 'main',
                timestamp TEXT,
                persona TEXT DEFAULT 'desi',
                metadata TEXT DEFAULT '{}',
                PRIMARY KEY (session_id, message_id)
            );
            CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_parent ON conversations(session_id, parent_id);
            CREATE INDEX IF NOT EXISTS idx_branch ON conversations(session_id, branch_id);
        """)
        conn.commit()

    def add_message(self, session_id: str, message_id: str, content: str, role: str,
                    parent_id: str = None, branch_id: str = "main",
                    persona: str = "desi", metadata: Dict = None) -> bool:
        """Add a message to the conversation tree."""
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO conversations
                   (session_id, message_id, content, role, parent_id, branch_id, timestamp, persona, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, message_id, content, role, parent_id, branch_id,
                 datetime.now().isoformat(), persona, json.dumps(metadata or {}))
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return False

    def get_thread(self, session_id: str, branch_id: str = "main") -> List[Dict[str, Any]]:
        """Get all messages in a branch, ordered chronologically."""
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT * FROM conversations
               WHERE session_id = ? AND branch_id = ?
               ORDER BY timestamp ASC""",
            (session_id, branch_id)
        )
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "message_id": row["message_id"],
                "content": row["content"],
                "role": row["role"],
                "parent_id": row["parent_id"],
                "branch_id": row["branch_id"],
                "timestamp": row["timestamp"],
                "persona": row["persona"],
                "metadata": json.loads(row["metadata"] or "{}"),
            })
        return messages

    def get_branches(self, session_id: str) -> List[Dict[str, Any]]:
        """List all branches for a session."""
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT branch_id, COUNT(*) as msg_count, MIN(timestamp) as started,
                      MAX(timestamp) as last_active
               FROM conversations
               WHERE session_id = ?
               GROUP BY branch_id
               ORDER BY started ASC""",
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def fork_from(self, session_id: str, from_message_id: str, new_branch_id: str) -> bool:
        """Fork a new branch from a specific message."""
        conn = self._get_conn()
        # Verify the message exists
        cursor = conn.execute(
            "SELECT 1 FROM conversations WHERE session_id = ? AND message_id = ?",
            (session_id, from_message_id)
        )
        if not cursor.fetchone():
            return False

        # Get all messages up to the fork point in the original branch
        cursor = conn.execute(
            "SELECT branch_id FROM conversations WHERE session_id = ? AND message_id = ?",
            (session_id, from_message_id)
        )
        row = cursor.fetchone()
        if not row:
            return False
        original_branch = row["branch_id"]

        # Copy messages from original branch up to fork point into new branch
        cursor = conn.execute(
            """SELECT * FROM conversations
               WHERE session_id = ? AND branch_id = ?
               AND timestamp <= (SELECT timestamp FROM conversations
                                 WHERE session_id = ? AND message_id = ?)
               ORDER BY timestamp ASC""",
            (session_id, original_branch, session_id, from_message_id)
        )

        for msg in cursor.fetchall():
            conn.execute(
                """INSERT OR IGNORE INTO conversations
                   (session_id, message_id, content, role, parent_id, branch_id,
                    timestamp, persona, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, f"{new_branch_id}_{msg['message_id']}", msg["content"],
                 msg["role"], msg["parent_id"], new_branch_id,
                 msg["timestamp"], msg["persona"], msg["metadata"])
            )
        conn.commit()
        return True

    def delete_branch(self, session_id: str, branch_id: str) -> bool:
        """Delete a branch (cannot delete 'main')."""
        if branch_id == "main":
            return False
        try:
            conn = self._get_conn()
            conn.execute(
                "DELETE FROM conversations WHERE session_id = ? AND branch_id = ?",
                (session_id, branch_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete branch: {e}")
            return False

    def get_message_count(self, session_id: str) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE session_id = ?",
            (session_id,)
        )
        return cursor.fetchone()["cnt"]

    def export_session(self, session_id: str, format: str = "json") -> str:
        """Export entire session with all branches."""
        branches = self.get_branches(session_id)
        data = {"session_id": session_id, "branches": {}}

        for branch in branches:
            data["branches"][branch["branch_id"]] = self.get_thread(session_id, branch["branch_id"])

        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format == "markdown":
            lines = [f"# Conversation: {session_id}\n"]
            for branch_id, messages in data["branches"].items():
                lines.append(f"\n## Branch: {branch_id}\n")
                for msg in messages:
                    role = "**You**" if msg["role"] == "user" else "**Zenix**"
                    lines.append(f"{role}: {msg['content']}\n")
            return "\n".join(lines)
        return json.dumps(data, ensure_ascii=False)


# Singleton
branching_store = BranchingConversationStore()
