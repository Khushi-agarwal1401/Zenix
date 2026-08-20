"""
Abuse Prevention for Zenix AI.

Detects and mitigates:
  1. Spam: Repeated identical/near-identical messages
  2. Prompt injection escalation: Ban after repeated injection attempts
  3. Excessive tool abuse: Rate-limit heavy tool usage
  4. Session abuse tracking: Flag problematic sessions

Integrates with the rate_limiter and input_guard modules.
"""

import re
import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class SessionTracker:
    """Track per-session behavior for abuse detection."""

    def __init__(
        self,
        spam_window: int = 60,       # seconds to look back for spam
        spam_threshold: int = 3,     # identical messages in window = spam
        injection_threshold: int = 3,  # injection attempts before ban
        ban_duration: int = 3600,    # ban duration in seconds (1 hour)
        tool_rate_limit: int = 20,   # max tool calls per minute
    ):
        self.spam_window = spam_window
        self.spam_threshold = spam_threshold
        self.injection_threshold = injection_threshold
        self.ban_duration = ban_duration
        self.tool_rate_limit = tool_rate_limit

        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        """Get or create session tracking data."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "messages": [],           # [(timestamp, message, similarity)]
                    "injection_attempts": 0,
                    "tool_calls": [],         # [timestamp]
                    "banned_until": 0,
                    "warnings": 0,
                    "created_at": time.time(),
                }
            return self._sessions[session_id]

    def check_session(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Check if a message should be allowed, warned, or blocked.

        Returns:
        {
            "allowed": bool,
            "reason": str,
            "severity": "ok" | "warning" | "blocked",
            "retry_after": float,
        }
        """
        session = self._get_session(session_id)
        now = time.time()

        # Check if session is banned
        if session["banned_until"] > now:
            remaining = session["banned_until"] - now
            return {
                "allowed": False,
                "reason": f"Session temporarily suspended. Try again in {remaining:.0f}s.",
                "severity": "blocked",
                "retry_after": remaining,
            }

        # ── Spam Detection ──────────────────────────────────────────────
        spam_check = self._check_spam(session, message, now)
        if spam_check["is_spam"]:
            session["warnings"] += 1
            # Escalate warnings to ban
            if session["warnings"] >= 3:
                session["banned_until"] = now + self.ban_duration
                logger.warning(f"Session {session_id[:8]} banned for repeated spam")
                return {
                    "allowed": False,
                    "reason": "Too many repeated messages. Session suspended for 1 hour.",
                    "severity": "blocked",
                    "retry_after": self.ban_duration,
                }
            return {
                "allowed": True,
                "reason": spam_check["reason"],
                "severity": "warning",
                "retry_after": 0,
            }

        # ── Injection Tracking ──────────────────────────────────────────
        # (Injection detection is handled by input_guard, we just track escalation)
        # This is called externally after input_guard detects injection

        return {
            "allowed": True,
            "reason": "",
            "severity": "ok",
            "retry_after": 0,
        }

    def record_injection_attempt(self, session_id: str) -> Dict[str, Any]:
        """Record a prompt injection attempt and check for escalation."""
        session = self._get_session(session_id)
        session["injection_attempts"] += 1

        if session["injection_attempts"] >= self.injection_threshold:
            session["banned_until"] = time.time() + self.ban_duration
            logger.warning(
                f"Session {session_id[:8]} banned: "
                f"{session['injection_attempts']} injection attempts"
            )
            return {
                "allowed": False,
                "reason": "Multiple prompt injection attempts detected. Session suspended.",
                "severity": "blocked",
                "attempts": session["injection_attempts"],
            }

        return {
            "allowed": True,
            "reason": f"Injection attempt {session['injection_attempts']}/{self.injection_threshold}",
            "severity": "warning",
            "attempts": session["injection_attempts"],
        }

    def check_tool_rate(self, session_id: str) -> Dict[str, Any]:
        """Check if the session is exceeding tool call rate limits."""
        session = self._get_session(session_id)
        now = time.time()
        cutoff = now - 60  # last 60 seconds

        # Clean old tool calls
        session["tool_calls"] = [t for t in session["tool_calls"] if t > cutoff]

        if len(session["tool_calls"]) >= self.tool_rate_limit:
            return {
                "allowed": False,
                "reason": f"Too many tool calls ({len(session['tool_calls'])}/min). Please slow down.",
                "severity": "warning",
                "count": len(session["tool_calls"]),
            }

        session["tool_calls"].append(now)
        return {
            "allowed": True,
            "reason": "",
            "severity": "ok",
            "count": len(session["tool_calls"]),
        }

    def record_message(self, session_id: str, message: str):
        """Record a message for spam tracking."""
        session = self._get_session(session_id)
        now = time.time()
        session["messages"].append((now, message))

        # Clean old messages outside the spam window
        cutoff = now - self.spam_window
        session["messages"] = [
            (t, m) for t, m in session["messages"] if t > cutoff
        ]

    def _check_spam(self, session: Dict, message: str, now: float) -> Dict[str, Any]:
        """Check if the message is spam (repeated identical/near-identical)."""
        cutoff = now - self.spam_window
        recent_messages = [(t, m) for t, m in session["messages"] if t > cutoff]

        if len(recent_messages) < self.spam_threshold - 1:
            return {"is_spam": False, "reason": ""}

        message_lower = message.lower().strip()

        # Check for exact duplicates
        exact_count = sum(
            1 for _, m in recent_messages
            if m.lower().strip() == message_lower
        )
        if exact_count >= self.spam_threshold - 1:
            return {
                "is_spam": True,
                "reason": f"Repeated identical message detected ({exact_count + 1} times).",
            }

        # Check for near-duplicates (similarity > 0.85)
        near_count = 0
        for _, prev_msg in recent_messages:
            prev_lower = prev_msg.lower().strip()
            similarity = SequenceMatcher(None, message_lower, prev_lower).ratio()
            if similarity > 0.85:
                near_count += 1

        if near_count >= self.spam_threshold - 1:
            return {
                "is_spam": True,
                "reason": f"Repeated similar message detected ({near_count + 1} times).",
            }

        return {"is_spam": False, "reason": ""}

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get abuse stats for a session."""
        session = self._get_session(session_id)
        now = time.time()
        return {
            "session_id": session_id,
            "warnings": session["warnings"],
            "injection_attempts": session["injection_attempts"],
            "tool_calls_last_min": sum(
                1 for t in session["tool_calls"] if t > now - 60
            ),
            "is_banned": session["banned_until"] > now,
            "banned_until": session["banned_until"] if session["banned_until"] > now else None,
            "message_count": len(session["messages"]),
            "age_seconds": now - session["created_at"],
        }

    def cleanup_stale(self, max_age: float = 7200):
        """Remove sessions older than max_age seconds."""
        now = time.time()
        with self._lock:
            stale = [
                sid for sid, data in self._sessions.items()
                if now - data["created_at"] > max_age
            ]
            for sid in stale:
                del self._sessions[sid]
            return len(stale)

    def stats(self) -> Dict[str, Any]:
        """Global abuse prevention stats."""
        with self._lock:
            total = len(self._sessions)
            banned = sum(
                1 for s in self._sessions.values()
                if s["banned_until"] > time.time()
            )
            total_warnings = sum(s["warnings"] for s in self._sessions.values())
            total_injections = sum(
                s["injection_attempts"] for s in self._sessions.values()
            )
            return {
                "active_sessions": total,
                "banned_sessions": banned,
                "total_warnings": total_warnings,
                "total_injection_attempts": total_injections,
            }


# Module-level singleton
abuse_tracker = SessionTracker()
