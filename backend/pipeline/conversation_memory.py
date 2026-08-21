"""
Conversation Memory Module for Zenix AI.
Provides conversation summarization, context carryover, and long-term memory.
"""

import json
import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    tokens: int = 0
    tool_used: Optional[str] = None


@dataclass
class ConversationSummary:
    """Summary of a conversation."""
    session_id: str
    summary: str
    key_points: List[str]
    user_intent: str
    topics_discussed: List[str]
    created_at: str
    turn_count: int
    total_tokens: int


class ConversationMemory:
    """
    Manages conversation memory with summarization.
    Stores full conversations and creates summaries for context carryover.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "conversation_memory.db")
        self.db_path = os.path.realpath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._current_session: Optional[str] = None
        self._turns: List[ConversationTurn] = []

    def _init_db(self):
        """Initialize SQLite database for conversation storage."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                tokens INTEGER DEFAULT 0,
                tool_used TEXT
            );
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                summary TEXT,
                key_points TEXT,
                user_intent TEXT,
                topics_discussed TEXT,
                created_at TEXT,
                turn_count INTEGER,
                total_tokens INTEGER
            );
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                key TEXT,
                value TEXT,
                source TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
        """)
        conn.commit()
        conn.close()

    def start_session(self, session_id: str = None) -> str:
        """Start a new conversation session."""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._current_session = session_id
        self._turns = []
        return session_id

    def add_turn(self, role: str, content: str, tool_used: str = None, tokens: int = 0):
        """Add a turn to the current conversation."""
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            tokens=tokens,
            tool_used=tool_used,
        )
        self._turns.append(turn)

        # Persist to database
        if self._current_session:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO conversations (session_id, role, content, timestamp, tokens, tool_used) VALUES (?, ?, ?, ?, ?, ?)",
                (self._current_session, role, content, turn.timestamp, tokens, tool_used),
            )
            conn.commit()
            conn.close()

    def get_context(self, max_turns: int = 20, include_summary: bool = True) -> str:
        """
        Get conversation context for the LLM.
        Includes recent turns and optional summary of older turns.
        """
        context_parts = []

        # Add summary if available
        if include_summary and self._current_session:
            summary = self.get_latest_summary()
            if summary:
                context_parts.append(f"[Conversation Summary]\n{summary.summary}")
                if summary.key_points:
                    context_parts.append("Key points: " + "; ".join(summary.key_points))

        # Add recent turns
        recent_turns = self._turns[-max_turns:]
        for turn in recent_turns:
            prefix = "User" if turn.role == "user" else "Assistant"
            context_parts.append(f"{prefix}: {turn.content[:500]}")

        return "\n\n".join(context_parts)

    def summarize_session(self) -> Optional[ConversationSummary]:
        """
        Create a summary of the current conversation session.
        Uses extractive summarization (no LLM needed).
        """
        if not self._turns or not self._current_session:
            return None

        # Extract key information
        user_messages = [t.content for t in self._turns if t.role == "user"]
        assistant_messages = [t.content for t in self._turns if t.role == "assistant"]
        tools_used = [t.tool_used for t in self._turns if t.tool_used]

        # Build summary
        summary_parts = []
        key_points = []
        topics = set()

        # Extract topics from user messages
        for msg in user_messages:
            words = msg.lower().split()
            # Look for topic indicators
            for word in words:
                if len(word) > 4:
                    topics.add(word)

        # Create summary
        if user_messages:
            summary_parts.append(f"User asked about: {'; '.join(user_messages[:3])}")

        if tools_used:
            unique_tools = list(set(tools_used))
            summary_parts.append(f"Tools used: {', '.join(unique_tools)}")

        # Extract key points from assistant responses
        for msg in assistant_messages[:5]:
            # Get first sentence as key point
            sentences = msg.split('.')
            if sentences and len(sentences[0]) > 10:
                key_points.append(sentences[0].strip())

        summary_text = ". ".join(summary_parts) if summary_parts else "General conversation"

        # Calculate total tokens
        total_tokens = sum(t.tokens for t in self._turns)

        # Create summary object
        summary = ConversationSummary(
            session_id=self._current_session,
            summary=summary_text,
            key_points=key_points[:5],
            user_intent=user_messages[0][:200] if user_messages else "",
            topics_discussed=list(topics)[:10],
            created_at=datetime.now().isoformat(),
            turn_count=len(self._turns),
            total_tokens=total_tokens,
        )

        # Save to database
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO summaries 
               (session_id, summary, key_points, user_intent, topics_discussed, created_at, turn_count, total_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                summary.session_id,
                summary.summary,
                json.dumps(summary.key_points),
                summary.user_intent,
                json.dumps(summary.topics_discussed),
                summary.created_at,
                summary.turn_count,
                summary.total_tokens,
            ),
        )
        conn.commit()
        conn.close()

        return summary

    def get_latest_summary(self) -> Optional[ConversationSummary]:
        """Get the latest summary for the current session."""
        if not self._current_session:
            return None

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM summaries WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (self._current_session,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return ConversationSummary(
                session_id=row["session_id"],
                summary=row["summary"],
                key_points=json.loads(row["key_points"]) if row["key_points"] else [],
                user_intent=row["user_intent"] or "",
                topics_discussed=json.loads(row["topics_discussed"]) if row["topics_discussed"] else [],
                created_at=row["created_at"],
                turn_count=row["turn_count"],
                total_tokens=row["total_tokens"],
            )
        return None

    def get_session_history(self, session_id: str = None) -> List[Dict[str, Any]]:
        """Get full conversation history for a session."""
        session_id = session_id or self._current_session
        if not session_id:
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversation history by content."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM conversations WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation sessions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """SELECT session_id, MIN(timestamp) as started, MAX(timestamp) as ended,
                      COUNT(*) as turn_count
               FROM conversations
               GROUP BY session_id
               ORDER BY ended DESC
               LIMIT ?""",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def cleanup_old_sessions(self, days: int = 30):
        """Clean up conversation data older than specified days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM summaries WHERE created_at < ?", (cutoff,))
        conn.commit()
        conn.close()

        logger.info(f"Cleaned up conversations older than {days} days")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)

        total_turns = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]
        total_summaries = conn.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
        total_facts = conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0]

        conn.close()

        return {
            "total_turns": total_turns,
            "total_sessions": total_sessions,
            "total_summaries": total_summaries,
            "total_user_facts": total_facts,
            "current_session": self._current_session,
            "current_turns": len(self._turns),
        }


