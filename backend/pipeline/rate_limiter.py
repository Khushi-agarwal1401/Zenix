"""
Token Bucket Rate Limiter for Zenix AI.
Per-session rate limiting to prevent abuse and manage costs.
"""

import time
import threading
from typing import Optional


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    Each session gets a bucket that refills tokens over time.
    """

    def __init__(self, capacity: int = 20, refill_rate: float = 0.5):
        """
        Args:
            capacity: Max tokens (burst size).
            refill_rate: Tokens added per second.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        Returns True if allowed, False if rate limited.
        """
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def retry_after(self) -> float:
        """Seconds until the next token is available."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate


class RateLimiter:
    """
    Global rate limiter that manages per-session token buckets.
    """

    def __init__(self, capacity: int = 20, refill_rate: float = 0.5):
        """
        Args:
            capacity: Max requests per session (burst).
            refill_rate: Requests refilled per second (sustained rate).
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

        # Stats
        self._total_requests = 0
        self._total_rejected = 0

    def _get_bucket(self, session_id: str) -> TokenBucket:
        """Get or create a token bucket for a session."""
        with self._lock:
            if session_id not in self._buckets:
                self._buckets[session_id] = TokenBucket(
                    capacity=self.capacity, refill_rate=self.refill_rate
                )
            return self._buckets[session_id]

    def check(self, session_id: str) -> dict:
        """
        Check if a request is allowed.

        Returns:
            {
                "allowed": bool,
                "remaining": int,       # Tokens left
                "retry_after": float,   # Seconds to wait (0 if allowed)
                "limit": int,           # Max burst
            }
        """
        self._total_requests += 1
        bucket = self._get_bucket(session_id)
        allowed = bucket.consume(1)

        if not allowed:
            self._total_rejected += 1
            return {
                "allowed": False,
                "remaining": 0,
                "retry_after": bucket.retry_after,
                "limit": self.capacity,
            }

        return {
            "allowed": True,
            "remaining": int(bucket.tokens),
            "retry_after": 0.0,
            "limit": self.capacity,
        }

    def cleanup_stale(self, max_age: float = 3600):
        """Remove buckets that haven't been used recently."""
        now = time.time()
        with self._lock:
            stale = [
                sid for sid, bucket in self._buckets.items()
                if now - bucket.last_refill > max_age
            ]
            for sid in stale:
                del self._buckets[sid]
            return len(stale)

    def stats(self) -> dict:
        """Return rate limiter statistics."""
        with self._lock:
            return {
                "active_sessions": len(self._buckets),
                "total_requests": self._total_requests,
                "total_rejected": self._total_rejected,
                "rejection_rate": (
                    f"{self._total_rejected / self._total_requests * 100:.1f}%"
                    if self._total_requests > 0 else "0%"
                ),
                "capacity": self.capacity,
                "refill_rate": f"{self.refill_rate}/sec",
            }


# Module-level singleton (20 burst, 0.5/sec sustained = ~30 req/min)
rate_limiter = RateLimiter(capacity=20, refill_rate=0.5)
