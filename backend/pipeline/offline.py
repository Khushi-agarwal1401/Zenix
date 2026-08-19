"""
Offline Mode Support — cached responses, local knowledge, sync queue.

Provides:
- Response caching for common queries
- Local knowledge snippets for offline use
- Sync queue for messages composed offline
- Service worker manifest generation
"""

import json
import os
import hashlib
import logging
import sqlite3
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OfflineCache:
    """SQLite-backed offline response cache and sync queue."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "offline_cache.db")
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
            CREATE TABLE IF NOT EXISTS cached_responses (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                response TEXT,
                persona TEXT DEFAULT 'desi',
                tool_used TEXT,
                cached_at TEXT,
                expires_at TEXT,
                hit_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                message TEXT,
                persona TEXT DEFAULT 'desi',
                created_at TEXT,
                synced INTEGER DEFAULT 0,
                synced_at TEXT
            );
            CREATE TABLE IF NOT EXISTS offline_knowledge (
                topic TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT
            );
        """)
        conn.commit()
        self._seed_offline_knowledge()

    def _seed_offline_knowledge(self):
        """Seed commonly needed info for offline use."""
        knowledge = {
            "emergency_numbers": """🚨 Emergency Numbers (Always Available):
- Police: 100
- Fire: 101
- Ambulance: 108
- Women Helpline: 1091
- Child Helpline: 1098
- Disasters: 112
- Tourist Helpline: 1363
- Blood Bank: 104""",
            "upi_basics": """💳 UPI Basics (Offline):
UPI = Unified Payments Interface
- Send money: Open any UPI app → Enter recipient UPI ID → Enter amount → Enter PIN
- Receive money: Share your UPI ID with sender
- Check balance: UPI app → Check Balance → Enter PIN
- UPI ID format: name@bank (e.g., ram@oksbi)
- Daily limit: ₹1,00,000 (most banks)""",
            "aadhaar_basics": """🆔 Aadhaar Basics (Offline):
- Update address: Visit Aadhaar centre or uidai.gov.in
- Download e-Aadhaar: myaadhaar.uidai.gov.in
- Check Aadhaar status: 1947 (toll-free)
- Link PAN: incometax.gov.in
- Balance check: Give missed call to 9223123123""",
            "common_schemes": """🏛️ Common Govt Schemes:
- PM-KISAN: Rs 6,000/yr for farmers (pmkisan.gov.in)
- Ayushman Bharat: Rs 5 lakh health cover (pmjay.gov.in)
- PM Ujjwala: Free LPG connection (pmujjwala.gov.in)
- PMKVY: Free skill training (pmkvyofficial.org)
- MUDRA Loan: Up to Rs 10 lakh for business (mudra.org.in)""",
            "rights": """⚖️ Basic Rights:
- Right to Information (RTI): File at rtionline.gov.in
- Consumer Rights: Complaint at consumerhelpline.gov.in
- Legal Aid: Call 15100 (National Legal Aid)
- Property Rights: Registration at sub-registrar office""",
            "weather_advisory": """🌤️ Weather Safety Tips:
- Heat wave: Stay hydrated, avoid 12-3 PM sun
- Flood: Move to higher ground, don't walk in water
- Cyclone: Stay indoors, away from windows
- Cold wave: Layer clothing, keep warm room
- Lightning: Don't use electronics, stay indoors""",
        }

        conn = self._get_conn()
        now = datetime.now().isoformat()
        for topic, content in knowledge.items():
            conn.execute(
                "INSERT OR IGNORE INTO offline_knowledge (topic, content, updated_at) VALUES (?, ?, ?)",
                (topic, content, now)
            )
        conn.commit()

    def cache_response(self, query: str, response: str, persona: str = "desi",
                       tool_used: str = None, ttl_hours: int = 24) -> bool:
        """Cache a response for offline use."""
        try:
            query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
            now = datetime.now()
            expires = now + timedelta(hours=ttl_hours)

            conn = self._get_conn()
            conn.execute(
                """INSERT OR REPLACE INTO cached_responses
                   (query_hash, query, response, persona, tool_used, cached_at, expires_at, hit_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                (query_hash, query, response, persona, tool_used,
                 now.isoformat(), expires.isoformat())
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Cache write failed: {e}")
            return False

    def get_cached(self, query: str) -> Optional[Dict[str, Any]]:
        """Get a cached response if available and not expired."""
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT * FROM cached_responses
               WHERE query_hash = ? AND expires_at > ?""",
            (query_hash, datetime.now().isoformat())
        )
        row = cursor.fetchone()
        if row:
            # Increment hit count
            conn.execute(
                "UPDATE cached_responses SET hit_count = hit_count + 1 WHERE query_hash = ?",
                (query_hash,)
            )
            conn.commit()
            return {
                "response": row["response"],
                "persona": row["persona"],
                "tool_used": row["tool_used"],
                "cached_at": row["cached_at"],
                "hit_count": row["hit_count"] + 1,
            }
        return None

    def get_offline_knowledge(self, topic: str = None) -> Any:
        """Get offline knowledge snippets."""
        conn = self._get_conn()
        if topic:
            cursor = conn.execute(
                "SELECT * FROM offline_knowledge WHERE topic = ?", (topic,)
            )
            row = cursor.fetchone()
            return row["content"] if row else None
        else:
            cursor = conn.execute("SELECT * FROM offline_knowledge")
            return {row["topic"]: row["content"] for row in cursor.fetchall()}

    def queue_sync(self, session_id: str, message: str, persona: str = "desi") -> bool:
        """Queue a message for sync when back online."""
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO sync_queue (session_id, message, persona, created_at, synced)
                   VALUES (?, ?, ?, ?, 0)""",
                (session_id, message, persona, datetime.now().isoformat())
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Sync queue failed: {e}")
            return False

    def get_pending_sync(self) -> List[Dict[str, Any]]:
        """Get all pending messages to sync."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM sync_queue WHERE synced = 0 ORDER BY created_at ASC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_synced(self, ids: List[int]):
        """Mark messages as synced."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        for msg_id in ids:
            conn.execute(
                "UPDATE sync_queue SET synced = 1, synced_at = ? WHERE id = ?",
                (now, msg_id)
            )
        conn.commit()

    def get_cache_stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        cached = conn.execute("SELECT COUNT(*) as cnt FROM cached_responses").fetchone()["cnt"]
        pending = conn.execute("SELECT COUNT(*) as cnt FROM sync_queue WHERE synced = 0").fetchone()["cnt"]
        knowledge = conn.execute("SELECT COUNT(*) as cnt FROM offline_knowledge").fetchone()["cnt"]
        return {"cached_responses": cached, "pending_sync": pending, "offline_knowledge": knowledge}


# Service worker manifest for offline support
def generate_sw_manifest() -> Dict[str, Any]:
    """Generate a service worker cache manifest."""
    return {
        "version": "1.0.0",
        "cacheName": "zenix-offline-v1",
        "precache": [
            "/",
            "/offline.html",
        ],
        "runtimeCache": {
            "images": {"strategy": "CacheFirst", "maxEntries": 50, "maxAgeSeconds": 86400},
            "api": {"strategy": "NetworkFirst", "maxEntries": 100, "maxAgeSeconds": 3600},
            "static": {"strategy": "CacheFirst", "maxEntries": 30, "maxAgeSeconds": 604800},
        },
        "fallback": "/offline.html",
    }


# Singleton
offline_cache = OfflineCache()
