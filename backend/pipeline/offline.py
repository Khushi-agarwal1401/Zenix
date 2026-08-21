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
- Blood Bank: 104
- Cybercrime: 1930
- Senior Citizen: 14567""",
            "upi_basics": """💳 UPI Basics (Offline):
UPI = Unified Payments Interface
- Send money: Open any UPI app → Enter recipient UPI ID → Enter amount → Enter PIN
- Receive money: Share your UPI ID with sender
- Check balance: UPI app → Check Balance → Enter PIN
- UPI ID format: name@bank (e.g., ram@oksbi)
- Daily limit: ₹1,00,000 (most banks)
- NEVER share UPI PIN or OTP with anyone
- Fraud? Call bank immediately + 1930""",
            "aadhaar_basics": """🆔 Aadhaar Basics (Offline):
- Update address: Visit Aadhaar centre or uidai.gov.in
- Download e-Aadhaar: myaadhaar.uidai.gov.in
- Check Aadhaar status: 1947 (toll-free)
- Link PAN: incometax.gov.in
- Balance check: Give missed call to 9223123123
- Lock biometrics: myaadhaar.uidai.gov.in (for safety)
- Virtual ID: Generate at uidai.gov.in (16-digit temporary ID)""",
            "pan_basics": """📋 PAN Card Basics (Offline):
- Apply online: incometax.gov.in or NSDL/UTIITSL
- Check PAN-Aadhaar link: incometax.gov.in → Link Aadhaar Status
- PAN format: AABCP1234C (5 letters, 4 digits, 1 letter)
- Lost PAN: Apply for duplicate at NSDL
- Fee: Rs 110 (Indian), Rs 1,020 (foreign)
- Correction: Free online at incometax.gov.in""",
            "common_schemes": """🏛️ Common Govt Schemes:
- PM-KISAN: Rs 6,000/yr for farmers (pmkisan.gov.in)
- Ayushman Bharat: Rs 5 lakh health cover (pmjay.gov.in)
- PM Ujjwala: Free LPG connection (pmujjwala.gov.in)
- PMKVY: Free skill training (pmkvyofficial.org)
- MUDRA Loan: Up to Rs 10 lakh for business (mudra.org.in)
- Sukanya Samriddhi: Girl child savings (8.2% interest)
- PM Awas: Housing for all (pmaymis.gov.in)
- Atal Pension: Pension for unorganized (atalpension.yojana.gov.in)""",
            "rights": """⚖️ Basic Rights:
- Right to Information (RTI): File at rtionline.gov.in
- Consumer Rights: Complaint at consumerhelpline.gov.in
- Legal Aid: Call 15100 (National Legal Aid)
- Property Rights: Registration at sub-registrar office
- Right to Education: Free for ages 6-14 (RTE Act)
- Fundamental Rights: Art 14-32 of Constitution""",
            "weather_advisory": """🌤️ Weather Safety Tips:
- Heat wave: Stay hydrated, avoid 12-3 PM sun
- Flood: Move to higher ground, don't walk in water
- Cyclone: Stay indoors, away from windows
- Cold wave: Layer clothing, keep warm room
- Lightning: Don't use electronics, stay indoors
- Earthquake: Drop, Cover, Hold On. Stay away from windows""",
            "fraud_prevention": """🛡️ Fraud Prevention Tips:
- NEVER share OTP, UPI PIN, CVV, or passwords
- Bank will NEVER call asking for PIN/OTP
- UPI fraud? Call 1930 IMMEDIATELY
- Fake calls: Don't trust "bank officer" asking for details
- Lottery/prize scams: If it's too good to be true, it is
- SIM swap fraud: Report to police + bank immediately
- Online shopping: Pay only through official apps/websites""",
            "passport_basics": """🛂 Passport Basics (Offline):
- Apply online: passportindia.gov.in
- Documents needed: Aadhaar, PAN, birth proof, address proof
- Fee: Rs 1,500 (36 pages), Rs 2,000 (60 pages)
- Tatkal: Rs 2,000 (36 pages), Rs 3,500 (60 pages)
- Normal processing: 30-45 days
- Tatkal: 1-3 days
- Track application: passportindia.gov.in → Track Status""",
            "driving_license": """🚗 Driving License Basics (Offline):
- Apply online: parivahan.gov.in
- Learner's License: Age 16+ (gearless), 18+ (gear)
- Documents: Aadhaar, age proof, address proof, photos
- Fee: Rs 200-500 (LL), Rs 200-1000 (DL)
- LL validity: 6 months
- DL validity: 20 years (until 50 years age)
- Renewal: 30 days before expiry
- International DL: Available at parivahan.gov.in""",
            "insurance_basics": """🏥 Insurance Basics (Offline):
- Health Insurance: IRDAI regulates (irdai.gov.in)
- Life Insurance: IRDAI regulates
- Vehicle Insurance: Mandatory third-party
- Claim within: 7-30 days (varies by policy)
- Free-look period: 15 days (can cancel)
- Grievance: irdai.gov.in or call 155255
- Cashless treatment: At network hospitals only""",
            "banking_basics": """🏦 Banking Basics (Offline):
