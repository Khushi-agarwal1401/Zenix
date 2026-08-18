"""
Response Cache for Zenix AI.
Caches LLM responses to avoid redundant calls for identical queries.
Uses an in-memory LRU cache with configurable TTL.
"""

import time
import hashlib
import threading
from collections import OrderedDict
from typing import Optional, Any


class ResponseCache:
    """
    Thread-safe LRU cache with TTL expiration.
    Stores response text keyed by (message, persona) hash.
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        """
        Args:
            max_size: Maximum number of cached entries.
            ttl_seconds: Time-to-live for each entry (default 1 hour).
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, message: str, persona: str) -> str:
        """Generate a cache key from message and persona."""
        raw = f"{message.strip().lower()}|{persona}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, message: str, persona: str) -> Optional[str]:
        """Retrieve a cached response if available and not expired."""
        key = self._make_key(message, persona)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check TTL
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry["response"]

    def set(self, message: str, persona: str, response: str):
        """Store a response in the cache."""
        key = self._make_key(message, persona)

        with self._lock:
            # If key exists, update it
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = {"response": response, "timestamp": time.time()}
                return

            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = {"response": response, "timestamp": time.time()}

    def clear(self):
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "0%",
                "ttl_seconds": self.ttl_seconds,
            }

    def cleanup_expired(self):
        """Remove all expired entries."""
        now = time.time()
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if now - entry["timestamp"] > self.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                print(f"Cache cleanup: removed {len(expired_keys)} expired entries")


# Module-level singleton
response_cache = ResponseCache(max_size=500, ttl_seconds=3600)