class UserFactStore:
    """
    Store and retrieve user facts across sessions.
    More sophisticated than simple key-value memory.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "conversation_memory.db")
        self.db_path = os.path.realpath(db_path)

    def remember(self, user_id: str, key: str, value: str, source: str = "user"):
        """Remember a fact about the user."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()

        # Check if fact exists
        existing = conn.execute(
            "SELECT id FROM user_facts WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE user_facts SET value = ?, source = ?, updated_at = ? WHERE id = ?",
                (value, source, now, existing[0]),
            )
        else:
            conn.execute(
                "INSERT INTO user_facts (user_id, key, value, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, key, value, source, now, now),
            )

        conn.commit()
        conn.close()

    def recall(self, user_id: str, key: str = None) -> Any:
        """Recall facts about the user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if key:
            cursor = conn.execute(
                "SELECT * FROM user_facts WHERE user_id = ? AND key = ?",
                (user_id, key),
            )
            row = cursor.fetchone()
            conn.close()
            return row["value"] if row else None
        else:
            cursor = conn.execute(
                "SELECT key, value FROM user_facts WHERE user_id = ?",
                (user_id,),
            )
            rows = cursor.fetchall()
            conn.close()
            return {row["key"]: row["value"] for row in rows}

    def forget(self, user_id: str, key: str):
        """Forget a specific fact."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM user_facts WHERE user_id = ? AND key = ?", (user_id, key))
        conn.commit()
        conn.close()

    def get_context_string(self, user_id: str) -> str:
        """Get a formatted string of user facts for LLM context."""
        facts = self.recall(user_id)
        if not facts:
            return ""

        lines = ["[User Profile]"]
        for key, value in facts.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)


# Singleton instances
_conversation_memory = None
_user_fact_store = None


def get_conversation_memory() -> ConversationMemory:
    """Get or create the conversation memory singleton."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory


def get_user_fact_store() -> UserFactStore:
    """Get or create the user fact store singleton."""
    global _user_fact_store
    if _user_fact_store is None:
        _user_fact_store = UserFactStore()
    return _user_fact_store