- Open account: Aadhaar + PAN + address proof
- Interest rates: 3-7% (savings), 6-8% (FD)
- NEFT: Available 24x7 (since Dec 2020)
- RTGS: For amounts ≥ Rs 2 lakh
- IMPS: Instant transfer 24x7
- Minimum balance: Rs 0-10,000 (varies by bank)
- ATM withdrawal: Free 5 times/month (own bank)
- UPI: Free for individuals (merchants may pay)""",
            "tax_basics": """💰 Tax Basics (Offline):
- ITR filing deadline: July 31 (individuals)
- Tax audit deadline: October 31
- Old regime: With deductions (80C, HRA, etc.)
- New regime: Lower rates, no deductions (default)
- Section 80C: Rs 1.5 lakh deduction (LIC, PPF, ELSS)
- Section 80D: Rs 25,000 health insurance (Rs 50,000 senior)
- Capital gains: 10% above Rs 1 lakh (equity)
- TDS: Deducted at source by employer/bank""",
            "electricity_basics": """⚡ Electricity Basics (Offline):
- Pay bill: UPI apps, discom website, or app
- Complaint: Call 1912 (most states)
- New connection: Apply at discom office/portal
- Solar rooftop subsidy: 40% (up to 3kW)
- Meter reading: Usually monthly (1st-5th)
- Late fee: Rs 100-500/month
- BPL families: Subsidized rates available""",
            "food_safety": """🍽️ Food Safety Tips (Offline):
- Check FSSAI license on packaged food
- Expiry date: Always check before consuming
- Food complaint: Call 1800-111-003 (FSSAI)
- Restaurant hygiene: Check FSSAI rating
- Street food: Eat at clean, busy stalls
- Milk: Boil before drinking (raw milk risk)
- Water: Drink purified/bottled water in unknown areas""",
            "legal_aid": """⚖️ Free Legal Aid (Offline):
- National Legal Aid: 15100 (toll-free)
- NALSA: nalsa.gov.in
- Free for: SC/ST, women, children, disabled, disaster victims
- District Legal Services Authority: Visit local court
- Legal Services Clinics: At district courts
- Lok Adalat: Free dispute resolution
- Consumer Forum: File complaint at edaakhil.nic.in""",
            "digital_safety": """🔒 Digital Safety Tips (Offline):
- Use strong passwords: 12+ characters, mix of letters/numbers/symbols
- Enable 2FA on all important accounts
- Don't click unknown links (phishing)
- Use official apps only (download from Play Store/App Store)
- Public WiFi: Avoid banking/sensitive activities
- Update phone regularly (security patches)
- Backup data: Google Photos, iCloud, or computer""",
            "travel_safety": """✈️ Travel Safety Tips (Offline):
- Keep copies of: Aadhaar, PAN, passport, tickets
- Share itinerary with family/friend
- Emergency: Call 100 (Police), 108 (Ambulance)
- Tourist Helpline: 1363
- Train PNR: SMS PNR <10-digit> to 139
- Flight status: Check airline app
- Hotel: Book through trusted platforms (MakeMyTrip, OYO)""",
            "student_info": """📚 Student Information (Offline):
- Scholarship portal: scholarships.gov.in
- NEET/JEE/UPSC: Check respective NTA websites
- Results: cbseresults.nic.in (CBSE), results.gov.in
- Digital locker: digilocker.gov.in (store certificates)
- SWAYAM: Free online courses (swayam.gov.in)
- NPTEL: IIT courses (nptel.ac.in)
- Book bank: National Digital Library (ndl.iitkgp.ac.in)""",
            "farming_basics": """🌾 Farming Basics (Offline):
- MSP: Check minimum support prices at msp.gov.in
- PM-KISAN: Rs 6,000/yr in 3 installments
- Crop insurance: PMFBY (pmfby.gov.in)
- Mandi prices: enaam.gov.in
- Soil health card: soilhealth.dac.gov.in
- Kisan Call Centre: 1800-180-1551 (toll-free)
- Organic farming: pgstcindia.in""",
            "senior_citizen": """👴 Senior Citizen Info (Offline):
- Elderline: 14567 (toll-free)
- Senior citizen savings: 8.2% interest (post office)
- Ayushman Bharat: Rs 5 lakh cover (pmjay.gov.in)
- Concession: 50% on rail fare (60+ male, 58+ female)
- Property tax: Exemption in many states
- Will registration: Register at sub-registrar office""",
            "women_safety": """👩 Women Safety Tips (Offline):
- Women Helpline: 181 (24x7)
- Police: 100
- SOS button: Most phones have emergency SOS
- Share live location: WhatsApp/Google Maps
- Domestic violence: 181, 1091 (Police)
- Sexual harassment: 181, file FIR
- Workplace: POSH Act — mandatory ICC in companies""",
            "child_safety": """👶 Child Safety Tips (Offline):
- Childline: 1098 (24x7, free)
- POCSO Helpline: 1800-11-0031
- Missing child: Call 100 + 1094 (anti-trafficking)
- Right to Education: Free for ages 6-14
- Child labour: Report to 1098
- Cyber safety: Don't share personal info online""",
            "recycling_tips": """♻️ Recycling & Waste Tips (Offline):
- Wet waste: Compost (food, garden waste)
- Dry waste: Recycle (paper, plastic, metal)
- E-waste: Don't throw in trash — take to collection center
- Battery: Don't throw — hazardous
- Plastic: Avoid single-use. Carry reusable bags
- Segregate waste: Wet + Dry + Hazardous
- Swachh Bharat: sbmapp.swachhbharat.gov.in""",
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
