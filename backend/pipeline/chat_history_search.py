"""
Chat History Search Module for Zenix AI.
Provides search functionality across conversation history.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ChatHistorySearch:
    """
    Search across conversation history.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "conversation_memory.db")
        self.db_path = os.path.realpath(db_path)

    def search(self, query: str, user_id: str = None,
              start_date: str = None, end_date: str = None,
              limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search conversation history.

        Args:
            query: Search query
            user_id: Filter by user ID
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            limit: Maximum results

        Returns:
            List of matching conversation entries
        """
        if not os.path.exists(self.db_path):
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            query_lower = query.lower()
            results = []

            # Build query
            sql = "SELECT * FROM conversations WHERE 1=1"
            params = []

            if user_id:
                sql += " AND user_id = ?"
                params.append(user_id)

            if start_date:
                sql += " AND timestamp >= ?"
                params.append(start_date)

            if end_date:
                sql += " AND timestamp <= ?"
                params.append(end_date)

            sql += " ORDER BY timestamp DESC"

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            # Filter by search query (since SQLite LIKE is limited)
            for row in rows:
                content = row["content"].lower()
                if query_lower in content:
                    results.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                        "relevance": self._calculate_relevance(query_lower, content),
                    })

                    if len(results) >= limit:
                        break

            conn.close()

            # Sort by relevance
            results.sort(key=lambda x: x["relevance"], reverse=True)

            return results

        except Exception as e:
            logger.error(f"Chat history search failed: {e}")
            return []

    def search_summaries(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversation summaries."""
        if not os.path.exists(self.db_path):
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("SELECT * FROM summaries ORDER BY created_at DESC")
            rows = cursor.fetchall()

            results = []
            query_lower = query.lower()

            for row in rows:
                summary = row["summary"].lower()
                topics = row["topics_discussed"].lower() if row["topics_discussed"] else ""

                if query_lower in summary or query_lower in topics:
                    results.append({
                        "session_id": row["session_id"],
                        "summary": row["summary"],
                        "topics": row["topics_discussed"],
                        "created_at": row["created_at"],
                        "turn_count": row["turn_count"],
                    })

                    if len(results) >= limit:
                        break

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Summary search failed: {e}")
            return []

    def get_recent_context(self, user_id: str, session_id: str = None,
                          max_turns: int = 10) -> str:
        """
        Get recent conversation context for a user.

        Args:
            user_id: User identifier
            session_id: Specific session ID (optional)
            max_turns: Maximum turns to include

        Returns:
            Formatted context string
        """
        if not os.path.exists(self.db_path):
            return ""

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM conversations WHERE user_id = ?"
            params = [user_id]

            if session_id:
                sql += " AND session_id = ?"
                params.append(session_id)

            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(max_turns)

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()

            # Reverse to get chronological order
            rows = list(reversed(rows))

            context_parts = []
            for row in rows:
                role = "User" if row["role"] == "user" else "Assistant"
                content = row["content"][:200]  # Truncate long messages
                context_parts.append(f"{role}: {content}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return ""

    def get_session_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's conversation history."""
        if not os.path.exists(self.db_path):
            return {}

        try:
            conn = sqlite3.connect(self.db_path)

            # Total conversations
            total = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            # Total sessions
            sessions = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM conversations WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            # First and last conversation
            first = conn.execute(
                "SELECT MIN(timestamp) FROM conversations WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            last = conn.execute(
                "SELECT MAX(timestamp) FROM conversations WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            conn.close()

            return {
                "total_messages": total,
                "total_sessions": sessions,
                "first_conversation": first,
                "last_conversation": last,
            }

        except Exception as e:
            logger.error(f"Stats retrieval failed: {e}")
            return {}

    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score for search result."""
        # Simple relevance based on query word frequency
        query_words = set(query.split())
        content_words = set(content.split())

        overlap = len(query_words.intersection(content_words))
        total = len(query_words)

        return (overlap / total * 100) if total > 0 else 0


# Singleton instance
_chat_history_search = None


def get_chat_history_search() -> ChatHistorySearch:
    """Get or create the chat history search singleton."""
    global _chat_history_search
    if _chat_history_search is None:
        _chat_history_search = ChatHistorySearch()
    return _chat_history_search
