"""
Tool Registry for Zenix Agent.
Real tool integrations: weather API, SQL, filesystem, calculator.
"""

import os
import re
import math
import json
import ssl
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, Optional
from datetime import datetime
from .speech import INDIAN_LANGUAGES


# Shared SSL context for HTTP requests
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _http_get(url: str, timeout: int = 10, headers: Dict[str, str] = None) -> Optional[dict]:
    """Helper: GET a URL and return parsed JSON, or None on failure."""
    hdrs = {"User-Agent": "Zenix/1.0"}
    if headers:
        hdrs.update(headers)
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


class ToolRegistry:
    """
    Registry of tools available to the Agent.
    Each tool has a name, description, usage, and handler function.
    """

    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.tools = {}
        self._register_tools()
        self._init_sample_db()

    def _register_tools(self):
        self.tools["search"] = {
            "name": "search",
            "description": "Search the knowledge base for information.",
            "usage": "search: <query>",
            "handler": self._handle_search,
        }
        self.tools["weather"] = {
            "name": "weather",
            "description": "Get current weather for a city using Open-Meteo API (free, no key needed).",
            "usage": "weather: <city name>",
            "handler": self._handle_weather,
        }
        self.tools["sql"] = {
            "name": "sql",
            "description": (
                "Execute SQL queries on a sample database. "
                "Tables: employees(id, name, role, city, salary), "
                "orders(id, customer_id, item, amount, date)."
            ),
            "usage": "sql: SELECT * FROM employees WHERE city = 'Mumbai'",
            "handler": self._handle_sql,
        }
        self.tools["calculator"] = {
            "name": "calculator",
            "description": "Evaluate a math expression (supports +, -, *, /, **, sqrt, sin, cos, etc.).",
            "usage": "calculator: 2**10 + sqrt(144)",
            "handler": self._handle_calculator,
        }
        self.tools["file"] = {
            "name": "file",
            "description": "Read file contents from a sandboxed data directory.",
            "usage": "file: read <filename>",
            "handler": self._handle_file,
        }
        self.tools["datetime"] = {
            "name": "datetime",
            "description": "Get current date, time, timezone info, or day of the week.",
            "usage": "datetime: now | datetime: date | datetime: day",
            "handler": self._handle_datetime,
        }
        self.tools["translate"] = {
            "name": "translate",
            "description": (
                "Translate text between languages. Supports all 22 Indian languages + English. "
                "Use language names (e.g., Hindi, Bengali, Tamil, Telugu, Marathi) or ISO codes."
            ),
            "usage": "translate: <text> to <language> | translate: <text> from <lang1> to <lang2>",
            "handler": self._handle_translate,
        }
        self.tools["unit"] = {
            "name": "unit",
            "description": "Convert between units (length, weight, temperature).",
            "usage": "unit: 10 km to miles | unit: 72 fahrenheit to celsius | unit: 5 kg to pounds",
            "handler": self._handle_unit,
        }
        self.tools["currency"] = {
            "name": "currency",
            "description": (
                "Convert between currencies using live exchange rates. "
                "Supports INR, USD, EUR, GBP, JPY, and 30+ currencies."
            ),
            "usage": "currency: 100 usd to inr | currency: 5000 inr to usd | currency: 50 eur to gbp",
            "handler": self._handle_currency,
        }
        self.tools["web_search"] = {
            "name": "web_search",
            "description": (
                "Search the web for current, up-to-date information. "
                "Use when the knowledge base doesn't have the answer or for real-time queries."
            ),
            "usage": "web_search: <search query>",
            "handler": self._handle_web_search,
        }
        self.tools["news"] = {
            "name": "news",
            "description": "Get latest news headlines on any topic.",
            "usage": "news: <topic> | news: today headlines",
            "handler": self._handle_news,
        }
        self.tools["stocks"] = {
            "name": "stocks",
            "description": "Get stock market data for Indian (NSE/BSE) and global stocks.",
            "usage": "stocks: RELIANCE | stocks: TCS | stocks: AAPL",
            "handler": self._handle_stocks,
        }
        self.tools["location"] = {
            "name": "location",
            "description": "Find location details, coordinates, and nearby places.",
            "usage": "location: <place name> | location: find <query> near <place>",
            "handler": self._handle_location,
        }
        self.tools["calendar"] = {
            "name": "calendar",
            "description": "Get Indian festival info, holidays, and cultural calendar events.",
            "usage": "calendar: today | calendar: next festival | calendar: holidays in October",
            "handler": self._handle_calendar,
        }
        self.tools["speech"] = {
            "name": "speech",
            "description": "Text-to-Speech: Convert text to spoken audio. Use for reading out answers, news, or notifications.",
            "usage": "speech: <text> | speech: <text> in Hindi | speech: <text> language=bn",
            "handler": self._handle_speech,
        }
        self.tools["eligibility"] = {
            "name": "eligibility",
            "description": ("Check eligibility for Indian government schemes like PM-Kisan, Ayushman Bharat, "
                "PM Ujjwala, Sukanya Samriddhi, etc. based on user profile."),
            "usage": "eligibility: {income: 200000, occupation: farmer, state: UP, age: 45, gender: male}",
            "handler": self._handle_eligibility,
        }
        self.tools["feedback"] = {
            "name": "feedback",
            "description": "Analyze user feedback (thumbs up/down), generate feedback reports, and track response quality.",
            "usage": "feedback: report | feedback: stats | feedback: thumbs_down list",
            "handler": self._handle_feedback,
        }
        self.tools["preferences"] = {
            "name": "preferences",
            "description": "Manage user preferences: save/load language, persona, location, and interests.",
            "usage": "preferences: save {language: hi, persona: desi, location: Delhi} | preferences: load | preferences: list",
            "handler": self._handle_preferences,
        }
        self.tools["generate_doc"] = {
            "name": "generate_doc",
            "description": ("Generate documents: emails, reports, summaries, memos, form letters, code docs. "
                "Supports Markdown output and PDF export."),
            "usage": "generate_doc: email {subject: Meeting, recipient: Ravi, body: ..., sender: ...} | generate_doc: templates",
            "handler": self._handle_generate_doc,
        }
        self.tools["reason"] = {
            "name": "reason",
            "description": ("Multi-step reasoning for complex queries. Breaks down complex questions into sub-goals, "
                "executes each, and synthesizes a comprehensive answer."),
            "usage": "reason: <complex query that needs multiple steps>",
            "handler": self._handle_reason,
        }
        self.tools["scan"] = {
            "name": "scan",
            "description": ("Scan/OCR a document photo: extract text from Aadhaar, PAN, receipts, bills, marksheets. "
                "Provide an image file path or base64 data."),
            "usage": "scan: /path/to/image.jpg | scan: <base64_data>",
            "handler": self._handle_scan,
        }
        self.tools["profile"] = {
            "name": "profile",
            "description": "Manage user profiles for family sharing. Create, switch, list, and update profiles.",
            "usage": "profile: list | profile: create Ram | profile: switch Ram | profile: update {language: hi}",
            "handler": self._handle_profile,
        }
        self.tools["memory"] = {
            "name": "memory",
            "description": ("Remember user facts across sessions. Store names, cities, preferences, corrections. "
                "Auto-detects 'remember' and 'forget' intents from user messages."),
            "usage": "memory: remember {key: value} | memory: recall | memory: recall name | memory: forget name | memory: context",
            "handler": self._handle_memory,
        }
        self.tools["export"] = {
            "name": "export",
            "description": "Export chat history as JSON, Markdown, or PDF.",
            "usage": "export: json | export: markdown | export: pdf",
            "handler": self._handle_export,
        }
        self.tools["branch"] = {
            "name": "branch",
            "description": ("Conversation branching: go back to a previous message and fork a new conversation path. "
                "List branches or create a new one."),
            "usage": "branch: list | branch: fork <message_id> | branch: switch <branch_id>",
            "handler": self._handle_branch,
        }
        self.tools["suggest"] = {
            "name": "suggest",
            "description": "Get proactive follow-up suggestions based on the conversation context.",
            "usage": "suggest: followup | suggest: topics",
            "handler": self._handle_suggest,
        }
        self.tools["offline"] = {
            "name": "offline",
            "description": "Offline mode: get cached responses, queue messages for sync, check offline knowledge.",
            "usage": "offline: knowledge | offline: cache stats | offline: sync queue",
            "handler": self._handle_offline,
        }
        self.tools["pincode"] = {
            "name": "pincode",
            "description": ("Indian pincode lookup: find city, district, state from pincode. "
                "Also validates Aadhaar, PAN, and phone numbers."),
            "usage": "pincode: 110001 | pincode: validate aadhaar 123456789012 | pincode: validate pan ABCDE1234F",
            "handler": self._handle_pincode,
        }
        self.tools["sip"] = {
            "name": "sip",
            "description": ("SIP calculator: calculate mutual fund SIP returns, compare funds, "
                "find required SIP for a financial goal."),
            "usage": "sip: 5000 for 10 years at 12% | sip: compare 5000 for 10 years | sip: goal 5000000 in 10 years at 12%",
            "handler": self._handle_sip,
        }
        self.tools["crop"] = {
            "name": "crop",
            "description": "Crop advisory: seasonal advice, mandi prices, farming guidance for Indian farmers.",
            "usage": "crop: season | crop: price rice | crop: advisory",
            "handler": self._handle_crop,
        }
        self.tools["petrol"] = {
            "name": "petrol",
            "description": "Live petrol/diesel prices for Indian cities. Fetches from mypetrolprice.com.",
            "usage": "petrol: Mumbai | petrol: Delhi | petrol: all",
            "handler": self._handle_petrol,
        }
        self.tools["gold"] = {
            "name": "gold",
            "description": "Live gold and silver prices in India. Fetches from metals.live API.",
            "usage": "gold: today | gold: rate",
            "handler": self._handle_gold,
        }
        self.tools["aqi"] = {
            "name": "aqi",
            "description": "Live Air Quality Index for Indian cities. Fetches from Open-Meteo API.",
            "usage": "aqi: Delhi | aqi: Mumbai | aqi: all",
            "handler": self._handle_aqi,
        }
        self.tools["ifsc"] = {
            "name": "ifsc",
            "description": (
                "IFSC code lookup: find bank name, branch, address, city, state from IFSC code. "
                "Also supports bank name search. Uses Razorpay IFSC API (free, no key)."
            ),
            "usage": "ifsc: SBIN0001234 | ifsc: search State Bank of India Delhi",
            "handler": self._handle_ifsc,
        }
        self.tools["emi"] = {
            "name": "emi",
            "description": (
                "EMI calculator: calculate EMI for home loan, car loan, personal loan. "
                "Also calculates total interest and total payment."
            ),
            "usage": "emi: 5000000 for 20 years at 8.5% | emi: 800000 for 5 years at 9%",
            "handler": self._handle_emi,
        }
        self.tools["tax"] = {
            "name": "tax",
            "description": (
                "Income tax calculator: compare old vs new regime for FY 2025-26. "
                "Enter annual income to see tax under both regimes with deductions."
            ),
            "usage": "tax: 1200000 | tax: income 1500000 with 80c 150000 hra 100000",
            "handler": self._handle_tax,
        }
        self.tools["hospital"] = {
            "name": "hospital",
            "description": (
                "Find nearby hospitals, clinics, blood banks, and pharmacies. "
                "Uses OpenStreetMap Nominatim API for location search."
            ),
            "usage": "hospital: near Delhi | blood bank: Mumbai | pharmacy: Bangalore",
            "handler": self._handle_hospital,
        }
        self.tools["train_status"] = {
            "name": "train_status",
            "description": (
                "Live train running status, PNR status, and seat availability. "
                "Uses RailYatri/IRCTC data via web search."
            ),
            "usage": "train_status: 12951 | train_status: PNR 4521234567 | train_status: Delhi to Mumbai",
            "handler": self._handle_train_status,
        }
        self.tools["epfo"] = {
            "name": "epfo",
            "description": (
                "EPFO/PF guidance: check PF balance, UAN activation, claim status, "
                "transfer process, and pension scheme details."
            ),
            "usage": "epfo: check balance | epfo: uan activate | epfo: claim process | epfo: pension",
            "handler": self._handle_epfo,
        }
        self.tools["telecom"] = {
            "name": "telecom",
            "description": (
                "Telecom recharge plan comparison for Jio, Airtel, Vi, BSNL. "
                "Compare prepaid plans by validity, data, calls, and price."
            ),
            "usage": "telecom: Jio 399 | telecom: compare 299 | telecom: best 1gb per day | telecom: annual Jio",
            "handler": self._handle_telecom,
        }
        self.tools["stamp_duty"] = {
            "name": "stamp_duty",
            "description": (
                "Stamp duty and property registration cost calculator for Indian states. "
                "Calculate total cost including stamp duty, registration fee, and GST."
            ),
            "usage": "stamp_duty: 5000000 in Maharashtra | stamp_duty: 80 lakh Delhi | stamp_duty: register 1 crore Karnataka",
            "handler": self._handle_stamp_duty,
        }
        self.tools["panchang"] = {
            "name": "panchang",
            "description": (
                "Hindu Panchang: tithi, nakshatra, yoga, karana, muhurat, rashi. "
                "Also provides Islamic Hijri and Sikh Nanakshahi calendar dates."
            ),
            "usage": "panchang: today | panchang: muhurat | panchang: rashi | panchang: 15 august 2026",
            "handler": self._handle_panchang,
        }
        self.tools["training_data"] = {
            "name": "training_data",
            "description": (
                "Training data pipeline: generate training examples from user feedback, "
                "export as JSONL for fine-tuning, show quality report."
            ),
            "usage": "training_data: report | training_data: generate | training_data: export openai | training_data: export jsonl",
            "handler": self._handle_training_data,
        }
        self.tools["abuse"] = {
            "name": "abuse",
            "description": (
                "Abuse prevention stats: check session health, spam detection, "
                "injection attempts, tool rate limits."
            ),
            "usage": "abuse: stats | abuse: session <id> | abuse: cleanup",
            "handler": self._handle_abuse,
        }
        self.tools["medicine"] = {
            "name": "medicine",
            "description": (
                "Medicine interaction checker and drug information. Check if two medicines "
                "can be taken together, side effects, dosage guidance, and alternatives."
            ),
            "usage": "medicine: paracetamol and ibuprofen | medicine: cross check crocin with combiflam | medicine: side effects of metformin",
            "handler": self._handle_medicine,
        }
        self.tools["bank"] = {
            "name": "bank",
            "description": (
                "Banking guidance: how to check balance, mini statement, transfer money, "
                "block card, update KYC for SBI, HDFC, ICICI, PNB, and all major banks."
            ),
            "usage": "bank: check balance SBI | bank: mini statement HDFC | bank: transfer money ICICI | bank: block card",
            "handler": self._handle_bank,
        }
        self.tools["electricity"] = {
            "name": "electricity",
            "description": (
                "Electricity bill payment guidance and discom information for Indian states. "
                "How to pay bill, check consumption, register complaint, apply for new connection."
            ),
            "usage": "electricity: pay bill Delhi | electricity: complaint Mumbai | electricity: new connection Bangalore",
            "handler": self._handle_electricity,
        }
        self.tools["driving_license"] = {
            "name": "driving_license",
            "description": (
                "Driving license application, renewal, and related services. "
                "Step-by-step guide for DL application, test booking, international DL, and more."
            ),
            "usage": "driving_license: apply | driving_license: renew | driving_license: international | driving_license: test booking",
            "handler": self._handle_driving_license,
        }
        self.tools["knowledge"] = {
            "name": "knowledge",
            "description": (
                "Search the Indian Knowledge Base for curated information on Indian constitution, "
                "legal rights, RTI, consumer protection, health, education, labour laws, and environment."
            ),
            "usage": "knowledge: <query> | knowledge: fundamental rights | knowledge: RTI process | knowledge: consumer protection",
            "handler": self._handle_knowledge,
        }
        self.tools["transliterate"] = {
            "name": "transliterate",
            "description": (
                "Transliterate Roman/Hinglish text to any Indian script. "
                "Converts 'namaste' to Devanagari, 'vanakkam' to Tamil, etc."
            ),
            "usage": "transliterate: namaste to devanagari | transliterate: hello to bengali | transliterate: namaskaram to tamil",
            "handler": self._handle_transliterate,
        }

    # ── Sample Database ───────────────────────────────────────────────────────

    def _init_sample_db(self):
        """Initialize a richer in-memory SQLite database for the SQL tool."""
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                role TEXT,
                city TEXT,
                salary REAL
            )
        """)
        employees = [
            ("Priya Sharma", "Software Engineer", "Mumbai", 1200000),
            ("Rahul Verma", "Data Scientist", "Delhi", 1400000),
            ("Ananya Patel", "Product Manager", "Bangalore", 1600000),
            ("Vikram Singh", "DevOps Engineer", "Hyderabad", 1100000),
            ("Neha Gupta", "UX Designer", "Pune", 950000),
            ("Arjun Nair", "Backend Developer", "Chennai", 1050000),
            ("Meera Iyer", "ML Engineer", "Bangalore", 1500000),
            ("Sanjay Kumar", "Frontend Developer", "Mumbai", 1000000),
            ("Kavita Joshi", "Tech Lead", "Delhi", 1800000),
            ("Deepak Reddy", "Security Analyst", "Hyderabad", 1300000),
        ]
        cur.executemany("INSERT INTO employees (name, role, city, salary) VALUES (?, ?, ?, ?)", employees)

        cur.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                item TEXT,
                amount REAL,
                date TEXT
            )
        """)
        orders = [
            (1, "Laptop", 75000.00, "2026-01-15"),
            (2, "Smartphone", 45000.00, "2026-02-10"),
            (3, "Headphones", 3500.00, "2026-03-05"),
            (1, "Keyboard", 4500.00, "2026-04-20"),
            (4, "Monitor", 25000.00, "2026-05-12"),
            (5, "Mouse", 1200.00, "2026-06-01"),
            (2, "Tablet", 35000.00, "2026-07-18"),
            (3, "Webcam", 6000.00, "2026-08-22"),
            (1, "USB Hub", 1500.00, "2026-09-10"),
            (5, "SSD 1TB", 8000.00, "2026-10-05"),
        ]
        cur.executemany("INSERT INTO orders (customer_id, item, amount, date) VALUES (?, ?, ?, ?)", orders)

        self.conn.commit()

    # ── Tool Handlers ─────────────────────────────────────────────────────────

    def _handle_search(self, query: str) -> str:
        if not self.rag_engine:
            return "Error: Search engine not available."
        results = self.rag_engine.search(query, k=3)
        if not results:
            return "No results found in the knowledge base."
        return "\n".join(
            f"[Score: {r.get('cross_score', 0):.2f}] {r['content'][:300]}"
            for r in results
        )

    def _handle_weather(self, args: str) -> str:
        """Get weather from Open-Meteo API (free, no API key needed)."""
        city_name = args.strip()
        if not city_name:
            return "Error: Please provide a city name. Example: weather: Mumbai"

        # Geocoding step — use Open-Meteo geocoding API
        geocode_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(city_name)}&count=1&language=en"
        )

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(geocode_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data.get("results"):
                return f"Could not find weather for '{city_name}'. Please check the city name."

            place = data["results"][0]
            lat = place["latitude"]
            lon = place["longitude"]
            resolved_name = place.get("name", city_name)
            country = place.get("country", "")

            # Fetch weather
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
                f"&timezone=auto"
            )

            req2 = urllib.request.Request(weather_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req2, timeout=10, context=ctx) as resp2:
                weather_data = json.loads(resp2.read().decode("utf-8"))

            current = weather_data.get("current", {})
            temp = current.get("temperature_2m", "N/A")
            humidity = current.get("relative_humidity_2m", "N/A")
            wind = current.get("wind_speed_10m", "N/A")
            code = current.get("weather_code", 0)

            # Weather code → description
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                85: "Slight snow showers", 86: "Heavy snow showers",
                95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
            }
            description = weather_codes.get(code, f"Code {code}")

            return (
                f"Weather in {resolved_name}, {country}:\n"
                f"  🌡️ Temperature: {temp}°C\n"
                f"  💧 Humidity: {humidity}%\n"
                f"  💨 Wind: {wind} km/h\n"
                f"  ☁️ Condition: {description}"
            )

        except urllib.error.URLError as e:
            return f"Weather API error: {e}. Please try again later."
        except Exception as e:
            return f"Error fetching weather: {e}"

    def _handle_sql(self, query: str) -> str:
        """Execute SQL on the in-memory database with safety checks."""
        query = query.strip().rstrip(";")

        # Safety: only allow SELECT queries
        first_word = query.split()[0].upper() if query.split() else ""
        if first_word not in ("SELECT", "SHOW", "DESCRIBE", "PRAGMA"):
            return "Only SELECT queries are allowed for safety. No INSERT/UPDATE/DELETE."

        try:
            cur = self.conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

            if not rows:
                return "Query returned no results."

            # Format as a readable table
            header = " | ".join(columns)
            separator = "-" * len(header)
            lines = [header, separator]
            for row in rows[:20]:  # Limit to 20 rows
                lines.append(" | ".join(str(v) for v in row))

            if len(rows) > 20:
                lines.append(f"... ({len(rows)} total rows, showing first 20)")

            return "\n".join(lines)

        except Exception as e:
            return f"SQL Error: {e}"

    def _handle_calculator(self, args: str) -> str:
        """Evaluate a math expression safely."""
        expr = args.strip()
        if not expr:
            return "Error: Please provide a math expression. Example: calculator: 2**10"

        # Allow only safe math operations
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "log": math.log, "log10": math.log10,
            "pi": math.pi, "e": math.e, "ceil": math.ceil, "floor": math.floor,
            "pow": pow,
        }

        # Security check: only allow digits, operators, parentheses, dots, spaces, letters
        sanitized = re.sub(r'[a-zA-Z_]+', '', expr)
        sanitized = re.sub(r'[^0-9+\-*/().%^ ]', '', sanitized)

        try:
            # Use eval with restricted namespace
            result = eval(expr, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except Exception as e:
            return f"Calculation error: {e}"

    def _handle_file(self, args: str) -> str:
        """Read files from a sandboxed data directory."""
        args = args.strip()
        if args.startswith("read "):
            args = args[5:].strip()

        if not args:
            return "Error: Please provide a filename. Example: file: read report.txt"

        # Sandbox to data/ directory
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        file_path = os.path.join(data_dir, args)

        # Security: prevent path traversal
        real_data_dir = os.path.realpath(data_dir)
        real_file_path = os.path.realpath(file_path)

        if not real_file_path.startswith(real_data_dir):
            return "Error: Access denied. Can only read files from the data directory."

        if not os.path.exists(real_file_path):
            return f"File '{args}' not found in data directory."

        if not os.path.isfile(real_file_path):
            return f"Error: '{args}' is not a file."

        try:
            with open(real_file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(10000)  # Limit to 10KB

            if len(content) >= 10000:
                content += "\n\n... (file truncated at 10KB)"

            return f"Content of {args}:\n{content}"
        except Exception as e:
            return f"Error reading file: {e}"

    def _handle_datetime(self, args: str) -> str:
        """Get current date/time info."""
        args = args.strip().lower()
        now = datetime.now()

        if "date" in args:
            return f"Today's date: {now.strftime('%A, %B %d, %Y')}"
        elif "day" in args:
            return f"Today is {now.strftime('%A')}"
        elif "time" in args or "now" in args or not args:
            return (
                f"Current time: {now.strftime('%I:%M %p')}\n"
                f"Date: {now.strftime('%A, %B %d, %Y')}\n"
                f"Timezone: IST (UTC+5:30)"
            )
        else:
            return (
                f"Current time: {now.strftime('%I:%M %p')}\n"
                f"Date: {now.strftime('%A, %B %d, %Y')}"
            )

    # ── Translation Tool ───────────────────────────────────────────────────────

    # Language name → MyMemory ISO code mapping
    LANGUAGE_CODES = {
        # Indian Languages (22 Scheduled Languages)
        "hindi": "hi", "bengali": "bn", "telugu": "te", "marathi": "mr",
        "tamil": "ta", "gujarati": "gu", "urdu": "ur", "kannada": "kn",
        "odia": "or", "odia (oriya)": "or", "malayalam": "ml", "punjabi": "pa",
        "sanskrit": "sa", "assamese": "as", "maithili": "mai",
        "dogri": "doi", "kashmiri": "ks", "konkani": "kok",
        "sindhi": "sd", "manipuri": "mni", "bodo": "brx",
        "santhali": "sat",
        # Major world languages
        "english": "en", "spanish": "es", "french": "fr",
        "german": "de", "chinese": "zh-CN", "japanese": "ja",
        "korean": "ko", "arabic": "ar", "portuguese": "pt",
        "russian": "ru", "italian": "it", "thai": "th",
        "turkish": "tr", "vietnamese": "vi", "indonesian": "id",
        "malay": "ms", "nepali": "ne", "sinhala": "si",
        "burmese": "my", "khmer": "km", "lao": "lo",
        "tibetan": "bo", "filipino": "tl", "swahili": "sw",
        "dutch": "nl", "polish": "pl", "czech": "cs",
        "greek": "el", "hebrew": "he", "hungarian": "hu",
        "romanian": "ro", "swedish": "sv", "danish": "da",
        "finnish": "fi", "norwegian": "no",
    }

    def _resolve_language(self, name: str) -> Optional[str]:
        """Resolve a language name or code to MyMemory language code."""
        name = name.strip().lower()
        # Direct code match (2-3 letter ISO codes)
        if len(name) <= 3 and name.isalpha():
            return name
        # Named language match
        return self.LANGUAGE_CODES.get(name)

    def _handle_translate(self, args: str) -> str:
        """
        Translate text using MyMemory API (free, no API key).

        Formats:
          translate: <text> to <target_language>
          translate: <text> from <source_lang> to <target_lang>
        """
        if not args.strip():
            return "Error: Please provide text and target language. Example: translate: namaste to English"

        # Parse "from X to Y" format
        source_lang = None
        target_lang = None
        text = args.strip()

        # Try "from ... to ..." format
        from_to_match = re.search(
            r'\bfrom\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)', args, re.IGNORECASE
        )
        if from_to_match:
            source_lang = self._resolve_language(from_to_match.group(1))
            target_lang = self._resolve_language(from_to_match.group(2))
            # Extract text: everything after "to <lang>" and optional colon
            after_match = args[from_to_match.end():].strip()
            text = re.sub(r'^:\s*', '', after_match).strip() if after_match else ''
            # If no text after, check text before "from"
            if not text:
                text = args[:from_to_match.start()].strip()
        else:
            # Try "to <language>" at end
            to_match = re.search(r'\bto\s+([a-zA-Z ]+?)$', args, re.IGNORECASE)
            if to_match:
                target_lang = self._resolve_language(to_match.group(1))
                text = args[:to_match.start()].strip()

        if not target_lang:
            return (
                "Error: Could not determine target language. "
                "Use format: translate: <text> to <language>\n"
                "Supported languages: Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, "
                "Kannada, Malayalam, Punjabi, Odia, Urdu, English, and many more."
            )

        if not text:
            return "Error: No text provided to translate."

        # Build MyMemory API URL (MyMemory requires explicit source language)
        lang_pair = f"{source_lang or 'en'}|{target_lang}"
        encoded_text = urllib.parse.quote(text[:500])  # Limit to 500 chars
        api_url = (
            f"https://api.mymemory.translated.net/get"
            f"?q={encoded_text}&langpair={lang_pair}"
        )

        try:
            # Use permissive SSL context for compatibility across environments
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(api_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("responseStatus") == 200:
                translated = data["responseData"]["translatedText"]
                # MyMemory sometimes returns the original text if it can't translate
                is_same = (
                    not translated
                    or translated.strip().lower() == text.strip().lower()
                    or len(translated.strip()) == 0
                )
                if not is_same:
                    source_label = source_lang or "en"
                    return (
                        f"🌐 Translation ({source_label} → {target_lang}):\n"
                        f"Original: {text}\n"
                        f"Translated: {translated}"
                    )
                else:
                    # Fallback: try auto-detect with 'en' as source
                    return (
                        f"Could not translate to {target_lang}. "
                        f"The text may already be in that language, or it may need "
                        f"the source language specified (use: from <source_lang> to {target_lang})."
                    )
            else:
                return f"Translation API returned status: {data.get('responseStatus', 'unknown')}"

        except urllib.error.URLError as e:
            return f"Translation API error: {e}. Please try again later."
        except Exception as e:
            return f"Translation error: {e}"

    # ── Unit Conversion Tool ──────────────────────────────────────────────────

    # Conversion factors to base units (meter, kg, celsius)
    LENGTH_TO_METER = {
        "mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
        "inch": 0.0254, "inches": 0.0254, "foot": 0.3048, "feet": 0.3048,
        "yard": 0.9144, "yards": 0.9144, "mile": 1609.344, "miles": 1609.344,
        "meter": 1, "meters": 1, "kilometer": 1000, "kilometers": 1000,
        "centimeter": 0.01, "centimeters": 0.01, "millimeter": 0.001, "millimeters": 0.001,
    }
    WEIGHT_TO_KG = {
        "mg": 0.000001, "g": 0.001, "kg": 1, "tonne": 1000, "ton": 1000,
        "gram": 0.001, "grams": 0.001, "kilogram": 1, "kilograms": 1,
        "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592,
        "oz": 0.0283495, "ounce": 0.0283495, "ounces": 0.0283495,
        "quintal": 100,
    }
    VOLUME_TO_LITER = {
        "ml": 0.001, "l": 1, "liter": 1, "liters": 1, "litre": 1, "litres": 1,
        "milliliter": 0.001, "milliliters": 0.001, "gallon": 3.78541, "gallons": 3.78541,
        "cup": 0.236588, "cups": 0.236588,
    }

    def _handle_unit(self, args: str) -> str:
        """Convert between units."""
        if not args.strip():
            return "Error: Please provide a conversion. Example: unit: 10 km to miles"

        # Parse "<number> <from_unit> to <to_unit>"
        match = re.match(
            r'([\d.]+)\s*([a-zA-Z°]+)\s+(?:to|in|into)\s+([a-zA-Z°]+)',
            args.strip(), re.IGNORECASE,
        )
        if not match:
            return (
                "Error: Could not parse conversion. Use format: "
                "<number> <from_unit> to <to_unit>\n"
                "Example: 10 km to miles, 72 fahrenheit to celsius, 5 kg to pounds"
            )

        value = float(match.group(1))
        from_unit = match.group(2).lower()
        to_unit = match.group(3).lower()

        # --- Temperature (special case) ---
        temp_result = self._convert_temperature(value, from_unit, to_unit)
        if temp_result is not None:
            return f"🌡️ {value}°{from_unit.capitalize()} = {temp_result:.2f}°{to_unit.capitalize()}"

        # --- Length ---
        if from_unit in self.LENGTH_TO_METER and to_unit in self.LENGTH_TO_METER:
            meters = value * self.LENGTH_TO_METER[from_unit]
            result = meters / self.LENGTH_TO_METER[to_unit]
            return f"📏 {value} {from_unit} = {result:.4g} {to_unit}"

        # --- Weight ---
        if from_unit in self.WEIGHT_TO_KG and to_unit in self.WEIGHT_TO_KG:
            kg = value * self.WEIGHT_TO_KG[from_unit]
            result = kg / self.WEIGHT_TO_KG[to_unit]
            return f"⚖️ {value} {from_unit} = {result:.4g} {to_unit}"

        # --- Volume ---
        if from_unit in self.VOLUME_TO_LITER and to_unit in self.VOLUME_TO_LITER:
            liters = value * self.VOLUME_TO_LITER[from_unit]
            result = liters / self.VOLUME_TO_LITER[to_unit]
            return f"🧪 {value} {from_unit} = {result:.4g} {to_unit}"

        return (
            f"Error: Unknown unit conversion '{from_unit}' → '{to_unit}'.\n"
            f"Supported: km/miles/m/ft/in, kg/lb/oz/g, ml/l/gallon, °C/°F/K"
        )

    @staticmethod
    def _convert_temperature(value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convert between Celsius, Fahrenheit, and Kelvin."""
        # Normalize to lowercase
        from_u = from_unit.lower().replace("°", "")
        to_u = to_unit.lower().replace("°", "")

        # Map common names
        temp_map = {
            "c": "c", "celsius": "c", "centigrade": "c",
            "f": "f", "fahrenheit": "f",
            "k": "k", "kelvin": "k",
        }
        from_u = temp_map.get(from_u)
        to_u = temp_map.get(to_u)

        if not from_u or not to_u:
            return None

        # Convert to Celsius first
        if from_u == "c":
            celsius = value
        elif from_u == "f":
            celsius = (value - 32) * 5 / 9
        elif from_u == "k":
            celsius = value - 273.15
        else:
            return None

        # Convert from Celsius to target
        if to_u == "c":
            return celsius
        elif to_u == "f":
            return celsius * 9 / 5 + 32
        elif to_u == "k":
            return celsius + 273.15
        return None

    # ── Currency Conversion Tool ──────────────────────────────────────────────

    # Common currency codes and symbols
    CURRENCY_CODES = {
        "inr": "INR", "rs": "INR", "rupee": "INR", "rupees": "INR",
        "usd": "USD", "dollar": "USD", "dollars": "USD", "us dollar": "USD",
        "eur": "EUR", "euro": "EUR", "euros": "EUR",
        "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "british pound": "GBP",
        "jpy": "JPY", "yen": "JPY", "japanese yen": "JPY",
        "cny": "CNY", "yuan": "CNY", "rmb": "CNY",
        "aud": "AUD", "australian dollar": "AUD",
        "cad": "CAD", "canadian dollar": "CAD",
        "sgd": "SGD", "singapore dollar": "SGD",
        "aed": "AED", "dirham": "AED", "dirhams": "AED",
        "sar": "SAR", "riyal": "SAR", "riyals": "SAR",
        "chf": "CHF", "swiss franc": "CHF",
        "krw": "KRW", "won": "KRW",
        "thb": "THB", "baht": "THB",
        "myr": "MYR", "ringgit": "MYR",
        "idr": "IDR", "rupiah": "IDR",
        "php": "PHP", "peso": "PHP", "pesos": "PHP",
        "zar": "ZAR", "rand": "ZAR",
        "brl": "BRL", "real": "BRL", "reais": "BRL",
        "rub": "RUB", "ruble": "RUB", "rouble": "RUB",
        "try": "TRY", "lira": "TRY",
        "nzd": "NZD", "new zealand dollar": "NZD",
        "sek": "SEK", "nok": "NOK", "dkk": "DKK",
        "pln": "PLN", "zloty": "PLN",
        "czk": "CZK", "koruna": "CZK",
    }

    CURRENCY_SYMBOLS = {
        "INR": "₹", "USD": "$", "EUR": "€", "GBP": "£",
        "JPY": "¥", "CNY": "¥", "KRW": "₩", "THB": "฿",
    }

    def _resolve_currency(self, name: str) -> Optional[str]:
        """Resolve a currency name or code to ISO 4217 code."""
        name = name.strip().lower()
        # Direct 3-letter code match
        if len(name) == 3 and name.isalpha():
            return name.upper()
        return self.CURRENCY_CODES.get(name)

    def _handle_currency(self, args: str) -> str:
        """
        Convert between currencies using live exchange rates.
        Uses Frankfurter API (free, no key needed).

        Formats:
          currency: <amount> <from> to <to>
          currency: <amount> <from> in <to>
        """
        if not args.strip():
            return (
                "Error: Please provide amount and currencies. "
                "Example: currency: 100 usd to inr"
        )

        # Parse: <amount> <from_currency> to <to_currency>
        match = re.match(
            r'([\d.,]+)\s+([a-zA-Z ₹$€£¥]+?)\s+(?:to|in|into)\s+([a-zA-Z ₹$€£¥]+?)$',
            args.strip(), re.IGNORECASE,
        )
        if not match:
            return (
                "Error: Could not parse. Use format: "
                "<amount> <from_currency> to <to_currency>\n"
                "Example: 100 usd to inr, 5000 inr to usd, 50 eur to gbp"
            )

        # Parse amount (handle commas)
        amount_str = match.group(1).replace(',', '')
        try:
            amount = float(amount_str)
        except ValueError:
            return f"Error: Invalid amount '{match.group(1)}'"

        from_cur = self._resolve_currency(match.group(2))
        to_cur = self._resolve_currency(match.group(3))

        if not from_cur:
            return (
                f"Error: Unknown currency '{match.group(2)}'. "
                f"Supported: INR, USD, EUR, GBP, JPY, and 30+ currencies."
            )
        if not to_cur:
            return (
                f"Error: Unknown currency '{match.group(3)}'. "
                f"Supported: INR, USD, EUR, GBP, JPY, and 30+ currencies."
            )

        # Fetch live rates from Frankfurter API
        api_url = (
            f"https://api.frankfurter.app/latest"
            f"?amount={amount}&from={from_cur}&to={to_cur}"
        )

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(api_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            rates = data.get("rates", {})
            if to_cur in rates:
                converted = rates[to_cur]
                rate_per_unit = converted / amount if amount else 0
                symbol = self.CURRENCY_SYMBOLS.get(to_cur, "")
                from_sym = self.CURRENCY_SYMBOLS.get(from_cur, "")

                return (
                    f"💱 Currency Conversion:\n"
                    f"  {from_sym}{amount:,.2f} {from_cur} = {symbol}{converted:,.2f} {to_cur}\n"
                    f"  Rate: 1 {from_cur} = {rate_per_unit:,.4f} {to_cur}\n"
                    f"  Source: Frankfurter API (ECB data)"
                )
            else:
                return f"Error: Could not convert {from_cur} → {to_cur}. Check currency codes."

        except urllib.error.URLError as e:
            return f"Currency API error: {e}. Please try again later."
        except Exception as e:
            return f"Currency conversion error: {e}"

    # ── Web Search Tool ───────────────────────────────────────────────────────

    def _handle_web_search(self, query: str) -> str:
        """Search the web using DuckDuckGo (no API key needed)."""
        if not query.strip():
            return "Error: Please provide a search query. Example: web_search: weather in Mumbai"

        try:
            import ssl as _ssl
            from duckduckgo_search import DDGS

            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE

            with DDGS() as ddgs:
                results = list(ddgs.text(query.strip(), max_results=5))

            if not results:
                return f"No search results found for: {query}"

            output_lines = [f"🔍 Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                body = r.get("body", "No description")
                url = r.get("href", "")
                output_lines.append(f"{i}. {title}")
                output_lines.append(f"   {body[:200]}")
                if url:
                    output_lines.append(f"   🔗 {url}")
                output_lines.append("")

            return "\n".join(output_lines)

        except ImportError:
            return "Web search module not installed. Please install: pip install duckduckgo-search"
        except Exception as e:
            return f"Web search error: {e}"

    # ── News Tool ─────────────────────────────────────────────────────────────

    def _handle_news(self, query: str) -> str:
        """Get latest news headlines using DuckDuckGo news search."""
        if not query.strip():
            query = "India today"

        try:
            import ssl as _ssl
            from duckduckgo_search import DDGS

            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE

            with DDGS() as ddgs:
                results = list(ddgs.news(query.strip(), max_results=5))

            if not results:
                return f"No news found for: {query}"

            output_lines = [f"📰 Latest News: {query}\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                body = r.get("body", "")
                source = r.get("source", "")
                date_str = r.get("date", "")
                url = r.get("url", "")
                output_lines.append(f"{i}. {title}")
                if source:
                    output_lines.append(f"   Source: {source}")
                if body:
                    output_lines.append(f"   {body[:150]}")
                if url:
                    output_lines.append(f"   🔗 {url}")
                output_lines.append("")

            return "\n".join(output_lines)

        except ImportError:
            return "News module not installed. Please install: pip install duckduckgo-search"
        except Exception as e:
            return f"News search error: {e}"

    # ── Stocks Tool ────────────────────────────────────────────────────────────

    def _handle_stocks(self, symbol: str) -> str:
        """Get stock data from Yahoo Finance (free, no API key)."""
        if not symbol.strip():
            return "Error: Please provide a stock symbol. Example: stocks: RELIANCE or stocks: AAPL"

        symbol = symbol.strip().upper()

        # Add .NS suffix for NSE stocks if not already present
        yf_symbol = symbol
        if not any(suffix in symbol for suffix in [".NS", ".BO", ".L", ".TO", ".HK"]):
            # Try NSE first, then raw symbol
            yf_symbol = f"{symbol}.NS"

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
                f"?interval=1d&range=5d"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            result = data.get("chart", {}).get("result", [])
            if not result:
                # Try without .NS suffix
                if yf_symbol.endswith(".NS"):
                    yf_symbol = symbol
                    url2 = (
                        f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
                        f"?interval=1d&range=5d"
                    )
                    req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req2, timeout=10, context=ctx) as resp2:
                        data2 = json.loads(resp2.read().decode("utf-8"))
                    result = data2.get("chart", {}).get("result", [])

            if not result:
                return f"Stock symbol '{symbol}' not found. Please check the symbol."

            meta = result[0].get("meta", {})
            indicators = result[0].get("indicators", {})
            timestamps = result[0].get("timestamp", [])

            stock_name = meta.get("shortName", meta.get("symbol", symbol))
            currency = meta.get("currency", "INR")
            current_price = meta.get("regularMarketPrice", 0)
            previous_close = meta.get("previousClose", 0)
            market_state = meta.get("marketState", "UNKNOWN")

            # Get historical close prices
            closes = indicators.get("quote", [{}])[0].get("close", [])
            closes = [c for c in closes if c is not None]

            change = current_price - previous_close if previous_close else 0
            change_pct = (change / previous_close * 100) if previous_close else 0
            direction = "📈" if change >= 0 else "📉"

            lines = [
                f"{direction} {stock_name} ({symbol})",
                f"  💰 Price: {currency} {current_price:,.2f}",
                f"  📊 Change: {change:+,.2f} ({change_pct:+.2f}%)",
                f"  📋 Previous Close: {currency} {previous_close:,.2f}",
                f"  🏛️ Market: {market_state}",
            ]

            if closes:
                lines.append(f"  📈 5-Day High: {currency} {max(closes):,.2f}")
                lines.append(f"  📉 5-Day Low: {currency} {min(closes):,.2f}")

            return "\n".join(lines)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return f"Stock '{symbol}' not found. Try adding .NS (NSE) or .BO (BSE) suffix."
            return f"Stock API error: {e}"
        except Exception as e:
            return f"Stock lookup error: {e}"

    # ── Location Tool ──────────────────────────────────────────────────────────

    def _handle_location(self, query: str) -> str:
        """Find location details using Nominatim (OpenStreetMap) — free, no API key."""
        if not query.strip():
            return "Error: Please provide a location. Example: location: Mumbai"

        try:
            # Geocoding
            encoded_query = urllib.parse.quote(query.strip())
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = (
                f"https://nominatim.openstreetmap.org/search"
                f"?q={encoded_query}&format=json&limit=3&countrycodes=in"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Zenix/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data:
                return f"Location '{query}' not found. Please try a different name."

            lines = [f"📍 Location Results for: {query}\n"]
            for i, place in enumerate(data[:3], 1):
                name = place.get("display_name", "Unknown")
                lat = place.get("lat", "N/A")
                lon = place.get("lon", "N/A")
                place_type = place.get("type", "")
                importance = place.get("importance", 0)

                # Truncate display name for readability
                name_parts = name.split(", ")
                short_name = ", ".join(name_parts[:4])

                lines.append(f"{i}. {short_name}")
                lines.append(f"   📐 Coordinates: {lat}, {lon}")
                if place_type:
                    lines.append(f"   🏷️ Type: {place_type.replace('_', ' ').title()}")
                lines.append("")

            # Add nearby search suggestion
            lines.append("💡 Tip: Use 'location: find <item> near <place>' to search nearby.")

            return "\n".join(lines)

        except Exception as e:
            return f"Location search error: {e}"

    # ── Calendar Tool ──────────────────────────────────────────────────────────

    def _handle_calendar(self, query: str) -> str:
        """Get Indian calendar info — festivals, holidays, cultural events."""
        try:
            from .calendar import IndianCalendar
            cal = IndianCalendar()
            query_lower = query.strip().lower()

            if not query_lower or "today" in query_lower or "aaj" in query_lower:
                return cal.format_calendar_response()

            elif "next festival" in query_lower or "agla tyohaar" in query_lower:
                info = cal.get_today_info()
                uf = info.get("upcoming_festival")
                if uf:
                    return (
                        f"🎉 Agla tyohaar: {uf['name']}\n"
                        f"📅 Date: {uf['date']}\n"
                        f"⏰ Din baad: {uf['days_until']}"
                    )
                return "Koi tyohaar abhi paas nahi aa raha."

            elif "holidays" in query_lower or "holiday" in query_lower or "chutti" in query_lower:
                # Try to extract month
                month_map = {
                    "january": 1, "february": 2, "march": 3, "april": 4,
                    "may": 5, "june": 6, "july": 7, "august": 8,
                    "september": 9, "october": 10, "november": 11, "december": 12,
                    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
                }
                month = None
                for name, num in month_map.items():
                    if name in query_lower:
                        month = num
                        break

                holidays = cal.get_holiday_calendar(month=month)
                if holidays:
                    lines = [f"🏛️ {('Month ' + str(month) if month else 'All')} Holidays 2026:\n"]
                    for h in holidays:
                        lines.append(f"  📅 {h['date']} ({h['day']}) — {h['name']} [{h['type']}]")
                    return "\n".join(lines)
                return f"No holidays found for the specified period."

            elif "check" in query_lower or "is" in query_lower:
                result = cal.check_if_holiday()
                if result["is_holiday"]:
                    events = result["regional_events"] + result["islamic_events"]
                    holiday_name = result["national_holiday"] or ", ".join(events)
                    banks = "🔴 Banks CLOSED" if result["banks_closed"] else "🟢 Banks OPEN"
                    return f"🎉 Aaj holiday hai: {holiday_name}\n{banks}"
                else:
                    return f"📅 Aaj koi holiday nahi hai. Regular working day hai."

            else:
                return cal.format_calendar_response()

        except Exception as e:
            return f"Calendar error: {e}"

    # ── Speech Tool ──────────────────────────────────────────────────────────

    def _handle_speech(self, args: str) -> str:
        """Text-to-Speech: Convert text to spoken audio."""
        if not args.strip():
            return "Error: Please provide text to speak. Example: speech: Namaste, how are you?"

        # Parse language from args: "text language=hi" or "text in Hindi"
        language = "en"
        text = args.strip()

        # Check for "language=XX" pattern
        lang_match = re.search(r'language=(\w+)', args, re.IGNORECASE)
        if lang_match:
            language = lang_match.group(1).lower()
            text = re.sub(r'\s*language=\w+', '', args, flags=re.IGNORECASE).strip()
        else:
            # Check for "in <language>" pattern
            in_match = re.search(r'\bin\s+([a-zA-Z]+)\s*$', args, re.IGNORECASE)
            if in_match:
                lang_name = in_match.group(1).lower()
                # Resolve language name to code
                lang_codes = {
                    "hindi": "hi", "bengali": "bn", "telugu": "te",
                    "marathi": "mr", "tamil": "ta", "gujarati": "gu",
                    "urdu": "ur", "kannada": "kn", "malayalam": "ml",
                    "odia": "or", "punjabi": "pa", "english": "en",
                }
                language = lang_codes.get(lang_name, "en")
                text = args[:in_match.start()].strip()

        if not text:
            return "Error: No text provided to speak."

        try:
            from .speech import speech_service
            result = speech_service.synthesize_speech(text, language=language)

            if result.get("error"):
                return f"Speech error: {result['error']}"

            # Save audio to temp file and return path
            import tempfile
            audio_format = result.get("format", "mp3")
            with tempfile.NamedTemporaryFile(
                suffix=f".{audio_format}", delete=False, dir="/tmp"
            ) as f:
                f.write(result["audio_data"])
                audio_path = f.name

            return (
                f"🔊 Audio generated ({audio_format.upper()})\n"
                f"  📁 File: {audio_path}\n"
                f"  🌐 Language: {INDIAN_LANGUAGES.get(language, {}).get('name', language)}\n"
                f"  ⏱️ Duration: ~{result.get('duration', 0):.1f}s\n"
                f"  📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}"
            )

        except ImportError:
            return "Speech module not installed. Install: pip install gTTS pyttsx3"
        except Exception as e:
            return f"Speech synthesis error: {e}"

    # ── Eligibility Checker ──────────────────────────────────────────────────

    def _handle_eligibility(self, args: str) -> str:
        try:
            from .eligibility import EligibilityChecker
            # Try parsing as JSON
            try:
                profile = json.loads(args)
            except json.JSONDecodeError:
                # Try extracting key: value pairs
                profile = {}
            for part in args.replace(", ", ",").split(","):
                if ":" in part:
                    k, v = part.split(":", 1)
                    profile[k.strip()] = v.strip()

            # Map shorthand fields to expected names
            if "income" in profile and "income_annual" not in profile:
                try:
                    profile["income_annual"] = float(profile.pop("income"))
                except (ValueError, TypeError):
                    pass
            if "occupation" in profile and profile["occupation"].lower() == "farmer" and "land_acres" not in profile:
                profile["land_acres"] = 1.0  # default assumption
            if "age" in profile:
                try:
                    profile["age"] = int(profile["age"])
                except (ValueError, TypeError):
                    pass

            checker = EligibilityChecker()
            results = checker.check_all(profile)

            eligible = results.get("eligible_schemes", [])
            not_eligible = results.get("not_eligible_schemes", [])

            if not eligible and not not_eligible:
                return "No matching schemes found for the given profile."

            lines = [f"**Eligibility Results:**\n"]
            if eligible:
                lines.append(f"\u2705 **ELIGIBLE ({len(eligible)}):**\n")
                for r in eligible:
                    name = r.get("name", "Unknown")
                    lines.append(f"  ✅ **{name}**")
                    reasons = r.get("reasons", [])
                    for reason in reasons:
                        lines.append(f"    - {reason}")
                    if r.get("benefit"):
                        lines.append(f"    💰 Benefit: {r['benefit']}")
                    if r.get("apply_at"):
                        lines.append(f"    🔗 Apply: {r['apply_at']}")
                    lines.append("")

            if not_eligible:
                lines.append(f"\u274c **NOT ELIGIBLE ({len(not_eligible)}):**\n")
                for r in not_eligible:
                    name = r.get("name", "Unknown")
                    reasons = r.get("reasons", [])
                    not_reason = [x for x in reasons if "requires" in x.lower() or "excluded" in x.lower()]
                    reason_text = not_reason[0] if not_reason else reasons[0] if reasons else "Does not meet criteria"
                    lines.append(f"  ❌ **{name}** — {reason_text}")
                    lines.append("")

            return "\n".join(lines)
        except ImportError:
            return "Eligibility module not available."
        except Exception as e:
            return f"Eligibility check error: {e}"

    # ── Feedback Analysis ─────────────────────────────────────────────────────

    def _handle_feedback(self, args: str) -> str:
        try:
            from .feedback import FeedbackAnalyzer
            analyzer = FeedbackAnalyzer()
            action = args.strip().lower()

            if action.startswith("report"):
                return analyzer.generate_report()
            elif action.startswith("stats"):
                return analyzer.get_stats()
            elif action.startswith("thumbs_down") or action.startswith("negative"):
                return analyzer.list_negative_feedback()
            elif action.startswith("suggestions"):
                return analyzer.suggest_improvements()
            else:
                return analyzer.get_stats()
        except ImportError:
            return "Feedback module not available."
        except Exception as e:
            return f"Feedback analysis error: {e}"

    # ── User Preferences ──────────────────────────────────────────────────────

    def _handle_preferences(self, args: str) -> str:
        try:
            from .preferences import user_preferences
            action = args.strip().lower()
            session_id = "default"  # default session

            if action.startswith("save"):
                json_str = args[4:].strip()
                try:
                    prefs = json.loads(json_str)
                except json.JSONDecodeError:
                    prefs = {}
                    for part in json_str.replace(", ", ",").split(","):
                        if ":" in part:
                            k, v = part.split(":", 1)
                            prefs[k.strip()] = v.strip()

                update_kwargs = {}
                if "language" in prefs:
                    update_kwargs["preferred_language"] = prefs["language"]
                if "persona" in prefs:
                    update_kwargs["preferred_persona"] = prefs["persona"]
                if "location" in prefs:
                    update_kwargs["location_city"] = prefs["location"]
                if "interests" in prefs:
                    topics = [t.strip() for t in prefs["interests"].split(",")]
                    update_kwargs["topics_of_interest"] = topics
                if update_kwargs:
                    user_preferences.update(session_id, **update_kwargs)
                return f"\u2705 Preferences saved: {json.dumps(prefs, ensure_ascii=False)}"

            elif action.startswith("load"):
                prefs = user_preferences.get(session_id)
                if prefs:
                    lines = ["**Your Preferences:**\n"]
                    for k, v in prefs.items():
                        lines.append(f"- **{k}**: {v}")
                    return "\n".join(lines)
                return "No preferences saved yet. Use: preferences: save {language: hi, ...}"

            elif action.startswith("list"):
                return """**Available preference keys:**
- language: Preferred language code (hi, en, bn, ta, te, mr, etc.)
- persona: Default persona (desi, sarkari)
- location: City or state for local info
- interests: Topics of interest (comma-separated)"""

            elif action.startswith("stats"):
                return json.dumps(user_preferences.stats(), indent=2)

            else:
                prefs = user_preferences.get(session_id)
                if prefs and prefs.get("preferred_language") != "hi":
                    return f"Current: {json.dumps({k: v for k, v in prefs.items() if v}, ensure_ascii=False)}"
                return "No preferences set. Use: preferences: save {language: hi}"

        except ImportError:
            return "Preferences module not available."
        except Exception as e:
            return f"Preferences error: {e}"

    # ── Document Generation ───────────────────────────────────────────────────

    def _handle_generate_doc(self, args: str) -> str:
        try:
            from .documents import render_template, list_templates, markdown_to_html, generate_pdf

            # Check for template list request
            if args.strip().lower() in ("templates", "list", "help"):
                return list_templates()

            # Try to parse as: <template_name> {json}
            parts = args.split(" ", 1)
            template_name = parts[0].strip().lower()
            vars_str = parts[1].strip() if len(parts) > 1 else "{}"

            # Handle pdf export flag
            export_pdf = False
            if "--pdf" in vars_str:
                export_pdf = True
                vars_str = vars_str.replace("--pdf", "").strip()

            try:
                variables = json.loads(vars_str)
            except json.JSONDecodeError:
                variables = {"body": vars_str}

            # Add date if not provided
            if "date" not in variables:
                from datetime import datetime
                variables["date"] = datetime.now().strftime("%d %B %Y")

            content = render_template(template_name, variables)

            if export_pdf:
                html = markdown_to_html(content, title=variables.get("title", variables.get("subject", "Document")))
                pdf_path = f"/tmp/zenix_doc_{template_name}_{int(datetime.now().timestamp())}.pdf"
                result = generate_pdf(html, pdf_path)
                if result:
                    return f"📄 PDF generated: {result}\n\n{content}"
                return f"⚠️ PDF libraries not available (install weasyprint). Here's the Markdown:\n\n{content}"

            return content

        except ImportError:
            return "Document module not available."
        except Exception as e:
            return f"Document generation error: {e}"

    # ── Multi-Step Reasoning ──────────────────────────────────────────────────

    def _handle_reason(self, args: str) -> str:
        if not args.strip():
            return "Provide a complex query for multi-step reasoning."
        try:
            import asyncio
            from .reasoning import MultiStepReasoner

            # Use the LLM client
            from .llm_client import LLMClient
            llm = LLMClient()

            reasoner = MultiStepReasoner(llm, agent=None)  # agent=None for standalone use

            # Run async in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(asyncio.run, reasoner.execute(args)).result()
                else:
                    result = loop.run_until_complete(reasoner.execute(args))
            except RuntimeError:
                result = asyncio.run(reasoner.execute(args))

            return result.get("final_answer", "Reasoning could not be completed.")

        except ImportError:
            return "Reasoning module not available."
        except Exception as e:
            return f"Reasoning error: {e}"

    # ── Document Scanner / OCR ───────────────────────────────────────────────

    def _handle_scan(self, args: str) -> str:
        try:
            from .multimodal import multimodal
            args = args.strip()

            if not args:
                return "Provide an image path or base64 data to scan.\nUsage: scan: /path/to/image.jpg"

            # Check if it's a file path
            if os.path.exists(args):
                result = multimodal.process_image(args)
            elif len(args) > 100:  # Likely base64
                result = multimodal.process_base64(args)
            else:
                return f"File not found: {args}. Provide a valid image path."

            if result.get("error"):
                return f"Scan error: {result['error']}"

            lines = [f"**Document Scan Result:**\n"]
            lines.append(f"Type: {result.get('type', 'unknown')}")

            if result.get("document_type"):
                lines.append(f"Document: {result['document_type'].upper()}")
            if result.get("raw_text"):
                lines.append(f"\n**Extracted Text:**\n{result['raw_text'][:500]}")
            if result.get("extracted_fields"):
                lines.append(f"\n**Extracted Fields:**")
                for k, v in result["extracted_fields"].items():
                    lines.append(f"  - {k}: {v}")
            if result.get("receipt_data"):
                lines.append(f"\n**Receipt Data:**")
                for k, v in result["receipt_data"].items():
                    lines.append(f"  - {k}: {v}")
            if result.get("message"):
                lines.append(f"\n{result['message']}")

            return "\n".join(lines)
        except ImportError:
            return "Multi-modal module not available."
        except Exception as e:
            return f"Scan error: {e}"

    # ── Multi-User Profiles ───────────────────────────────────────────────────

    def _handle_profile(self, args: str) -> str:
        try:
            from .profiles import profile_manager
            action = args.strip().lower()

            if action.startswith("list"):
                profiles = profile_manager.list_profiles()
                if not profiles:
                    return "No profiles found. Create one with: profile: create <name>"
                lines = ["**User Profiles:**\n"]
                for p in profiles:
                    active = " (Active)" if p["is_primary"] else ""
                    lines.append(f"{p['avatar']} **{p['name']}**{active}")
                    lines.append(f"  Language: {p['language']}, Persona: {p['persona']}")
                    if p.get("city"):
                        lines.append(f"  Location: {p['city']}")
                    lines.append("")
                return "\n".join(lines)

            elif action.startswith("create"):
                name = args[6:].strip()
                if not name:
                    return "Provide a name: profile: create <name>"
                profile = profile_manager.create_profile(name)
                return f"Created profile: {profile['avatar']} {profile['name']} (ID: {profile['profile_id']})"

            elif action.startswith("switch"):
                name_or_id = args[6:].strip()
                profiles = profile_manager.list_profiles()
                for p in profiles:
                    if p["name"].lower() == name_or_id.lower() or p["profile_id"] == name_or_id:
                        profile_manager.switch_profile(p["profile_id"])
                        return f"Switched to: {p['avatar']} {p['name']}"
                return f"Profile not found: {name_or_id}"

            elif action.startswith("update"):
                json_str = args[6:].strip()
                try:
                    prefs = json.loads(json_str)
                except json.JSONDecodeError:
                    prefs = {}
                    for part in json_str.replace(", ", ",").split(","):
                        if ":" in part:
                            k, v = part.split(":", 1)
                            prefs[k.strip()] = v.strip()
                active = profile_manager.get_active_profile()
                profile_manager.update_profile(active["profile_id"], **prefs)
                return f"Updated profile: {active['name']} with {json.dumps(prefs, ensure_ascii=False)}"

            elif action.startswith("delete"):
                name_or_id = args[6:].strip()
                profiles = profile_manager.list_profiles()
                for p in profiles:
                    if (p["name"].lower() == name_or_id.lower() or p["profile_id"] == name_or_id) and not p["is_primary"]:
                        profile_manager.delete_profile(p["profile_id"])
                        return f"Deleted profile: {p['name']}"
                return "Cannot delete primary profile or profile not found."

            else:
                active = profile_manager.get_active_profile()
                return f"Active: {active['avatar']} {active['name']} | Use: profile: list | create | switch | update | delete"

        except ImportError:
            return "Profile module not available."
        except Exception as e:
            return f"Profile error: {e}"

    # ── Conversation Memory ──────────────────────────────────────────────────

    def _handle_memory(self, args: str) -> str:
        try:
            from .memory import conversation_memory
            session_id = "default"  # Could be passed from context
            action = args.strip().lower()

            if action.startswith("remember"):
                # Parse the key:value from args
                json_str = args[8:].strip()
                try:
                    data = json.loads(json_str)
                    key = data.get("key", "")
                    value = data.get("value", "")
                except json.JSONDecodeError:
                    # Try key: value format
                    if ":" in json_str:
                        key, value = json_str.split(":", 1)
                        key, value = key.strip(), value.strip()
                    else:
                        return "Use: memory: remember {key: value} or memory: remember key: value"

                if key and value:
                    conversation_memory.remember(session_id, key, value)
                    return f"✅ Remembered: {key.title()} = {value}"
                return "Provide both key and value to remember."

            elif action.startswith("recall"):
                key = args[6:].strip() or None
                if key:
                    facts = conversation_memory.recall(session_id, key)
                    if facts:
                        f = facts[key]
                        return f"{key.title()}: {f['value']} (stored {f['updated_at'][:10]})"
                    return f"I don't remember anything about '{key}' yet."
                else:
                    facts = conversation_memory.get_all_facts(session_id)
                    if not facts:
                        return "I don't have any memories stored yet. Say 'remember my name is X' to get started."
                    lines = ["**What I remember about you:**\n"]
                    for f in facts:
                        lines.append(f"- {f['key'].title()}: {f['value']}")
                    return "\n".join(lines)

            elif action.startswith("forget"):
                key = args[6:].strip()
                if key == "everything" or key == "all":
                    from .memory import ConversationMemory
                    conn = conversation_memory._get_conn()
                    conn.execute("DELETE FROM memory_facts WHERE session_id = ?", (session_id,))
                    conn.commit()
                    return "✅ Cleared all memories."
                elif key:
                    conversation_memory.forget(session_id, key)
                    return f"✅ Forgot: {key.title()}"
                return "Specify what to forget: memory: forget <key>"

            elif action.startswith("context"):
                ctx = conversation_memory.get_context_string(session_id)
                return ctx if ctx else "No memories to inject into context."

            elif action.startswith("stats"):
                stats = conversation_memory.stats()
                return json.dumps(stats, indent=2)

            else:
                return "Memory commands: remember | recall | forget | context | stats"

        except ImportError:
            return "Memory module not available."
        except Exception as e:
            return f"Memory error: {e}"

    # ── Data Export ───────────────────────────────────────────────────────────

    def _handle_export(self, args: str) -> str:
        try:
            from .branching import branching_store
            fmt = args.strip().lower()
            session_id = "default"

            if fmt.startswith("json") or not fmt:
                data = branching_store.export_session(session_id, format="json")
                path = f"/tmp/zenix_export_{session_id}.json"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                return f"Exported to {path} (JSON, {len(data)} bytes)"

            elif fmt.startswith("markdown") or fmt.startswith("md"):
                data = branching_store.export_session(session_id, format="markdown")
                path = f"/tmp/zenix_export_{session_id}.md"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                return f"Exported to {path} (Markdown, {len(data)} bytes)"

            elif fmt.startswith("pdf"):
                data = branching_store.export_session(session_id, format="markdown")
                try:
                    from .documents import markdown_to_html, generate_pdf
                    html = markdown_to_html(data, title="Zenix Chat History")
                    path = f"/tmp/zenix_export_{session_id}.pdf"
                    result = generate_pdf(html, path)
                    if result:
                        return f"Exported to {result} (PDF)"
                    return "PDF libraries not available. Install weasyprint. Exported as Markdown instead."
                except ImportError:
                    return "PDF export requires weasyprint. Markdown exported."

            return "Usage: export: json | export: markdown | export: pdf"

        except ImportError:
            return "Export module not available."
        except Exception as e:
            return f"Export error: {e}"

    # ── Conversation Branching ────────────────────────────────────────────────

    def _handle_branch(self, args: str) -> str:
        try:
            from .branching import branching_store
            action = args.strip().lower()
            session_id = "default"

            if action.startswith("list"):
                branches = branching_store.get_branches(session_id)
                if not branches:
                    return "No branches yet. Start a conversation first."
                lines = ["**Conversation Branches:**\n"]
                for b in branches:
                    active = " (current)" if b["branch_id"] == "main" else ""
                    lines.append(f"  🌿 **{b['branch_id']}**{active} — {b['msg_count']} messages")
                return "\n".join(lines)

            elif action.startswith("fork"):
                msg_id = action[4:].strip()
                if not msg_id:
                    return "Provide message ID to fork from: branch: fork <message_id>"
                import time
                new_branch = f"branch_{int(time.time())}"
                success = branching_store.fork_from(session_id, msg_id, new_branch)
                if success:
                    return f"Forked new branch: {new_branch} from message {msg_id}"
                return f"Could not fork from message {msg_id}. Check the message ID."

            return "Usage: branch: list | branch: fork <message_id> | branch: switch <branch_id>"

        except ImportError:
            return "Branching module not available."
        except Exception as e:
            return f"Branch error: {e}"

    # ── Proactive Suggestions ─────────────────────────────────────────────────

    def _handle_suggest(self, args: str) -> str:
        try:
            from .suggestions import suggestion_engine
            action = args.strip().lower()

            if action.startswith("followup") or action.startswith("topics"):
                # This would be called with the last message/response context
                suggestions = suggestion_engine.get_followup_questions("", "desi")
                if suggestions:
                    lines = ["**Suggested follow-ups:**\n"]
                    for s in suggestions:
                        lines.append(f"  💡 {s}")
                    return "\n".join(lines)
                return "No suggestions available."

            return "Usage: suggest: followup | suggest: topics"

        except ImportError:
            return "Suggestions module not available."
        except Exception as e:
            return f"Suggestion error: {e}"

    # ── Offline Mode ──────────────────────────────────────────────────────────

    def _handle_offline(self, args: str) -> str:
        try:
            from .offline import offline_cache
            action = args.strip().lower()

            if action.startswith("knowledge") or action.startswith("help"):
                knowledge = offline_cache.get_offline_knowledge()
                lines = ["**Offline Knowledge Base:**\n"]
                for topic, content in knowledge.items():
                    lines.append(f"📌 **{topic.replace('_', ' ').title()}**")
                    lines.append(f"{content[:200]}...\n")
                return "\n".join(lines)

            elif action.startswith("cache"):
                stats = offline_cache.get_cache_stats()
                return (f"**Offline Cache Stats:**\n"
                        f"  📦 Cached responses: {stats['cached_responses']}\n"
                        f"  📤 Pending sync: {stats['pending_sync']}\n"
                        f"  📚 Offline knowledge: {stats['offline_knowledge']}")

            elif action.startswith("sync"):
                pending = offline_cache.get_pending_sync()
                if not pending:
                    return "No messages pending sync."
                lines = [f"**Pending Sync ({len(pending)} messages):**\n"]
                for p in pending[:5]:
                    lines.append(f"  - [{p['created_at'][:16]}] {p['message'][:50]}...")
                return "\n".join(lines)

            return "Usage: offline: knowledge | offline: cache stats | offline: sync queue"

        except ImportError:
            return "Offline module not available."
        except Exception as e:
            return f"Offline error: {e}"

    # ── Pincode / Validation Tool ────────────────────────────────────────────

    def _handle_pincode(self, args: str) -> str:
        try:
            from .pincode import pincode_service
            args = args.strip()

            if args.lower().startswith("validate aadhaar"):
                aadhaar = args.split()[-1]
                result = pincode_service.validate_aadhaar(aadhaar)
                if result.get("valid"):
                    return f"\u2705 Valid Aadhaar\n  Masked: {result['masked']}"
                return f"\u274c Invalid Aadhaar: {result.get('error', 'Unknown error')}"

            elif args.lower().startswith("validate pan"):
                pan = args.split()[-1]
                result = pincode_service.validate_pan(pan)
                if result.get("valid"):
                    return f"\u2705 Valid PAN\n  Type: {result['type']}\n  Masked: {result['masked']}"
                return f"\u274c Invalid PAN: {result.get('error', 'Unknown error')}"

            elif args.lower().startswith("validate phone"):
                phone = args.split()[-1]
                result = pincode_service.validate_phone(phone)
                if result.get("valid"):
                    return f"\u2705 Valid Phone\n  Formatted: {result['formatted']}"
                return f"\u274c Invalid Phone: {result.get('error', 'Unknown error')}"

            elif args.lower().startswith("format"):
                parts = args.split()
                pincode = parts[1] if len(parts) > 1 else ""
                landmark = parts[2] if len(parts) > 2 else ""
                return pincode_service.format_address(pincode, landmark)

            else:
                # Default: pincode lookup
                result = pincode_service.lookup(args)
                if result.get("error"):
                    return result["error"]
                lines = [f"**Pincode {result['pincode']}:**\n"]
                lines.append(f"\ud83d\udccd {result['formatted_address']}")
                lines.append(f"\ud83c\udfe2 District: {result['district']}")
                lines.append(f"\ud83d\udfcdb State: {result['state']}")
                if result.get("post_offices"):
                    lines.append(f"\ud83d\udce7 Post offices ({result['total_post_offices']}): {', '.join(result['post_offices'][:5])}")
                return "\n".join(lines)

        except ImportError:
            return "Pincode module not available."
        except Exception as e:
            return f"Pincode error: {e}"

    # ── SIP Calculator ───────────────────────────────────────────────────────

    def _handle_sip(self, args: str) -> str:
        try:
            from .financial_tools import sip_calculator
            args = args.strip().lower()

            # Parse: sip: 5000 for 10 years at 12%
            import re
            match = re.match(r'(\d+[\d,]*)(?:\s+for)?\s+(\d+)\s+years?(?:\s+at)?\s+(\d+(?:\.\d+)?)%?', args)
            if match:
                amount = float(match.group(1).replace(',', ''))
                years = int(match.group(2))
                rate = float(match.group(3))
                result = sip_calculator.calculate_sip(amount, years, rate)
                return (
                    f"**SIP Calculation:**\n"
                    f"  \ud83d\udcb0 Monthly: Rs {result['monthly_investment']:,.0f}\n"
                    f"  \ud83d\udcc5 Duration: {result['years']} years ({result['years']*12} months)\n"
                    f"  \ud83d\udcc8 Expected Return: {result['expected_return']}%\n"
                    f"  \n"
                    f"  \u2705 **Total Invested:** Rs {result['total_invested']:,.0f}\n"
                    f"  \ud83d\udcb3 **Maturity Value:** Rs {result['maturity_value']:,.0f}\n"
                    f"  \ud83d\udcc9 **Wealth Gained:** Rs {result['wealth_gained']:,.0f} ({result['return_percentage']}%)"
                )

            # Parse: sip: compare 5000 for 10 years
            compare_match = re.match(r'compare\s+(\d+[\d,]*)(?:\s+for)?\s+(\d+)', args)
            if compare_match:
                amount = float(compare_match.group(1).replace(',', ''))
                years = int(compare_match.group(2))
                results = sip_calculator.compare_funds(amount, years)
                lines = [f"**SIP Comparison: Rs {amount:,.0f}/month for {years} years:**\n"]
                lines.append(f"{'Fund':<25} {'Invested':>12} {'Maturity':>14} {'Returns':>10}")
                lines.append("-" * 65)
                for r in results:
                    lines.append(f"{r['fund']:<25} Rs {r['total_invested']:>10,.0f} Rs {r['maturity_value']:>12,.0f} {r['return_percentage']:>8}%")
                return "\n".join(lines)

            # Parse: sip: goal 5000000 in 10 years at 12%
            goal_match = re.match(r'goal\s+(\d+[\d,]*)(?:\s+in)?\s+(\d+)\s+years?(?:\s+at)?\s+(\d+(?:\.\d+)?)%?', args)
            if goal_match:
                target = float(goal_match.group(1).replace(',', ''))
                years = int(goal_match.group(2))
                rate = float(goal_match.group(3))
                required = sip_calculator.required_sip(target, years, rate)
                return (
                    f"**Goal: Rs {target:,.0f} in {years} years @ {rate}%**\n"
                    f"  \ud83c\udfaf Required Monthly SIP: **Rs {required:,.0f}**\n"
                    f"  \ud83d\udcb0 Total Investment: Rs {required * years * 12:,.0f}\n"
                    f"  \ud83d\udcc9 Wealth Gain: Rs {target - required * years * 12:,.0f}"
                )

            return "Usage: sip: 5000 for 10 years at 12% | sip: compare 5000 for 10 years | sip: goal 5000000 in 10 years at 12%"

        except ImportError:
            return "Financial tools not available."
        except Exception as e:
            return f"SIP error: {e}"

    # ── Crop Advisory ─────────────────────────────────────────────────────────

    def _handle_crop(self, args: str) -> str:
        try:
            from .financial_tools import crop_advisory
            args = args.strip().lower()

            if args.startswith("price") or args.startswith("msp"):
                crop = args.replace("price", "").replace("msp", "").strip()
                return crop_advisory.get_mandi_prices(crop)

            elif args.startswith("season") or args.startswith("advisory") or not args:
                from datetime import datetime
                month = datetime.now().month
                result = crop_advisory.get_season_advisory(month)
                lines = [f"**Crop Advisory ({result['current_season']} Season):**\n"]
                lines.append(f"\ud83d\udcc5 Period: {result['months']}")
                lines.append(f"\ud83c\udfe0 Sowing: {result['sowing_time']}")
                lines.append(f"\ud83e\uddea Harvesting: {result['harvesting_time']}")
                lines.append(f"\ud83c\udf3e Main Crops: {', '.join(result['crops'])}")
                lines.append(f"\n\ud83d\udca1 **Advice:** {result['advice']}")
                return "\n".join(lines)

            return "Usage: crop: season | crop: price rice | crop: advisory"

        except ImportError:
            return "Crop advisory not available."
        except Exception as e:
            return f"Crop error: {e}"

    # ── Enhanced Weather (7-day forecast) ─────────────────────────────────────

    def _handle_weather_enhanced(self, args: str) -> str:
        """Enhanced weather with 7-day forecast and crop advisory."""
        city_name = args.strip()
        if not city_name:
            return "Error: Please provide a city name. Example: weather: Mumbai"

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # Geocode
            geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city_name)}&count=1&language=en"
            req = urllib.request.Request(geocode_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data.get("results"):
                return f"Could not find weather for '{city_name}'."

            place = data["results"][0]
            lat, lon = place["latitude"], place["longitude"]
            resolved = place.get("name", city_name)

            # 7-day forecast
            forecast_url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
                f"&timezone=auto&forecast_days=7"
            )
            req2 = urllib.request.Request(forecast_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req2, timeout=10, context=ctx) as resp2:
                wdata = json.loads(resp2.read().decode("utf-8"))

            current = wdata.get("current", {})
            daily = wdata.get("daily", {})

            weather_codes = {
                0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Snow", 73: "Moderate snow", 75: "Heavy snow",
                80: "Rain showers", 81: "Moderate showers", 82: "Violent showers",
                95: "Thunderstorm", 96: "Thunderstorm + hail",
            }

            desc = weather_codes.get(current.get("weather_code", 0), "Unknown")
            lines = [
                f"**Weather in {resolved}:**\n",
                f"\ud83c\udf21\ufe0f **Now:** {current.get('temperature_2m', '?')}\u00b0C | {desc}",
                f"\ud83d\udca7 Humidity: {current.get('relative_humidity_2m', '?')}% | \ud83d\udca8 Wind: {current.get('wind_speed_10m', '?')} km/h",
                f"\n**7-Day Forecast:**",
            ]

            dates = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])
            codes = daily.get("weather_code", [])

            for i in range(min(7, len(dates))):
                day_desc = weather_codes.get(codes[i] if i < len(codes) else 0, "?")
                rain = precip[i] if i < len(precip) else 0
                rain_str = f" | \u2614 {rain}mm" if rain > 0 else ""
                lines.append(f"  {dates[i]}: {mins[i]}-{maxs[i]}\u00b0C | {day_desc}{rain_str}")

            return "\n".join(lines)

        except Exception as e:
            return f"Weather error: {e}"

    # ── Medicine Interaction Checker ────────────────────────────────────────

    def _handle_medicine(self, args: str) -> str:
        """Check medicine interactions, side effects, and dosage guidance."""
        args = args.strip()
        if not args:
            return (
                "**Medicine Interaction Checker:**\n\n"
                "Usage:\n"
                "  medicine: paracetamol and ibuprofen — Check if safe together\n"
                "  medicine: cross check crocin with combiflam — Interaction check\n"
                "  medicine: side effects of metformin — Side effects info\n"
                "  medicine: dosage of amoxicillin — Dosage guidance\n"
                "  medicine: alternatives for aspirin — Alternative medicines\n\n"
                "⚠️ *This is for informational purposes only. Always consult a doctor.*"
            )

        args_lower = args.lower()

        # ── Drug Database ───────────────────────────────────────────────────
        # Common Indian medicines with interaction data
        DRUGS = {
            # Pain / Fever
            "paracetamol": {
                "generic": "Acetaminophen", "category": "Analgesic/Antipyretic",
                "uses": "Fever, mild-moderate pain, headache, body ache",
                "dosage": "500mg-1g every 4-6 hours (max 4g/day)",
                "side_effects": "Nausea, liver damage (overdose), skin rash (rare)",
                "interacts_with": ["warfarin", "isoniazid", "alcohol"],
                "warnings": "Avoid alcohol. Max 4g/day. Liver disease patients: consult doctor.",
                "brands": ["Crocin", "Dolo", "Calpol", "Pyrimon"],
            },
            "ibuprofen": {
                "generic": "Ibuprofen", "category": "NSAID",
                "uses": "Pain, inflammation, fever, menstrual cramps, arthritis",
                "dosage": "200-400mg every 4-6 hours (max 1200mg/day OTC)",
                "side_effects": "Stomach upset, gastric bleeding, kidney issues (long term)",
                "interacts_with": ["aspirin", "blood thinners", "lithium", "methotrexate", "ace inhibitors"],
                "warnings": "Take with food. Avoid if gastric ulcers. Not for kidney disease.",
                "brands": ["Brufen", "Ibugesic", "Combiflam (with paracetamol)", "Mefnac"],
            },
            "aspirin": {
                "generic": "Acetylsalicylic Acid", "category": "NSAID/Antiplatelet",
                "uses": "Pain, fever, heart attack prevention, blood clot prevention",
                "dosage": "75-325mg daily (cardiac) or 325-650mg every 4-6 hrs (pain)",
                "side_effects": "Gastric bleeding, tinnitus, Reye's syndrome (children)",
                "interacts_with": ["warfarin", "ibuprofen", "methotrexate", "blood thinners"],
                "warnings": "NEVER give to children under 16 (Reye's syndrome). Avoid before surgery.",
                "brands": ["Ecospirin", "Loprin", "Delisprin"],
            },
            "combiflam": {
                "generic": "Ibuprofen + Paracetamol", "category": "Combination NSAID",
                "uses": "Pain, fever, inflammation (combination therapy)",
                "dosage": "1 tablet every 8 hours after food (max 3/day)",
                "side_effects": "Stomach upset, nausea, dizziness",
                "interacts_with": ["blood thinners", "ace inhibitors", "lithium"],
                "warnings": "Do NOT take with other ibuprofen or paracetamol. Take after food.",
                "brands": ["Combiflam", "Flexon", "Ibugesic Plus"],
            },
            "crocin": {
                "generic": "Paracetamol", "category": "Analgesic/Antipyretic",
                "uses": "Fever, pain (same as paracetamol)",
                "dosage": "500mg-1g every 4-6 hours",
                "side_effects": "Same as paracetamol",
                "interacts_with": ["warfarin", "isoniazid", "alcohol"],
                "warnings": "Same as paracetamol. Common brand in India.",
                "brands": ["Crocin", "Crocin Advance", "Crocin Pain Relief"],
            },
            # Antibiotics
            "amoxicillin": {
                "generic": "Amoxicillin", "category": "Antibiotic (Penicillin)",
                "uses": "Bacterial infections: throat, ear, UTI, pneumonia",
                "dosage": "250-500mg every 8 hours or 500mg every 12 hours",
                "side_effects": "Diarrhea, nausea, skin rash, allergic reactions",
                "interacts_with": ["methotrexate", "warfarin", "oral contraceptives"],
                "warnings": "Complete full course. Do NOT use for viral infections. Allergy check: penicillin allergy.",
                "brands": ["Amoxil", "Mox", "Astomox", "Wymox"],
            },
            "azithromycin": {
                "generic": "Azithromycin", "category": "Antibiotic (Macrolide)",
                "uses": "Respiratory infections, STIs, skin infections",
                "dosage": "500mg day 1, then 250mg days 2-5",
                "side_effects": "Diarrhea, nausea, QT prolongation (heart rhythm)",
                "interacts_with": ["antacids", "warfarin", "statins"],
                "warnings": "Take 1 hour before or 2 hours after food. Heart rhythm issues: consult doctor.",
                "brands": ["Azee", "Azithral", "Zifi", "Azax"],
            },
            # Diabetes
            "metformin": {
                "generic": "Metformin Hydrochloride", "category": "Antidiabetic (Biguanide)",
                "uses": "Type 2 diabetes, PCOS, prediabetes",
                "dosage": "500mg twice daily with meals (max 2550mg/day)",
                "side_effects": "Nausea, diarrhea, metallic taste, B12 deficiency (long term)",
                "interacts_with": ["alcohol", "contrast dye (CT scan)", "diuretics"],
                "warnings": "Stop 48 hours before CT scan with contrast. Take with food. Monitor B12 levels.",
                "brands": ["Glycomet", "Metformin", "Obimet", "Glyciphage"],
            },
            # Blood Pressure
            "amlodipine": {
                "generic": "Amlodipine Besylate", "category": "Calcium Channel Blocker",
                "uses": "High blood pressure, angina (chest pain)",
                "dosage": "5-10mg once daily",
                "side_effects": "Ankle swelling, dizziness, flushing, headache",
                "interacts_with": ["simvastatin (high dose)", "cyclosporine"],
                "warnings": "Do not stop suddenly. Swelling usually reduces over time.",
                "brands": ["Amlodac", "Amlokind", "Stamlo", "Amtas"],
            },
            "atenolol": {
                "generic": "Atenolol", "category": "Beta Blocker",
                "uses": "High blood pressure, angina, anxiety, migraine prevention",
                "dosage": "25-100mg once daily",
                "side_effects": "Fatigue, cold hands/feet, slow heartbeat, dizziness",
                "interacts_with": ["insulin", "other BP medicines", "calcium channel blockers"],
                "warnings": "Do not stop suddenly (rebound hypertension). Monitor heart rate.",
                "brands": ["Aten", "Atcardil", "Tenolol", "Amten"],
            },
            # Cholesterol
            "atorvastatin": {
                "generic": "Atorvastatin Calcium", "category": "Statin",
                "uses": "High cholesterol, heart disease prevention",
                "dosage": "10-80mg once daily (usually at night)",
                "side_effects": "Muscle pain, liver enzyme elevation, digestive issues",
                "interacts_with": ["grapefruit juice", "fibrates", "niacin", "cyclosporine"],
                "warnings": "Report unexplained muscle pain immediately. Avoid grapefruit. Regular liver tests.",
                "brands": ["Atorva", "Lipitor", "Tgvator", "Stator"],
            },
            # Acid / Gastric
            "pantoprazole": {
                "generic": "Pantoprazole", "category": "Proton Pump Inhibitor",
                "uses": "Acid reflux, GERD, stomach ulcers, acidity",
                "dosage": "40mg once daily before breakfast (2-4 weeks)",
                "side_effects": "Headache, nausea, long-term: B12 deficiency, bone fractures",
                "interacts_with": ["methotrexate", "clopidogrel", "iron supplements"],
                "warnings": "Take 30 min before food. Not for long-term use without doctor advice.",
                "brands": ["Pantocid", "Pan", "Pantodac", "Ulgel"],
            },
            # Allergy
            "cetirizine": {
                "generic": "Cetirizine Hydrochloride", "category": "Antihistamine",
                "uses": "Allergies, sneezing, runny nose, urticaria, itching",
                "dosage": "10mg once daily",
                "side_effects": "Drowsiness, dry mouth, headache",
                "interacts_with": ["alcohol", "sedatives", "other antihistamines"],
                "warnings": "May cause drowsiness. Avoid driving. Do not combine with alcohol.",
                "brands": ["Cetzine", "Alerid", "Cetcip", "OKAM"],
            },
            # Vitamins
            "vitamin_d3": {
                "generic": "Cholecalciferol", "category": "Vitamin Supplement",
                "uses": "Vitamin D deficiency, bone health, immunity",
                "dosage": "60,000 IU weekly (deficiency) or 1000 IU daily (maintenance)",
                "side_effects": "Nausea, constipation (overdose: hypercalcemia)",
                "interacts_with": ["thiazide diuretics", "digitalis"],
                "warnings": "Take with fatty food for absorption. Get levels tested (25-OH Vitamin D).",
                "brands": ["D-Rise", "Tata 1mg Vitamin D3", "HealthOK"],
            },
            # Blood thinners
            "warfarin": {
                "generic": "Warfarin Sodium", "category": "Anticoagulant",
                "uses": "Blood clot prevention, atrial fibrillation, DVT",
                "dosage": "Individualized (INR monitoring required)",
                "side_effects": "Bleeding, bruising, hair loss",
                "interacts_with": ["aspirin", "ibuprofen", "paracetamol (high dose)", "vitamin K foods", "many antibiotics"],
                "warnings": "DANGEROUS interactions. Regular INR testing mandatory. Avoid green leafy vegetables fluctuation.",
                "brands": ["Warcobin", "Calan", "Wfarin"],
            },
        }

        # ── Parse query ─────────────────────────────────────────────────────
        found_drugs = []
        query_lower = args_lower

        # Find which drugs are mentioned
        for drug_name in DRUGS:
            if drug_name in query_lower:
                found_drugs.append(drug_name)
            else:
                # Check brand names
                for brand in DRUGS[drug_name]["brands"]:
                    if brand.lower() in query_lower:
                        if drug_name not in found_drugs:
                            found_drugs.append(drug_name)

        # Check for interaction keywords
        is_cross_check = any(w in query_lower for w in ["cross", "together", "and", "with", "safe", "interaction"])
        is_side_effects = any(w in query_lower for w in ["side effect", "side effect", "reaction"])
        is_dosage = any(w in query_lower for w in ["dosage", "dose", "how much", "kitna", "how to take"])
        is_alternatives = any(w in query_lower for w in ["alternative", "instead", "other", "bekaar", "substitute"])

        if not found_drugs:
            # Try fuzzy match
            words = query_lower.split()
            for word in words:
                if len(word) > 3:
                    for drug_name in DRUGS:
                        if word in drug_name or drug_name in word:
                            if drug_name not in found_drugs:
                                found_drugs.append(drug_name)

        if not found_drugs:
            return (
                f"Could not identify medicines in: '{args}'\n"
                f"Try mentioning brand names (Crocin, Combiflam, Dolo) or generic names (paracetamol, ibuprofen).\n"
                f"Available drugs: {', '.join(sorted(DRUGS.keys()))}"
            )

        # ── Generate response ───────────────────────────────────────────────
        lines = []

        # Show drug info for each found drug
        for drug in found_drugs:
            info = DRUGS[drug]
            lines.append(f"**{drug.title()}** ({info['generic']})")
            lines.append(f"  Category: {info['category']}")
            lines.append(f"  Uses: {info['uses']}")
            lines.append(f"  Dosage: {info['dosage']}")
            lines.append(f"  Brands: {', '.join(info['brands'])}")
            lines.append("")

        # Side effects
        if is_side_effects or len(found_drugs) == 1:
            for drug in found_drugs:
                info = DRUGS[drug]
                lines.append(f"**{drug.title()} — Side Effects:**")
                lines.append(f"  {info['side_effects']}")
                lines.append(f"  ⚠️ {info['warnings']}")
                lines.append("")

        # Dosage
        if is_dosage:
            for drug in found_drugs:
                info = DRUGS[drug]
                lines.append(f"**{drug.title()} — Dosage:**")
                lines.append(f"  {info['dosage']}")
                lines.append(f"  ⚠️ {info['warnings']}")
                lines.append("")

        # Alternatives
        if is_alternatives:
            for drug in found_drugs:
                info = DRUGS[drug]
                category = info["category"]
                alts = [d for d, v in DRUGS.items() if v["category"] == category and d != drug]
                if alts:
                    lines.append(f"**Alternatives for {drug.title()} ({category}):**")
                    for alt in alts[:3]:
                        alt_info = DRUGS[alt]
                        lines.append(f"  - {alt.title()} ({alt_info['generic']}): {alt_info['uses'][:60]}")
                    lines.append("")

        # Interaction check
        if is_cross_check and len(found_drugs) >= 2:
            d1, d2 = found_drugs[0], found_drugs[1]
            info1, info2 = DRUGS[d1], DRUGS[d2]

            lines.append(f"**Interaction Check: {d1.title()} + {d2.title()}**\n")

            # Check if d2 is in d1's interaction list or vice versa
            interacts = (
                d2 in info1["interacts_with"] or
                d1 in info2["interacts_with"] or
                any(d2 in iw for iw in info1["interacts_with"]) or
                any(d1 in iw for iw in info2["interacts_with"])
            )

            if interacts:
                lines.append(f"  🔴 **INTERACTION DETECTED — Use with caution!**")
                lines.append(f"  {d1.title()} and {d2.title()} may interact.")
                # Specific interaction warnings
                dangerous_pairs = [
                    ("aspirin", "ibuprofen"), ("aspirin", "warfarin"),
                    ("ibuprofen", "warfarin"), ("paracetamol", "warfarin"),
                ]
                pair = tuple(sorted([d1, d2]))
                if pair in [("aspirin", "ibuprofen"), ("aspirin", "paracetamol"), ("ibuprofen", "paracetamol")]:
                    lines.append(f"  Two painkillers together increase risk of stomach bleeding.")
                elif "warfarin" in [d1, d2]:
                    lines.append(f"  {d1.title() if d2 == 'warfarin' else d2.title()} increases bleeding risk with Warfarin.")
                lines.append(f"  💡 Space doses 2-4 hours apart, or consult your doctor.")
            else:
                lines.append(f"  ✅ **No known significant interaction between {d1.title()} and {d2.title()}.**")
                lines.append(f"  Generally safe to take together, but always follow dosage guidelines.")

            # Also check common interactions for each
            for drug in found_drugs:
                info = DRUGS[drug]
                other_drugs_in_list = [d for d in found_drugs if d != drug]
                for other in other_drugs_in_list:
                    for iw in info["interacts_with"]:
                        if other in iw:
                            lines.append(f"  ⚠️ Note: {drug.title()} also interacts with {iw}")

            lines.append("")

        # General warnings
        lines.append("---")
        lines.append("⚠️ **Disclaimer:** This is for informational purposes only.")
        lines.append("Always consult a qualified doctor or pharmacist before taking any medicine.")
        lines.append("In emergency, call **108** (Ambulance) or visit nearest hospital.")

        return "\n".join(lines)

    # ── Banking Guidance ────────────────────────────────────────────────────

    def _handle_bank(self, args: str) -> str:
        """Provide banking guidance for major Indian banks."""
        args = args.strip().lower()
        if not args:
            return (
                "**Banking Services:**\n\n"
                "Usage:\n"
                "  bank: check balance SBI — How to check SBI balance\n"
                "  bank: mini statement HDFC — How to get mini statement\n"
                "  bank: transfer money ICICI — Money transfer guide\n"
                "  bank: block card PNB — Block lost/stolen card\n"
                "  bank: update KYC Axis — KYC update process\n\n"
                "Supported: SBI, HDFC, ICICI, PNB, Bank of Baroda, Canara, Union Bank, Axis, Kotak"
            )

        # Detect bank
        bank = None
        bank_aliases = {
            "sbi": "SBI", "state bank": "SBI", "state bank of india": "SBI",
            "hdfc": "HDFC", "hdfc bank": "HDFC",
            "icici": "ICICI", "icici bank": "ICICI",
            "pnb": "PNB", "punjab national": "PNB", "punjab national bank": "PNB",
            "bob": "BOB", "bank of baroda": "BOB", "baroda": "BOB",
            "canara": "Canara", "canara bank": "Canara",
            "union": "Union Bank", "union bank": "Union Bank",
            "axis": "Axis", "axis bank": "Axis",
            "kotak": "Kotak", "kotak mahindra": "Kotak",
            "idbi": "IDBI", "idbi bank": "IDBI",
            "indian bank": "Indian Bank",
            "central bank": "Central Bank",
        }
        for alias, name in bank_aliases.items():
            if alias in args:
                bank = name
                break

        # Detect action
        is_balance = any(w in args for w in ["balance", "check balance", "kitna paisa", "balance check"])
        is_mini = any(w in args for w in ["mini statement", "mini stmt", "last transactions", "recent transactions"])
        is_transfer = any(w in args for w in ["transfer", "send money", "neft", "rtgs", "imps", "upi transfer"])
        is_block = any(w in args for w in ["block", "lost card", "stolen card", "card band"])
        is_kyc = any(w in args for w in ["kyc", "update kyc", "ekyc", "aadhaar link"])
        is_statement = any(w in args for w in ["statement", "account statement", "passbook"])

        if not bank:
            bank = "SBI"  # default

        # ── Balance Check ────────────────────────────────────────────────────
        if is_balance:
            balance_guides = {
                "SBI": (
                    f"**SBI — Check Account Balance:**\n\n"
                    f"📱 **Method 1: Missed Call**\n"
                    f"  Call **09223766666** from registered mobile\n"
                    f"  Balance sent via SMS instantly\n\n"
                    f"📱 **Method 2: SMS**\n"
                    f"  Send **BAL** to **09223766666**\n"
                    f"  Format: BAL<space>Account Number\n\n"
                    f"📱 **Method 3: YONO App**\n"
                    f"  Open YONO → Login → View Balance\n"
                    f"  Download: yono.sbi.co.in\n\n"
                    f"📱 **Method 4: Internet Banking**\n"
                    f"  Login: onlinesbi.com → Account Summary\n\n"
                    f"📱 **Method 5: USSD**\n"
                    f"  Dial *99# → Choose SBI → Check Balance\n\n"
                    f"📞 **Customer Care:** 1800-11-2211 (toll-free)"
                ),
                "HDFC": (
                    f"**HDFC — Check Account Balance:**\n\n"
                    f"📱 **Method 1: Missed Call**\n"
                    f"  Call **09223920002** from registered mobile\n\n"
                    f"📱 **Method 2: SMS**\n"
                    f"  Send **BAL** to **5676712**\n\n"
                    f"📱 **Method 3: HDFC Mobile App**\n"
                    f"  Open app → Login → View Balance\n\n"
                    f"📱 **Method 4: NetBanking**\n"
                    f"  Login: netbanking.hdfcbank.com\n\n"
                    f"📱 **Method 5: WhatsApp Banking**\n"
                    f"  Send 'Hi' to **7065970659**\n\n"
                    f"📞 **Customer Care:** 1800-266-4332 (toll-free)"
                ),
                "ICICI": (
                    f"**ICICI — Check Account Balance:**\n\n"
                    f"📱 **Method 1: Missed Call**\n"
                    f"  Call **09222488888** from registered mobile\n\n"
                    f"📱 **Method 2: SMS**\n"
                    f"  Send **IBAL** to **09222488888**\n\n"
                    f"📱 **Method 3: iMobile App**\n"
                    f"  Open iMobile → Login → View Balance\n\n"
                    f"📱 **Method 4: NetBanking**\n"
                    f"  Login: icicibank.com\n\n"
                    f"📱 **Method 5: WhatsApp Banking**\n"
                    f"  Send 'Hi' to **08643990000**\n\n"
                    f"📞 **Customer Care:** 1800-103-8181 (toll-free)"
                ),
                "PNB": (
                    f"**PNB — Check Account Balance:**\n\n"
                    f"📱 **Method 1: Missed Call**\n"
                    f"  Call **1800-180-2223** (toll-free)\n\n"
                    f"📱 **Method 2: SMS**\n"
                    f"  Send **BAL<space>Account Number** to **9264092640**\n\n"
                    f"📱 **Method 3: PNB ONE App**\n"
                    f"  Open PNB ONE → Login → View Balance\n\n"
                    f"📱 **Method 4: NetBanking**\n"
                    f"  Login: netpnb.com\n\n"
                    f"📞 **Customer Care:** 1800-180-2223 (toll-free)"
                ),
            }

            # Generic guide for other banks
            generic_guide = (
                f"**{bank} — Check Account Balance:**\n\n"
                f"📱 **Method 1: Missed Call**\n"
                f"  Check {bank} website for missed call number\n"
                f"  Usually from registered mobile\n\n"
                f"📱 **Method 2: SMS Banking**\n"
                f"  Send BAL to the bank's SMS number\n"
                f"  Register for SMS banking first\n\n"
                f"📱 **Method 3: Mobile App**\n"
                f"  Download {bank} official app from Play Store / App Store\n"
                f"  Login with credentials → View Balance\n\n"
                f"📱 **Method 4: NetBanking**\n"
                f"  Visit {bank} official website → Login\n\n"
                f"📱 **Method 5: ATM**\n"
                    f"  Insert card → Enter PIN → Check Balance\n\n"
                f"📱 **Method 6: USSD**\n"
                    f"  Dial *99# → Follow prompts\n\n"
                f"📞 Call {bank} customer care for assistance"
            )

            return balance_guides.get(bank, generic_guide)

        # ── Mini Statement ───────────────────────────────────────────────────
        if is_mini:
            mini_guides = {
                "SBI": (
                    f"**SBI — Mini Statement:**\n\n"
                    f"📱 **Missed Call:** Call **09223866666** from registered mobile\n"
                    f"  Last 5 transactions sent via SMS\n\n"
                    f"📱 **SMS:** Send **MSTMT** to **09223866666**\n\n"
                    f"📱 **YONO App:** Login → Account → View Statement\n\n"
                    f"📱 **Passbook:** Update at any SBI ATM or branch"
                ),
                "HDFC": (
                    f"**HDFC — Mini Statement:**\n\n"
                    f"📱 **Missed Call:** Call **09223920001** from registered mobile\n"
                    f"📱 **SMS:** Send **MSTMT** to **5676712**\n"
                    f"📱 **HDFC App:** Login → Account → Statement"
                ),
                "ICICI": (
                    f"**ICICI — Mini Statement:**\n\n"
                    f"📱 **Missed Call:** Call **09222488888** from registered mobile\n"
                    f"📱 **SMS:** Send **ITRAN** to **09222488888**\n"
                    f"📱 **iMobile App:** Login → Accounts → Statement"
                ),
            }
            return mini_guides.get(bank, f"Check {bank} app or website for mini statement. Or call customer care.")

        # ── Transfer Money ───────────────────────────────────────────────────
        if is_transfer:
            return (
                f"**{bank} — Transfer Money:**\n\n"
                f"📱 **UPI (Instant, Free):**\n"
                f"  1. Open {bank} UPI app (BHIM, Google Pay, PhonePe)\n"
                f"  2. Enter recipient UPI ID or scan QR\n"
                f"  3. Enter amount → Enter UPI PIN\n"
                f"  4. Money transferred instantly\n\n"
                f"📱 **NEFT (30 min - 2 hours):**\n"
                    f"  1. Login to NetBanking\n"
                    f"  2. Go to Funds Transfer → NEFT\n"
                    f"  3. Add beneficiary (wait 30 min for approval)\n"
                    f"  4. Enter amount → Confirm\n"
                    f"  Working hours: 8 AM - 6:30 PM (Mon-Sat)\n\n"
                f"📱 **RTGS (Real-time, for Rs 2L+):**\n"
                    f"  Same as NEFT but select RTGS\n"
                    f"  For amounts Rs 2 lakh and above\n"
                    f"  Available 24x7\n\n"
                f"📱 **IMPS (Instant, 24x7):**\n"
                    f"  Via mobile banking or ATM\n"
                    f"  Available 24x7, including holidays\n\n"
                f"⚠️ **Never share UPI PIN or OTP with anyone.**"
            )

        # ── Block Card ───────────────────────────────────────────────────────
        if is_block:
            block_numbers = {
                "SBI": "1800-11-2211 (toll-free) or 0124-2367777",
                "HDFC": "1800-266-4332 (toll-free) or 022-61717100",
                "ICICI": "1800-103-8181 (toll-free) or 022-33667777",
                "PNB": "1800-180-2223 (toll-free) or 0120-2490000",
                "BOB": "1800-223-222 (toll-free) or 022-66699000",
                "Canara": "1800-425-0018 (toll-free)",
                "Union Bank": "1800-22-2244 (toll-free)",
                "Axis": "1800-233-5577 (toll-free) or 022-67987700",
                "Kotak": "1860-266-0000 (toll-free)",
            }
            number = block_numbers.get(bank, "Check bank website for block card number")
            return (
                f"**{bank} — Block Lost/Stolen Card:**\n\n"
                f"🚨 **IMMEDIATELY call:** {number}\n\n"
                f"📱 **Via App:**\n"
                f"  1. Open {bank} mobile app\n"
                f"  2. Go to Cards → Select card → Block Card\n"
                f"  3. Card blocked instantly\n\n"
                f"📱 **Via NetBanking:**\n"
                f"  1. Login → Cards → Block Card\n"
                f"  2. Confirm blocking\n\n"
                f"📱 **SMS (SBI):** Send BLOCK <last 4 digits> to 567676\n\n"
                f"📋 **After blocking:**\n"
                f"  - File police complaint (FIR) if stolen\n"
                f"  - Request new card via app or branch\n"
                f"  - Update auto-debit settings for new card"
            )

        # ── KYC Update ───────────────────────────────────────────────────────
        if is_kyc:
            return (
                f"**{bank} — KYC Update / Aadhaar Linking:**\n\n"
                f"📱 **Online e-KYC:**\n"
                f"  1. Login to {bank} NetBanking\n"
                f"  2. Go to Profile → KYC / Aadhaar Update\n"
                f"  3. Enter Aadhaar number\n"
                f"  4. OTP sent to Aadhaar-linked mobile\n"
                f"  5. Enter OTP → KYC updated\n\n"
                f"📱 **Via Branch:**\n"
                f"  1. Visit nearest {bank} branch\n"
                f"  2. Carry: Aadhaar, PAN, original documents\n"
                f"  3. Fill KYC form\n"
                f"  4. Submit → Updated in 1-3 working days\n\n"
                f"📱 **Video KYC (V-CIP):**\n"
                f"  Some banks offer video KYC from home\n"
                f"  Check {bank} app for V-CIP option\n\n"
                f"⚠️ **Important:** Keep KYC updated to avoid account freeze."
            )

        # ── Statement ────────────────────────────────────────────────────────
        if is_statement:
            return (
                f"**{bank} — Account Statement:**\n\n"
                f"📱 **Download from NetBanking:**\n"
                f"  1. Login to {bank} NetBanking\n"
                f"  2. Go to Accounts → Statement\n"
                f"  3. Select date range\n"
                f"  4. Download as PDF\n\n"
                f"📱 **Email Statement:**\n"
                f"  Set up auto email statement in NetBanking settings\n"
                f"  Monthly statement sent to registered email\n\n"
                f"📱 **Passbook Update:**\n"
                f"  Visit branch with passbook\n"
                f"  Or use passbook printing kiosk at branch"
            )

        # Default: show balance guide
        return self._handle_bank(f"balance {bank}")

    # ── Electricity Bill Guidance ────────────────────────────────────────────

    def _handle_electricity(self, args: str) -> str:
        """Electricity bill payment and discom guidance."""
        args = args.strip().lower()
        if not args:
            return (
                "**Electricity Bill Services:**\n\n"
                "Usage:\n"
                "  electricity: pay bill Delhi — Pay BSES/TPDDL bill\n"
                "  electricity: pay bill Mumbai — Pay Adani/MSEDCL bill\n"
                "  electricity: complaint Bangalore — Register complaint\n"
                "  electricity: new connection Chennai — Apply for new connection\n\n"
                "Supported cities: Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad,"
                " Pune, Ahmedabad, Jaipur, Lucknow, and all major cities"
            )

        # Detect city and discom
        city_discoms = {
            "delhi": {"discoms": ["BSES Rajdhani", "BSES Yamuna", "TPDDL"], "portal": "bsesdelhi.com / tpddl.com", "app": "BSES App", "pay": "PhonePe, Google Pay, Paytm, BSES website"},
            "mumbai": {"discoms": ["Adani Electricity", "MSEDCL"], "portal": "adani.com / msedcl.com", "app": "Adani Electricity App", "pay": "Adani website, MahaVitaran App, UPI"},
            "bangalore": {"discoms": ["BESCOM"], "portal": "bescom.karnataka.gov.in", "app": "BESCOM App", "pay": "BESCOM website, UPI, Bangalore One"},
            "bengaluru": {"discoms": ["BESCOM"], "portal": "bescom.karnataka.gov.in", "app": "BESCOM App", "pay": "BESCOM website, UPI, Bangalore One"},
            "chennai": {"discoms": ["TANGEDCO"], "portal": "tangedco.gov.in", "app": "TANGEDCO App", "pay": "TANGEDCO website, UPI"},
            "kolkata": {"discoms": ["CESC"], "portal": "cesc.co.in", "app": "CESC App", "pay": "CESC website, UPI"},
            "hyderabad": {"discoms": ["TSSPDCL", "TSSouthern", "TSNorthern"], "portal": "tssouthernpower.com", "app": "TSSPDCL App", "pay": "UPI, TSSPDCL website"},
            "pune": {"discoms": ["MSEDCL"], "portal": "msedcl.com", "app": "MahaVitaran App", "pay": "MSEDCL website, UPI"},
            "ahmedabad": {"discoms": ["UGVCL", "MGVCL"], "portal": "ugvcl.com", "app": "UGVCL App", "pay": "UGVCL website, UPI"},
            "jaipur": {"discoms": ["JVVNL", "JdVVNL"], "portal": "jvvnl.org", "app": "JVVNL App", "pay": "JVVNL website, UPI"},
            "lucknow": {"discoms": ["DVVNL", "MVVNL"], "portal": "dvvn.in", "app": "DVVNL App", "pay": "DVVNL website, UPI"},
        }

        # Detect city
        city = None
        for c in city_discoms:
            if c in args:
                city = c
                break

        if not city:
            city = "delhi"  # default

        discom_info = city_discoms[city]

        # Detect action
        is_pay = any(w in args for w in ["pay", "bill pay", "pay bill", "online pay"])
        is_complaint = any(w in args for w in ["complaint", "problem", "issue", "outage", "power cut", "bijli"])
        is_new = any(w in args for w in ["new connection", "naya connection", "apply", "new meter"])
        is_complaint_status = any(w in args for w in ["status", "track"])

        if is_complaint:
            return (
                f"**{city.title()} — Electricity Complaint:**\n\n"
                f"📱 **Register Complaint:**\n"
                f"  1. Call {discom_info['discoms'][0]} helpline (see below)\n"
                f"  2. Or visit {discom_info['portal']}\n"
                f"  3. Or use {discom_info['app']}\n"
                f"  4. Provide: Consumer number, complaint details\n\n"
                f"📱 **Common Issues:**\n"
                f"  - Power cut: Check if area-wide outage\n"
                f"  - Voltage fluctuation: Report to discom\n"
                f"  - Meter not working: Request meter replacement\n"
                f"  - Wrong bill: Submit reading with photo\n\n"
                f"📞 **Helpline:**\n"
                f"  - Emergency: 1912 (most states)\n"
                f"  - BSES Delhi: 011-49444944\n"
                f"  - MSEDCL: 1912\n"
                f"  - BESCOM: 1912\n"
                f"  - CESC: 1912\n\n"
                f"💡 **Tip:** Take photo of meter reading before complaining."
            )

        if is_new:
            return (
                f"**{city.title()} — New Electricity Connection:**\n\n"
                f"📋 **Documents Needed:**\n"
                f"  - Aadhaar card\n"
                f"  - Property ownership proof (sale deed / rental agreement)\n"
                f"  - Building approval plan\n"
                f"  - NOC from society (if apartment)\n"
                f"  - Passport-size photos\n\n"
                f"📱 **Apply Online:**\n"
                f"  1. Visit {discom_info['portal']}\n"
                f"  2. Register → Apply for New Connection\n"
                f"  3. Upload documents\n"
                f"  4. Pay application fee\n"
                f"  5. Inspection within 7-10 days\n"
                f"  6. Connection within 30 days\n\n"
                f"📱 **Apply Offline:**\n"
                f"  Visit {discom_info['discoms'][0]} office with documents\n\n"
                f"💰 **Cost:** Rs 5,000 - 25,000 (depends on load and area)\n"
                f"  - Application fee: Rs 100-500\n"
                f"  - Service line charge: Rs 2,000-10,000\n"
                f"  - Meter cost: Rs 1,000-3,000"
            )

        # Default: Pay bill
        return (
            f"**{city.title()} — Pay Electricity Bill:**\n\n"
            f"🏢 **Discom:** {', '.join(discom_info['discoms'])}\n"
            f"🌐 **Portal:** {discom_info['portal']}\n"
            f"📱 **App:** {discom_info['app']}\n\n"
            f"📱 **Online Payment Methods:**\n"
            f"  1. **Discom Website:** Visit {discom_info['portal']} → Pay Bill\n"
            f"  2. **UPI:** Google Pay / PhonePe / Paytm → Electricity → Select Discom\n"
            f"  3. **App:** {discom_info['app']} → Pay Bill\n"
            f"  4. **NEFT/NetBanking:** Login to your bank → Bill Payment\n\n"
            f"📱 **Offline Payment:**\n"
            f"  - Visit nearest {discom_info['discoms'][0]} office\n"
            f"  - Use authorized payment centers\n"
            f"  - Drop box at local office\n\n"
            f"📋 **How to Pay:**\n"
            f"  1. Find your Consumer Number (on previous bill)\n"
            f"  2. Enter on payment portal/app\n"
            f"  3. Verify name and amount\n"
            f"  4. Pay → Save receipt\n\n"                f"💡 **Tips:**\n"
                f"  - Set up auto-pay to avoid late fees\n"
                f"  - Late fee: Rs 100-500 per month\n"
                f"  - Check bill for subsidized rates (BPL families)\n\n"
                f"⚠️ **Disclaimer:** This is general guidance only. Always verify payment details on the official discom website. Zenix is not responsible for payment errors. Never share OTPs or passwords with anyone."
        )

    # ── Driving License Guidance ─────────────────────────────────────────────

    def _handle_driving_license(self, args: str) -> str:
        """Driving license application, renewal, and services."""
        args = args.strip().lower()
        if not args:
            return (
                "**Driving License Services:**\n\n"
                "Usage:\n"
                "  driving_license: apply — New DL application\n"
                "  driving_license: renew — Renew existing DL\n"
                "  driving_license: international — International DL\n"
                "  driving_license: test booking — Book DL test slot\n"
                "  driving_license: status — Check application status\n"
                "  driving_license: duplicate — Duplicate DL (lost)\n\n"
                "All services via: parivahan.gov.in"
            )

        is_apply = any(w in args for w in ["apply", "new dl", "naya license", "banwana", "learner"])
        is_renew = any(w in args for w in ["renew", "renewal", "validity", "extend"])
        is_international = any(w in args for w in ["international", "idp", "abroad", "foreign"])
        is_test = any(w in args for w in ["test", "slot", "booking", "appointment", "driving test"])
        is_status = any(w in args for w in ["status", "track", "check status"])
        is_duplicate = any(w in args for w in ["duplicate", "lost", "chori", "missing"])

        if is_apply:
            return (
                "**New Driving License — Step by Step:**\n\n"
                "📋 **Step 1: Learner's License (LL)**\n"
                "  Age required: 16 years (gearless), 18 years (with gear)\n"
                "  Documents: Aadhaar, age proof, address proof, photos\n"
                "  Apply: parivahan.gov.in → Driving License → New Learner License\n"
                "  Fee: Rs 200-500\n"
                "  Validity: 6 months\n"
                "  Test: Basic knowledge test (10 questions, online)\n\n"
                "📋 **Step 2: Permanent Driving License**\n"
                "  Wait: At least 30 days after Learner's License\n"
                "  Apply: parivahan.gov.in → Driving License → New DL\n"
                "  Documents: LL, Aadhaar, photos, address proof\n"
                "  Fee: Rs 200-1000 (varies by vehicle type)\n"
                "  Test: Practical driving test at RTO\n\n"
                "📋 **Step 3: Vehicle Classes**\n"
                "  LMV (Car): Age 18+, LL required\n"
                "  MCWG (Motorcycle): Age 18+, gear vehicle\n"
                "  MCWOG (Scooty): Age 16+, gearless <75cc\n"
                "  Transport: Age 20+, commercial vehicle\n\n"
                "📱 **Apply Online:**\n"
                "  1. Visit parivahan.gov.in\n"
                "  2. Select your state → RTO\n"
                "  3. Fill application → Upload documents\n"
                "  4. Pay fee online\n"
                "  5. Book slot for test\n"
                "  6. Attend test at RTO\n"
                "  7. DL dispatched within 7-15 days\n\n"
                "💡 **Tips:**\n"
                "  - Learn traffic signs before test\n"
                "  - Practice driving before practical test\n"
                "  - Carry all originals on test day"
            )

        if is_renew:
            return (
                "**Driving License Renewal:**\n\n"
                "📋 **When to Renew:**\n"
                "  - 30 days before expiry (or after expiry with late fee)\n"
                "  - Late fee: Rs 100/month (max Rs 1000)\n"
                "  - After 5 years expiry: Fresh application required\n\n"
                "📱 **Steps:**\n"
                "  1. Visit parivahan.gov.in\n"
                "  2. Select state → Renewal of DL\n"
                "  3. Enter DL number → Verify details\n"
                "  4. Upload: Aadhaar, photos, medical certificate (Form 1A)\n"
                "  5. Pay fee: Rs 200-500\n"
                "  6. No test required (usually)\n"
                "  7. New DL dispatched in 7-15 days\n\n"
                "📋 **Documents:**\n"
                "  - Original DL\n"
                "  - Aadhaar\n"
                "  - Passport-size photos\n"
                "  - Medical Certificate (Form 1A) from registered doctor\n\n"
                "💡 **Tip:** Start renewal 2-3 months before expiry."
            )

        if is_international:
            return (
                "**International Driving Permit (IDP):**\n\n"
                "📋 **Eligibility:**\n"
                "  - Valid Indian Driving License\n"
                "  - Age 18+\n"
                "  - Valid passport\n\n"
                "📱 **Steps:**\n"
                "  1. Apply at RTO where DL was issued\n"
                "  2. Or apply online: parivahan.gov.in\n"
                "  3. Documents: DL, Passport, Visa, photos\n"
                "  4. Fee: Rs 1000-2000\n"
                "  5. IDP issued in 1-3 days\n\n"
                "📋 **Documents:**\n"
                "  - Valid Indian DL\n"
                "  - Valid Passport\n"
                "  - Valid Visa (if applicable)\n"
                "  - Passport-size photos\n"
                "  - Address proof\n\n"
                "📋 **Validity:**\n"
                "  - 1 year from date of issue\n"
                "  - Valid in countries that recognize IDP\n"
                "  - Not valid in some countries (check before travel)\n\n"
                "💡 **Tip:** Some countries accept Indian DL directly (UAE, Singapore, etc.)."
            )

        if is_test:
            return (
                "**Book DL Test Slot:**\n\n"
                "📱 **Steps:**\n"
                "  1. Visit parivahan.gov.in\n"
                "  2. Select your state → RTO\n"
                "  3. Go to 'Appointment' or 'Slot Booking'\n"
                "  4. Select DL Test\n"
                "  5. Choose date and time slot\n"
                "  6. Confirm booking\n"
                "  7. Attend test at RTO on booked date\n\n"
                "📋 **What to Bring on Test Day:**\n"
                "  - Printed appointment receipt\n"
                "  - Original LL/DL\n"
                "  - Aadhaar\n"
                "  - Vehicle (for practical test)\n"
                "  - L/BTN for motorcycle test\n\n"
                "📋 **Test Format:**\n"
                "  - Online test: 20 questions, need 15 correct\n"
                "  - Practical: H-track, slope, parking, reverse\n"
                "  - Duration: 15-20 minutes\n\n"
                "💡 **Practice these before test:**\n"
                "  - Parallel parking\n"
                "  - Reverse gear driving\n"
                "  - Hill start (slope)\n"
                "  - Emergency braking"
            )

        if is_status:
            return (
                "**Check DL Application Status:**\n\n"
                "📱 **Steps:**\n"
                "  1. Visit parivahan.gov.in\n"
                "  2. Click 'Application Status'\n"
                "  3. Enter Application Number or DL Number\n"
                "  4. Enter date of birth\n"
                "  5. View current status\n\n"
                "📋 **Status Meanings:**\n"
                "  - Applied: Application received\n"
                "  - Under Processing: Being reviewed\n"
                "  - Test Scheduled: Book your test\n"
                "  - Test Passed: DL being printed\n"
                "  - Dispatched: Sent via post (7-15 days)\n"
                "  - Ready for Collection: Collect at RTO\n\n"
                "📞 **Helpline:** 0120-4688900 (parivahan)"
            )

        if is_duplicate:
            return (
                "**Duplicate Driving License:**\n\n"
                "📋 **When Needed:**\n"
                "  - DL lost, stolen, or damaged\n"
                "  - Name/address change\n\n"
                "📱 **Steps:**\n"
                "  1. File FIR if stolen\n"
                "  2. Visit parivahan.gov.in\n"
                "  3. Apply for Duplicate DL\n"
                "  4. Enter DL number → Verify details\n"
                "  5. Upload: Aadhaar, photos, FIR copy (if stolen)\n"
                "  6. Pay fee: Rs 200-500\n"
                "  7. No test required\n"
                "  8. New DL dispatched in 7-15 days\n\n"
                "📋 **Documents:**\n"
                "  - Aadhaar\n"
                "  - Passport-size photos\n"
                "  - FIR copy (if stolen)\n"
                "  - Address proof\n\n"
                "💡 **Tip:** Keep scanned copy of DL on phone for emergencies."
            )

        return self._handle_driving_license("apply")

    # ── Knowledge Base Search ────────────────────────────────────────────

    def _handle_knowledge(self, args: str) -> str:
        """Search the Indian knowledge base for curated legal, health, education content."""
        args = args.strip()
        if not args:
            return (
                "**Indian Knowledge Base:**\n\n"
                "Available domains:\n"
                "  - Constitution: Fundamental Rights, Duties, DPSP, Constitutional Bodies\n"
                "  - Legal Rights: RTI, Consumer Protection, Criminal Laws, Domestic Violence, FIR\n"
                "  - Health: Ayushman Bharat, Jan Aushadhi, COVID, Emergency Numbers\n"
                "  - Education: RTE, Scholarships, NEP 2020, NTA Exams\n"
                "  - Consumer Rights: DPDP Act, Cybercrime Reporting\n"
                "  - Labour Laws: Minimum Wages, EPF, ESI, Maternity Benefits\n"
                "  - Environment: Environmental Laws, Forest Rights Act\n\n"
                "Usage: knowledge: <query> | knowledge: fundamental rights | knowledge: RTI process"
            )

        try:
            from .knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            results = kb.search(args, top_k=3)

            if not results:
                return (
                    f"No results found for: '{args}'\n"
                    f"Try: knowledge: fundamental rights | knowledge: RTI | knowledge: consumer protection"
                )

            lines = [f"**Knowledge Base Results:**\n"]
            for i, r in enumerate(results, 1):
                domain_label = r["domain"].replace("_", " ").title()
                lines.append(f"**{i}. {r['title']}** [{domain_label}]")
                # Show first 500 chars of content
                content_preview = r["content"][:500]
                if len(r["content"]) > 500:
                    content_preview += "..."
                lines.append(content_preview)
                lines.append("")

            lines.append("⚠️ *This is general information. For specific legal/medical advice, consult a qualified professional.*")
            return "\n".join(lines)

        except Exception as e:
            return f"Knowledge base error: {e}"

    # ── Transliteration Tool ───────────────────────────────────────────────

    def _handle_transliterate(self, args: str) -> str:
        """Transliterate Roman text to Indic scripts."""
        args = args.strip()
        if not args:
            return (
                "**Transliteration Tool:**\n\n"
                "Usage:\n"
                "  transliterate: namaste to devanagari\n"
                "  transliterate: namaskaram to tamil\n"
                "  transliterate: hello to bengali\n"
                "  transliterate: naman to kannada\n\n"
                "Supported scripts: devanagari, bengali, tamil, telugu, gujarati, kannada, malayalam, odia, gurmukhi"
            )

        try:
            from .transliteration import transliterate as do_transliterate
            from .transliteration import is_indic_script, SCRIPT_MAP

            # Parse: <text> to <script>
            import re
            match = re.match(r'(.+?)\s+to\s+(\w+)$', args, re.IGNORECASE)
            if not match:
                # Try auto-detect
            text_to_convert = args.strip()
            target_script = "devanagari"  # default
            if match:
                text_to_convert = match.group(1).strip()
                target_script = match.group(2).strip().lower()

            if not text_to_convert:
                return "Error: No text provided for transliteration."

            # Already in Indic script?
            if is_indic_script(text_to_convert):
                return f"Text is already in Indic script: {text_to_convert}"

            # Valid script?
            if target_script not in SCRIPT_MAP:
                return (
                    f"Error: Unknown script '{target_script}'.\n"
                    f"Supported scripts: {', '.join(SCRIPT_MAP.keys())}"
                )

            result = do_transliterate(text_to_convert, target_script)

            if result and result != text_to_convert:
                return (
                    f"**Transliteration ({target_script.title()}):**\n"
                    f"  Original: {text_to_convert}\n"
                    f"  Script: {result}"
                )
            else:
                return (
                    f"Could not transliterate '{text_to_convert}' to {target_script}.\n"
                    f"Please ensure it is Romanized Indian text.\n"
                    f"Supported scripts: {', '.join(SCRIPT_MAP.keys())}"
                )

        except Exception as e:
            return f"Transliteration error: {e}"

    # ── Training Data Pipeline ──────────────────────────────────────────────

    def _handle_training_data(self, args: str) -> str:
        """Generate and export training data from user feedback."""
        args = args.strip().lower()
        if not args:
            args = "report"

        try:
            from .training_pipeline import training_pipeline

            if "report" in args:
                return training_pipeline.generate_report(days=30)

            elif "generate" in args:
                examples = training_pipeline.generate_training_examples(days=30)
                if not examples:
                    return "No training examples generated. Collect user feedback first."
                high = sum(1 for e in examples if e["quality"] >= 0.8)
                low = sum(1 for e in examples if e["quality"] <= 0.2)
                return (
                    f"**Training Data Generated:**\n"
                    f"  Total examples: {len(examples)}\n"
                    f"  High quality (thumbs up): {high}\n"
                    f"  Low quality (thumbs down): {low}\n"
                    f"  Neutral: {len(examples) - high - low}\n\n"
                    f"Use 'training_data: export jsonl' or 'training_data: export openai' to save."
                )

            elif "export" in args:
                examples = training_pipeline.generate_training_examples(days=30)
                if not examples:
                    return "No training examples to export. Generate first with 'training_data: generate'."

                if "openai" in args:
                    path = training_pipeline.export_openai_format(examples)
                    return f"Exported {len(examples)} examples in OpenAI format to:\n{path}"
                elif "pairs" in args or "dpo" in args:
                    pairs = training_pipeline.export_preference_pairs(examples, "preference_pairs.jsonl")
                    return f"Exported {len(pairs)} preference pairs for DPO/RHLF training."
                else:
                    path = training_pipeline.export_jsonl(examples)
                    return f"Exported {len(examples)} examples as JSONL to:\n{path}"

            else:
                return (
                    "**Training Data Commands:**\n"
                    "  training_data: report — Quality report\n"
                    "  training_data: generate — Generate examples\n"
                    "  training_data: export jsonl — Export as JSONL\n"
                    "  training_data: export openai — Export for OpenAI fine-tuning\n"
                    "  training_data: export pairs — Export DPO preference pairs"
                )

        except ImportError:
            return "Training pipeline module not available."
        except Exception as e:
            return f"Training pipeline error: {e}"

    # ── Abuse Prevention Stats ───────────────────────────────────────────────

    def _handle_abuse(self, args: str) -> str:
        """Check abuse prevention stats and session health."""
        args = args.strip().lower()
        if not args:
            args = "stats"

        try:
            from .abuse_prevention import abuse_tracker

            if "stats" in args:
                stats = abuse_tracker.stats()
                return (
                    f"**Abuse Prevention Stats:**\n"
                    f"  Active sessions: {stats['active_sessions']}\n"
                    f"  Banned sessions: {stats['banned_sessions']}\n"
                    f"  Total warnings: {stats['total_warnings']}\n"
                    f"  Injection attempts: {stats['total_injection_attempts']}"
                )

            elif "session" in args:
                # Extract session ID
                parts = args.split()
                sid = parts[1] if len(parts) > 1 else "default"
                stats = abuse_tracker.get_session_stats(sid)
                return (
                    f"**Session Stats: {sid[:12]}...**\n"
                    f"  Warnings: {stats['warnings']}\n"
                    f"  Injection attempts: {stats['injection_attempts']}\n"
                    f"  Tool calls (last min): {stats['tool_calls_last_min']}\n"
                    f"  Banned: {'Yes' if stats['is_banned'] else 'No'}\n"
                    f"  Messages: {stats['message_count']}\n"
                    f"  Age: {stats['age_seconds']:.0f}s"
                )

            elif "cleanup" in args:
                cleaned = abuse_tracker.cleanup_stale()
                return f"Cleaned up {cleaned} stale sessions."

            else:
                return (
                    "**Abuse Prevention Commands:**\n"
                    "  abuse: stats — Global stats\n"
                    "  abuse: session <id> — Check session\n"
                    "  abuse: cleanup — Remove stale sessions"
                )

        except ImportError:
            return "Abuse prevention module not available."
        except Exception as e:
            return f"Abuse prevention error: {e}"

    # ── Telecom Recharge Plans ──────────────────────────────────────────────

    def _handle_telecom(self, args: str) -> str:
        """Compare telecom recharge plans for Indian operators."""
        args = args.strip()
        if not args:
            return (
                "**Telecom Plan Comparison:**\n\n"
                "Usage:\n"
                "  telecom: Jio 399 — Show Jio Rs 399 plan details\n"
                "  telecom: compare 299 — Compare Rs 299 plans across operators\n"
                "  telecom: best 1gb per day — Best plans with 1GB/day\n"
                "  telecom: annual Airtel — Annual plans from Airtel\n\n"
                "Operators: Jio, Airtel, Vi (Vodafone Idea), BSNL"
            )

        args_lower = args.lower()

        # ── Plan Data ──────────────────────────────────────────────────────
        # Reference plans as of Aug 2026 (updated periodically)
        plans = {
            "jio": [
                {"price": 189, "validity": "28 days", "data": "2GB total", "calls": "Unlimited", "sms": "30", "type": "Pay as you go"},
                {"price": 299, "validity": "28 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Popular"},
                {"price": 349, "validity": "28 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Heavy Data"},
                {"price": 399, "validity": "56 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Value"},
                {"price": 599, "validity": "84 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Best Seller"},
                {"price": 999, "validity": "84 days", "data": "3GB/day", "calls": "Unlimited", "sms": "100", "type": "Heavy"},
                {"price": 2999, "validity": "365 days", "data": "2.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Annual"},
            ],
            "airtel": [
                {"price": 199, "validity": "28 days", "data": "2GB total", "calls": "Unlimited", "sms": "30", "type": "Basic"},
                {"price": 299, "validity": "28 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Popular"},
                {"price": 399, "validity": "56 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Value"},
                {"price": 599, "validity": "84 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Best Seller"},
                {"price": 999, "validity": "84 days", "data": "3GB/day", "calls": "Unlimited", "sms": "100", "type": "Heavy"},
                {"price": 3599, "validity": "365 days", "data": "2.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Annual"},
            ],
            "vi": [
                {"price": 179, "validity": "28 days", "data": "2GB total", "calls": "Unlimited", "sms": "30", "type": "Basic"},
                {"price": 299, "validity": "28 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Popular"},
                {"price": 399, "validity": "56 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Value"},
                {"price": 599, "validity": "84 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Best Seller"},
                {"price": 2999, "validity": "365 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Annual"},
            ],
            "bsnl": [
                {"price": 187, "validity": "28 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Budget"},
                {"price": 299, "validity": "56 days", "data": "1GB/day", "calls": "Unlimited", "sms": "100", "type": "Value"},
                {"price": 399, "validity": "84 days", "data": "1.5GB/day", "calls": "Unlimited", "sms": "100", "type": "Popular"},
                {"price": 997, "validity": "180 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Long Term"},
                {"price": 1499, "validity": "365 days", "data": "2GB/day", "calls": "Unlimited", "sms": "100", "type": "Annual"},
            ],
        }

        # Detect operator
        operator = None
        for op in plans:
            if op in args_lower:
                operator = op
                break

        # Detect price point
        price_match = re.search(r'(\d{3,5})', args)
        target_price = int(price_match.group(1)) if price_match else None

        # Detect intent
        is_compare = "compare" in args_lower
        is_best = "best" in args_lower
        is_annual = "annual" in args_lower or "yearly" in args_lower or "1 year" in args_lower
        data_filter = None
        for pattern in [r'(\d+(?:\.\d+)?)\s*gb\s*(?:per|/)?\s*day', r'(\d+(?:\.\d+)?)\s*gb/day']:
            m = re.search(pattern, args_lower)
            if m:
                data_filter = float(m.group(1))
                break

        # ── Annual Plans Comparison ─────────────────────────────────────────
        if is_annual and not operator:
            lines = ["**Annual Recharge Plans (365 days):**\n"]
            lines.append(f"{'Operator':<12} {'Price':>8} {'Data/Day':>10} {'Calls':>10} {'Per Day':>10}")
            lines.append("-" * 60)
            for op, op_plans in plans.items():
                for p in op_plans:
                    if "365" in p["validity"] or "annual" in p["type"].lower():
                        per_day = p["price"] / 365
                        lines.append(f"{op.upper():<12} Rs {p['price']:>5,} {p['data']:>10} {p['calls']:>10} Rs {per_day:>6.1f}")
            lines.append("\n*Prices indicative. Check operator apps for latest.*")
            return "\n".join(lines)

        # ── Compare specific price across operators ─────────────────────────
        if is_compare and target_price:
            lines = [f"**Plans around Rs {target_price}:**\n"]
            lines.append(f"{'Operator':<10} {'Price':>7} {'Validity':>10} {'Data':>12} {'Calls':>10}")
            lines.append("-" * 55)
            for op, op_plans in plans.items():
                # Find closest plan to target price
                closest = min(op_plans, key=lambda p: abs(p["price"] - target_price))
                if abs(closest["price"] - target_price) <= target_price * 0.3:
                    lines.append(f"{op.upper():<10} Rs {closest['price']:>4,} {closest['validity']:>10} {closest['data']:>12} {closest['calls']:>10}")
            lines.append("\n*Prices indicative. Check operator apps for latest.*")
            return "\n".join(lines)

        # ── Best plan with data filter ──────────────────────────────────────
        if is_best and data_filter:
            lines = [f"**Best plans with {data_filter}GB/day:**\n"]
            lines.append(f"{'Operator':<10} {'Price':>7} {'Validity':>10} {'Per Day':>10}")
            lines.append("-" * 45)
            for op, op_plans in plans.items():
                for p in op_plans:
                    if f"{data_filter}" in p["data"] and "day" in p["data"]:
                        validity_days = int(p["validity"].split()[0])
                        per_day = p["price"] / validity_days
                        lines.append(f"{op.upper():<10} Rs {p['price']:>4,} {p["validity"]:>10} Rs {per_day:>6.1f}")
            lines.append("\n*Prices indicative. Check operator apps for latest.*")
            return "\n".join(lines)

        # ── Show specific operator plans ────────────────────────────────────
        if operator:
            op_plans = plans[operator]
            lines = [f"**{operator.upper()} Recharge Plans:**\n"]
            lines.append(f"{'Price':>7} {'Validity':>10} {'Data':>12} {'Calls':>10} {'Type':>12}")
            lines.append("-" * 60)
            for p in op_plans:
                lines.append(f"Rs {p['price']:>4,} {p['validity']:>10} {p['data']:>12} {p['calls']:>10} {p['type']:>12}")
            lines.append("\n📱 **Recharge at:**")
            lines.append(f"  - {operator.upper()} app or website")
            lines.append("  - Paytm, PhonePe, Google Pay")
            lines.append("  - *Prices indicative. Check operator app for latest.*")
            return "\n".join(lines)

        # ── Show closest price plan ────────────────────────────────────────
        if target_price:
            all_closest = []
            for op, op_plans in plans.items():
                closest = min(op_plans, key=lambda p: abs(p["price"] - target_price))
                all_closest.append((op, closest))
            all_closest.sort(key=lambda x: abs(x[1]["price"] - target_price))

            lines = [f"**Closest plans to Rs {target_price}:**\n"]
            for op, p in all_closest:
                diff = abs(p["price"] - target_price)
                marker = " ← closest" if diff == min(abs(c[1]["price"] - target_price) for c in all_closest) else ""
                lines.append(f"  {op.upper()}: Rs {p['price']:,} ({p['validity']}, {p['data']}){marker}")
            lines.append("\n*Prices indicative. Use 'telecom: compare <price>' for detailed comparison.*")
            return "\n".join(lines)

        # Default: show all operators summary
        lines = ["**Telecom Plan Summary:**\n"]
        for op, op_plans in plans.items():
            cheapest = min(op_plans, key=lambda p: p["price"])
            best = max(op_plans, key=lambda p: p["price"])
            lines.append(f"  {op.upper()}: Rs {cheapest['price']:,} - Rs {best['price']:,}")
        lines.append("\nUsage: telecom: <operator> | telecom: compare <price> | telecom: best 1gb per day | telecom: annual")
        return "\n".join(lines)

    # ── Stamp Duty Calculator ───────────────────────────────────────────────

    def _handle_stamp_duty(self, args: str) -> str:
        """Calculate stamp duty and registration costs for property transactions."""
        args = args.strip()
        if not args:
            return (
                "**Stamp Duty Calculator:**\n\n"
                "Usage:\n"
                "  stamp_duty: 5000000 in Maharashtra\n"
                "  stamp_duty: 80 lakh Delhi\n"
                "  stamp_duty: 1 crore Karnataka\n\n"
                "Supports: Maharashtra, Delhi, Karnataka, Tamil Nadu, Gujarat, Rajasthan, UP, Bihar,"
                " West Bengal, Telangana, Andhra Pradesh, Kerala, Punjab, Haryana, MP, CG, Odisha, Goa"
            )

        args_lower = args.lower()

        # Parse property value
        value = 0
        # Handle lakh/crore
        cr_match = re.search(r'(\d+(?:\.\d+)?)\s*cr(?:ore)?s?', args_lower)
        lk_match = re.search(r'(\d+(?:\.\d+)?)\s*l(?:akh)?s?', args_lower)
        num_match = re.search(r'([\d,]+)', args)

        if cr_match:
            value = float(cr_match.group(1)) * 1_00_00_000
        elif lk_match:
            value = float(lk_match.group(1)) * 1_00_000
        elif num_match:
            value = float(num_match.group(1).replace(',', ''))

        if value <= 0:
            return "Please provide property value. Example: stamp_duty: 50 lakh Maharashtra"

        # Detect state
        state = None
        state_keywords = {
            "maharashtra": "Maharashtra", "mumbai": "Maharashtra", "pune": "Maharashtra",
            "delhi": "Delhi", "new delhi": "Delhi", "ncr": "Delhi",
            "karnataka": "Karnataka", "bangalore": "Karnataka", "bengaluru": "Karnataka",
            "tamil nadu": "Tamil Nadu", "chennai": "Tamil Nadu",
            "gujarat": "Gujarat", "ahmedabad": "Gujarat", "surat": "Gujarat",
            "rajasthan": "Rajasthan", "jaipur": "Rajasthan",
            "uttar pradesh": "UP", "up": "UP", "noida": "UP", "lucknow": "UP",
            "west bengal": "West Bengal", "kolkata": "West Bengal",
            "bihar": "Bihar", "patna": "Bihar",
            "telangana": "Telangana", "hyderabad": "Telangana",
            "andhra pradesh": "AP", "vijayawada": "AP",
            "kerala": "Kerala", "kochi": "Kerala", "thiruvananthapuram": "Kerala",
            "punjab": "Punjab", "amritsar": "Punjab", "ludhiana": "Punjab",
            "haryana": "Haryana", "gurgaon": "Haryana", "gurugram": "Haryana",
            "madhya pradesh": "MP", "bhopal": "MP", "indore": "MP",
            "chhattisgarh": "CG", "raipur": "CG",
            "odisha": "Odisha", "bhubaneswar": "Odisha",
            "goa": "Goa", "panaji": "Goa",
        }
        for keyword, st in state_keywords.items():
            if keyword in args_lower:
                state = st
                break

        if not state:
            state = "Maharashtra"  # default

        # State-wise stamp duty rates (approximate FY 2025-26)
        stamp_rates = {
            "Maharashtra": {"rate": 6.0, "metro额外": 1.0, "reg_fee": 1.0, "note": "Mumbai/Nagpur/Pune: 6% + 1% metro surcharge"},
            "Delhi": {"rate": 4.0, "metro额外": 0, "reg_fee": 1.0, "note": "4% stamp duty + 1% registration"},
            "Karnataka": {"rate": 5.6, "metro额外": 0, "reg_fee": 1.0, "note": "5.6% (Bengaluru Urban), 5.6% (other districts)"},
            "Tamil Nadu": {"rate": 7.0, "metro额外": 0, "reg_fee": 1.0, "note": "7% stamp duty + 1% registration"},
            "Gujarat": {"rate": 4.9, "metro额外": 0, "reg_fee": 1.0, "note": "4.9% stamp duty + 1% registration"},
            "Rajasthan": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "UP": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "West Bengal": {"rate": 6.0, "metro额外": 1.0, "reg_fee": 1.0, "note": "6% + 1% metro surcharge (Kolkata)"},
            "Bihar": {"rate": 5.0, "metro额外": 0, "reg_fee": 2.0, "note": "5% stamp duty + 2% registration"},
            "Telangana": {"rate": 5.0, "metro额外": 0.5, "reg_fee": 0.5, "note": "5% stamp duty + 0.5% registration"},
            "AP": {"rate": 5.0, "metro额外": 0, "reg_fee": 0.5, "note": "5% stamp duty + 0.5% registration"},
            "Kerala": {"rate": 5.0, "metro额外": 0, "reg_fee": 2.0, "note": "5% stamp duty + 2% registration"},
            "Punjab": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "Haryana": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "MP": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "CG": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "Odisha": {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "5% stamp duty + 1% registration"},
            "Goa": {"rate": 3.5, "metro额外": 0, "reg_fee": 1.0, "note": "3.5% stamp duty + 1% registration"},
        }

        rates = stamp_rates.get(state, {"rate": 5.0, "metro额外": 0, "reg_fee": 1.0, "note": "Approximate rates"})

        # Calculate costs
        stamp_duty = value * rates["rate"] / 100
        metro_surcharge = value * rates["metro额外"] / 100
        reg_fee = min(value * rates["reg_fee"] / 100, 30000)  # cap registration fee
        total = stamp_duty + metro_surcharge + reg_fee

        # Check for concessions
        concession_notes = []
        if value <= 10_00_000:
            concession_notes.append("  🏠 Properties under Rs 10L may get stamp duty concession in some states")
        if "woman" in args_lower or "female" in args_lower or "wife" in args_lower:
            concession_notes.append("  👩 Women buyers get 1-2% concession in Maharashtra, Karnataka, Delhi")

        lines = [
            f"**Stamp Duty Calculation — {state}:**\n",
            f"  🏠 Property Value: Rs {value:,.0f}",
            f"  📋 Stamp Duty ({rates['rate']}%): Rs {stamp_duty:,.0f}",
        ]
        if metro_surcharge > 0:
            lines.append(f"  🏙️ Metro Surcharge ({rates['metro额外']}%): Rs {metro_surcharge:,.0f}")
        lines.append(f"  📝 Registration Fee: Rs {reg_fee:,.0f}")
        lines.append(f"  \n  💰 **Total Registration Cost: Rs {total:,.0f}**")
        lines.append(f"  📊 As % of property value: {total/value*100:.1f}%")

        if concession_notes:
            lines.append(f"\n💡 **Concessions:**")
            lines.extend(concession_notes)

        lines.extend([
            f"\n📝 **Note:** {rates['note']}",
            f"\n⚠️ *Actual rates may vary. Consult a property lawyer for exact calculation.*",
            f"📌 *Additional costs: Legal fees, brokerage, GST on under-construction properties.*",
        ])

        return "\n".join(lines)

    # ── Panchang / Astrology ────────────────────────────────────────────────

    def _handle_panchang(self, args: str) -> str:
        """Hindu Panchang, Islamic calendar, and muhurat information."""
        from datetime import datetime, timedelta

        args = args.strip().lower()
        now = datetime.now()

        # ── Tithi (Lunar Day) Calculation ───────────────────────────────────
        # Simplified lunar calendar calculation
        # Reference: Amanta system (used in most of India)
        SYNODIC_MONTH = 29.530588  # days
        LUNAR_EPOCH = datetime(2000, 1, 6, 18, 14)  # known new moon

        days_since_epoch = (now - LUNAR_EPOCH).total_seconds() / 86400
        lunar_age = days_since_epoch % SYNODIC_MONTH
        tithi_num = int(lunar_age / SYNODIC_MONTH * 30) + 1
        if tithi_num > 30:
            tithi_num = 30

        # Tithi names
        tithi_names = [
            "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
            "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
            "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
            "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
            "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
            "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
        ]
        tithi_name = tithi_names[tithi_num - 1]
        paksha = "Shukla Paksha" if tithi_num <= 15 else "Krishna Paksha"
        day_in_paksha = tithi_num if tithi_num <= 15 else tithi_num - 15

        # ── Nakshatra ───────────────────────────────────────────────────────
        NAKSHATRAS = [
            "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
            "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
            "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
            "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
            "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
            "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
        ]
        nak_num = int((lunar_age / SYNODIC_MONTH * 27) % 27)
        nakshatra = NAKSHATRAS[nak_num]

        # ── Yoga ────────────────────────────────────────────────────────────
        YOGAS = [
            "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
            "Atiganda", "Sukarman", "Dhriti", "Shula", "Ganda",
            "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
            "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
            "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
            "Indra", "Vaidhriti",
        ]
        sun_long = (days_since_epoch * 0.9856) % 360  # approximate
        moon_long = (lunar_age / SYNODIC_MONTH * 360) % 360
        yoga_num = int(((sun_long + moon_long) / (360 / 27)) % 27)
        yoga = YOGAS[yoga_num]

        # ── Karana ──────────────────────────────────────────────────────────
        KARANAS = [
            "Kimstughna", "Shakuni", "Chatushpada", "Nagava",
            "Kintughna", "Bava", "Balava", "Kaulava", "Taitila",
            "Garaja", "Vanija", "Vishti",
        ]
        karana_num = int(lunar_age / SYNODIC_MONTH * 60) % 12
        karana = KARANAS[karana_num]

        # ── Rashi (Moon Sign) ──────────────────────────────────────────────
        RASHIS = [
            "Mesh (Aries)", "Vrishabh (Taurus)", "Mithun (Gemini)",
            "Kark (Cancer)", "Singh (Leo)", "Kanya (Virgo)",
            "Tula (Libra)", "Vrishchik (Scorpio)", "Dhanu (Sagittarius)",
            "Makar (Capricorn)", "Kumbh (Aquarius)", "Meen (Pisces)",
        ]
        rashi_num = int(moon_long / 30) % 12
        rashi = RASHIS[rashi_num]

        # ── Varam (Day of Week) ─────────────────────────────────────────────
        VARAMS = ["Ravivar", "Somavar", "Mangalvar", "Budhvar", "Guruvar", "Shukravar", "Shanivar"]
        varam = VARAMS[now.weekday()]

        # ── Islamic Date (Hijri) ────────────────────────────────────────────
        # Simplified calculation
        islamic_epoch = datetime(622, 7, 16)  # approximate
        days_diff = (now - islamic_epoch).days
        hijri_year = int(days_diff / 354.36667)
        hijri_days = days_diff - int(hijri_year * 354.36667)
        hijri_month = int(hijri_days / 29.5) + 1
        if hijri_month > 12:
            hijri_month = 12
        hijri_day = int(hijri_days - (hijri_month - 1) * 29.5) + 1
        hijri_months = [
            "Muharram", "Safar", "Rabi ul-Awwal", "Rabi ul-Thani",
            "Jumada al-Ula", "Jumada al-Thani", "Rajab", "Sha'ban",
            "Ramadan", "Shawwal", "Dhul Qi'dah", "Dhul Hijjah",
        ]
        hijri_month_name = hijri_months[min(hijri_month - 1, 11)]

        # ── Muhurat (Auspicious Times) ──────────────────────────────────────
        # Abhijit Muhurat (approximate: midday)
        sunrise_hour = 6  # approximate
        sunset_hour = 18  # approximate
        abhijit_start = 11 + 48 / 60  # ~11:48 AM
        abhijit_end = 12 + 36 / 60  # ~12:36 PM

        # Rahu Kaal (approximate)
        rahu_duration = 1.5  # hours
        rahu_start_hour = sunrise_hour + ((now.weekday() + 1) % 7 + 1) * 1.5
        rahu_end_hour = rahu_start_hour + rahu_duration

        # ── Format Output ───────────────────────────────────────────────────
        if "rashi" in args:
            return (
                f"**Moon Rashi (Rashi) — {now.strftime('%d %B %Y')}:**\n\n"
                f"  🌙 Moon Sign: **{rashi}**\n"
                f"  🌟 Nakshatra: **{nakshatra}**\n"
                f"  📿 Ruling Planet: {['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
                                        'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter'][rashi_num]}\n"
                f"\n  *Predictions depend on complete birth chart (Kundli).*"
            )

        if "muhurat" in args or "shubh" in args:
            return (
                f"**Muhurat — {now.strftime('%d %B %Y')} ({varam}):**\n\n"
                f"  ✅ **Abhijit Muhurat:** 11:48 AM - 12:36 PM (best for new beginnings)\n"
                f"  🚫 **Rahu Kaal:** {int(rahu_start_hour)}:{int((rahu_start_hour%1)*60):02d} - {int(rahu_end_hour)}:{int((rahu_end_hour%1)*60):02d} (avoid new work)\n"
                f"  ✅ **Amrit Ghat:** 10:00 AM - 11:30 AM (good for important tasks)\n"
                f"  ✅ **Dawn Period:** 4:30 AM - 6:00 AM (Brahma Muhurat)\n\n"
                f"  📿 **Today's Tithi:** {tithi_name} ({paksha}, Day {day_in_paksha})\n"
                f"  ⭐ **Nakshatra:** {nakshatra}\n"
                f"  🧘 **Yoga:** {yoga}\n\n"
                f"  *Muhurat times vary by location. Consult local Panchang for exact times.*"
            )

        # Default: Full Panchang
        lines = [
            f"**Hindu Panchang — {now.strftime('%A, %d %B %Y')}**\n",
            f"📅 **Hindu Date:** {paksha}, {tithi_name} (Day {day_in_paksha})\n",
            f"⭐ **Nakshatra:** {nakshatra}\n",
            f"🧘 **Yoga:** {yoga}\n",
            f"🔧 **Karana:** {karana}\n",
            f"🌙 **Moon Sign (Rashi):** {rashi}\n",
            f"📆 **Day (Varam):** {varam}\n",
            f"\n📅 **Islamic Date:** {hijri_day} {hijri_month_name} {hijri_year + 1} AH\n",
            f"⏰ **Muhurat:**",
            f"  ✅ Abhijit: 11:48 AM - 12:36 PM",
            f"  🚫 Rahu Kaal: {int(rahu_start_hour)}:{int((rahu_start_hour%1)*60):02d} - {int(rahu_end_hour)}:{int((rahu_end_hour%1)*60):02d}",
            f"\n📌 *Panchang times are approximate. Check drikpanchang.com for precise local times.*",
        ]

        return "\n".join(lines)

    # ── Hospital / Blood Bank Finder ────────────────────────────────────────

    def _handle_hospital(self, args: str) -> str:
        """Find hospitals, blood banks, and pharmacies using OpenStreetMap."""
        args = args.strip()
        if not args:
            return "Usage: hospital: near Delhi | blood bank: Mumbai | pharmacy: Bangalore"

        args_lower = args.lower()

        # Determine search type
        if "blood bank" in args_lower:
            query_type = "blood bank"
            search_query = args_lower.replace("blood bank", "").replace("near", "").replace("in", "").strip()
        elif "pharmacy" in args_lower or "chemist" in args_lower or "medical store" in args_lower:
            query_type = "pharmacy"
            search_query = args_lower.replace("pharmacy", "").replace("chemist", "").replace("medical store", "").replace("near", "").replace("in", "").strip()
        elif "clinic" in args_lower:
            query_type = "clinic"
            search_query = args_lower.replace("clinic", "").replace("near", "").replace("in", "").strip()
        else:
            query_type = "hospital"
            search_query = args_lower.replace("hospital", "").replace("near", "").replace("in", "").strip()

        if not search_query:
            search_query = "Delhi"  # default

        try:
            # Use Nominatim to find the location first
            encoded = urllib.parse.quote(f"{query_type} near {search_query}, India")
            url = (
                f"https://nominatim.openstreetmap.org/search"
                f"?q={encoded}&format=json&limit=5&countrycodes=in&addressdetails=1"
            )
            data = _http_get(url, timeout=10, headers={"User-Agent": "Zenix/1.0"})

            if not data:
                # Try a broader search
                encoded2 = urllib.parse.quote(f"{query_type} {search_query}")
                url2 = (
                    f"https://nominatim.openstreetmap.org/search"
                    f"?q={encoded2}&format=json&limit=5&countrycodes=in"
                )
                data = _http_get(url2, timeout=10, headers={"User-Agent": "Zenix/1.0"})

            if data:
                lines = [f"**{query_type.title()}s near {search_query.title()}:**\n"]
                for i, place in enumerate(data[:5], 1):
                    name = place.get("display_name", "Unknown")
                    name_parts = name.split(", ")
                    short_name = ", ".join(name_parts[:3])
                    lat = place.get("lat", "N/A")
                    lon = place.get("lon", "N/A")
                    lines.append(f"{i}. **{short_name}**")
                    lines.append(f"   📐 Lat: {lat}, Lon: {lon}")
                    lines.append("")

                lines.append("💡 **Tips:**")
                if query_type == "hospital":
                    lines.append("  - For emergencies, call **108** (Ambulance)")
                    lines.append("  - Government hospitals: Free treatment under Ayushman Bharat")
                    lines.append("  - Check: mohfw.gov.in for govt hospital list")
                elif query_type == "blood bank":
                    lines.append("  - Blood bank helpline: **104**")
                    lines.append("  - Check: bloodbankonline.in or erakdaan.com for availability")
                    lines.append("  - National Blood Transfusion Council: nbtc.nic.in")
                elif query_type == "pharmacy":
                    lines.append("  - Jan Aushadhi stores: Generic medicines at 50-90% discount")
                    lines.append("  - Check: bfrjda.gov.in for Jan Aushadhi store locations")

                return "\n".join(lines)
            else:
                return (
                    f"Could not find {query_type}s near '{search_query}'.\n"
                    f"Try: hospital: near <city name> | blood bank: <city> | pharmacy: <city>\n"
                    f"Emergency: Call **108** for ambulance, **100** for police"
                )

        except Exception as e:
            return f"Hospital search error: {e}"

    # ── Train Status / PNR ──────────────────────────────────────────────────

    def _handle_train_status(self, args: str) -> str:
        """Get live train status, PNR status, or route info."""
        args = args.strip()
        if not args:
            return "Usage: train_status: 12951 | train_status: PNR 4521234567 | train_status: Delhi to Mumbai"

        args_lower = args.lower().strip()

        # PNR Status check
        if "pnr" in args_lower:
            pnr_match = re.search(r'(\d{10})', args)
            if pnr_match:
                pnr = pnr_match.group(1)
                # Try to get PNR status via web search
                try:
                    search_url = (
                        f"https://api.duckduckgo.com/?q=PNR+{pnr}+status&format=json"
                    )
                    # DuckDuckGo instant answer API doesn't always work for PNR
                    # Provide direct guidance instead
                    return (
                        f"**PNR Status Check: {pnr}**\n\n"
                        f"📱 **How to check PNR status:**\n"
                        f"  1. SMS: Send **PNR** {pnr} to **139**\n"
                        f"  2. Call: **139** (IVRS) → Choose PNR Enquiry\n"
                        f"  3. Online: indianrail.gov.in/pnr\n"
                        f"  4. App: ixigo, RailYatri, ConfirmTkt\n"
                        f"  5. WhatsApp: Send PNR to IRCTC WhatsApp bot\n\n"
                        f"  ⚠️ PNR status changes in real-time. Check 2-3 hours before journey."
                    )
                except Exception:
                    return f"Check PNR {pnr} at indianrail.gov.in/pnr or call 139."
            else:
                return "Please provide a 10-digit PNR number. Example: train_status: PNR 4521234567"

        # Train number lookup
        num_match = re.search(r'(\d{5})', args)
        if num_match:
            train_num = num_match.group(1)
            return (
                f"**Train {train_num} — Status Check:**\n\n"
                f"📱 **How to check live status:**\n"
                f"  1. SMS: Send **SPOT** {train_num} to **139**\n"
                f"  2. Call: **139** → Choose Train Running Status\n"
                f"  3. Online: trains.raillife.in or etrain.info\n"
                f"  4. Apps: ixigo, RailYatri, Where is my Train\n"
                f"  5. IRCTC: irctc.co.in → Train Status\n\n"
                f"  📍 Live running status updates every 5-10 minutes."
            )

        # Route search (city to city)
        if " to " in args_lower:
            parts = args_lower.split(" to ")
            if len(parts) == 2:
                from_city = parts[0].strip().replace("train", "").replace("from", "").strip()
                to_city = parts[1].strip()
                return (
                    f"**Trains: {from_city.title()} → {to_city.title()}**\n\n"
                    f"📱 **Find & book trains:**\n"
                    f"  1. IRCTC: irctc.co.in (official booking)\n"
                    f"  2. ixigo.com (compare prices, check availability)\n"
                    f"  3. RailYatri.in (live status, platform info)\n"
                    f"  4. confirmtkt.com (seat availability predictor)\n\n"
                    f"  💡 **Tips:**\n"
                    f"  - Book 120 days in advance for confirmed tickets\n"
                    f"  - Tatkal opens at 10 AM (AC) / 11 AM (Non-AC)\n"
                    f"  - Check alternative: Vande Bharat, Shatabdi for premium"
                )

        # Default: show popular trains
        from .realtime import train_service
        return train_service.lookup(args)

    # ── EPFO / PF Guidance ──────────────────────────────────────────────────

    def _handle_epfo(self, args: str) -> str:
        """Provide EPFO/PF guidance — balance check, UAN, claims, pension."""
        args = args.strip().lower()
        if not args:
            args = "help"

        if "balance" in args or "check" in args or "passbook" in args:
            return (
                "**Check PF Balance:**\n\n"
                "📱 **Method 1: EPFO Unified Portal**\n"
                "  1. Visit: unifiedportal-mem.epfindia.gov.in\n"
                "  2. Login with UAN + Password\n"
                "  3. Go to 'View' → 'Passbook'\n"
                "  4. Select financial year to see balance\n\n"
                "📱 **Method 2: UMANG App**\n"
                "  1. Download UMANG app\n"
                "  2. Search for 'EPFO'\n"
                "  3. Click 'Employee Centric Services'\n"
                "  4. Login with UAN + OTP\n"
                "  5. View passbook & balance\n\n"
                "📱 **Method 3: SMS**\n"
                "  Send: **EPFOHO UAN LAN** to **7738299899**\n"
                "  (LAN: ENG, HIN, TAM, TEL, MAR, KAN, MAL, BEN, GUJ, PUN, ORI, ASS)\n\n"
                "📱 **Method 4: Missed Call**\n"
                "  Give missed call to **011-22901406** from registered mobile\n\n"
                "  ⚠️ First activate UAN at: unifiedportal-mem.epfindia.gov.in"
            )

        elif "uan" in args:
            if "activate" in args:
                return (
                    "**Activate UAN (Universal Account Number):**\n\n"
                    "  1. Visit: unifiedportal-mem.epfindia.gov.in\n"
                    "  2. Click 'Activate UAN' under 'Important Links'\n"
                    "  3. Enter: UAN, Aadhaar, Name, DOB, Mobile, Email\n"
                    "  4. Get OTP on mobile → Enter OTP\n"
                    "  5. Set password → UAN activated!\n\n"
                    "  📌 **Find your UAN:**\n"
                    "  - Check salary slip (employer provides UAN)\n"
                    "  - SMS: **UAN** to **7738299899** (if mobile linked)\n"
                    "  - Ask your HR/employer"
                )
            else:
                return (
                    "**UAN (Universal Account Number):**\n\n"
                    "  - 12-digit number assigned to every EPFO member\n"
                    "  - One UAN = One PF account (even if you change jobs)\n"
                    "  - Link all PF accounts to single UAN\n\n"
                    "  **Find your UAN:**\n"
                    "  - Check salary slip\n"
                    "  - Ask employer HR\n"
                    "  - unifiedportal-mem.epfindia.gov.in"
                )

        elif "claim" in args or "withdraw" in args or "settlement" in args:
            return (
                "**PF Claim / Withdrawal Process:**\n\n"
                "📱 **Online Claim (Recommended):**\n"
                "  1. Login: unifiedportal-mem.epfindia.gov.in\n"
                "  2. Go to 'Manage' → 'KYC' → Update Aadhaar, PAN, Bank\n"
                "  3. Go to 'Online Services' → 'Claim (Form-31, 19, 10C & 10D)'\n"
                "  4. Select claim type:\n"
                    "     - Form 19: Final PF settlement\n"
                    "     - Form 31: Partial withdrawal (housing, medical, education)\n"
                    "     - Form 10C: Pension withdrawal\n"
                    "     - Form 10D: Monthly pension\n"
                "  5. Enter amount → Submit → OTP on Aadhaar-linked mobile\n"
                "  6. Amount credited in 5-20 working days\n\n"
                "📋 **Eligibility for Withdrawal:**\n"
                "  - Form 31: After 7 years of service (housing), 5 years (education)\n"
                "  - Form 19: After 2 months of last contribution (unemployment)\n"
                "  - Form 10C: After 10 years of service\n\n"
                "  📞 EPFO Helpline: **1800-118-185** (toll-free)"
            )

        elif "pension" in args or "eps" in args:
            return (
                "**EPFO Pension Scheme (EPS):**\n\n"
                "  📋 **How EPS Works:**\n"
                "  - 8.33% of basic salary goes to EPS (from employer's 12%)\n"
                "  - Pension = (Pensionable Salary × Pensionable Service) / 70\n"
                "  - Minimum service: 10 years\n"
                "  - Pension age: 58 years (can start at 50 with reduced amount)\n\n"
                "  💰 **Pension Amounts (Approximate):**\n"
                "  - 10 years service, Rs 15,000 salary: ~Rs 2,143/month\n"
                "  - 20 years service, Rs 15,000 salary: ~Rs 4,286/month\n"
                "  - 30 years service, Rs 15,000 salary: ~Rs 6,429/month\n"
                "  - 35 years service, Rs 25,000 salary: ~Rs 12,500/month\n\n"
                "  📋 **How to Apply for Pension:**\n"
                "  1. Submit Form 10D (online or at EPFO office)\n"
                "  2. Required: Aadhaar, bank details, cancelled cheque\n"
                "  3. Pension starts from date of filing application\n\n"
                "  ⚠️ **Important:**\n"
                "  - Pension is taxable if total income > Rs 5L\n"
                "  - EPS pension is NOT inflation-indexed\n"
                "  - Family pension: 50% to spouse after member's death"
            )

        elif "transfer" in args:
            return (
                "**PF Transfer (Job Change):**\n\n"
                "📱 **Online Transfer:**\n"
                "  1. Login: unifiedportal-mem.epfindia.gov.in\n"
                "  2. Go to 'Online Services' → 'One Member - One EPF Account'\n"
                "  3. Enter old employer's establishment code\n"
                "  4. Submit → Old employer approves → Amount transferred\n\n"
                "  ⏱️ Takes 20-30 days after approval\n"
                "  📋 Both old & new employer must have linked KYC\n\n"
                "  💡 **Tips:**\n"
                "  - Always transfer within 2 months of leaving job\n"
                "  - If employer doesn't respond in 15 days, escalate to EPFO\n"
                "  - Track status: unifiedportal → 'Track Claim Status'"
            )

        else:
            return (
                "**EPFO / PF Services:**\n\n"
                "  📌 Available commands:\n"
                "  - epfo: check balance — View PF balance & passbook\n"
                "  - epfo: uan activate — Activate your UAN\n"
                "  - epfo: uan — Know about UAN\n"
                "  - epfo: claim process — How to withdraw PF\n"
                "  - epfo: pension — EPS pension details\n"
                "  - epfo: transfer — Transfer PF on job change\n\n"
                "  📞 EPFO Helpline: **1800-118-185** (toll-free)\n"
                "  🌐 Portal: unifiedportal-mem.epfindia.gov.in\n"
                "  📱 App: UMANG → EPFO services"
            )

    # ── Petrol / Diesel Prices ──────────────────────────────────────────────

    def _handle_petrol(self, args: str) -> str:
        """Get live petrol/diesel prices."""
        try:
            from .realtime import petrol_service
            return petrol_service.get_price(args.strip())
        except ImportError:
            return "Petrol price service not available."
        except Exception as e:
            return f"Petrol price error: {e}"

    # ── Gold / Silver Prices ─────────────────────────────────────────────────

    def _handle_gold(self, args: str) -> str:
        """Get live gold/silver prices."""
        try:
            from .realtime import gold_service
            return gold_service.get_price()
        except ImportError:
            return "Gold price service not available."
        except Exception as e:
            return f"Gold price error: {e}"

    # ── Air Quality Index ────────────────────────────────────────────────────

    def _handle_aqi(self, args: str) -> str:
        """Get live AQI data."""
        try:
            from .realtime import aqi_service
            return aqi_service.get_aqi(args.strip())
        except ImportError:
            return "AQI service not available."
        except Exception as e:
            return f"AQI error: {e}"

    # ── IFSC Code Lookup ─────────────────────────────────────────────────────

    def _handle_ifsc(self, args: str) -> str:
        """Look up IFSC code or search banks using Razorpay IFSC API (free, no key)."""
        args = args.strip()
        if not args:
            return "Error: Provide an IFSC code. Example: ifsc: SBIN0001234"

        # Check if it looks like an IFSC code (11 chars, starts with bank code)
        is_ifsc = bool(re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', args.upper()))

        if is_ifsc:
            url = f"https://ifsc.razorpay.com/{args.upper()}"
            data = _http_get(url, timeout=8)
            if data and not data.get("error"):
                lines = [
                    f"**IFSC: {data.get('IFSC', args.upper())}**\n",
                    f"🏦 Bank: {data.get('BANK', 'N/A')}",
                    f"🏢 Branch: {data.get('BRANCH', 'N/A')}",
                    f"📍 Address: {data.get('ADDRESS', 'N/A')}",
                    f"🌆 City: {data.get('CITY', 'N/A')}",
                    f"🗺️ District: {data.get('DISTRICT', 'N/A')}",
                    f"🏛️ State: {data.get('STATE', 'N/A')}",
                    f"📞 Contact: {data.get('CONTACT', 'N/A')}",
                    f"📮 MICR: {data.get('MICR', 'N/A')}",
                    f"🔄 NEFT: {'✅' if data.get('NEFT') else '❌'} | "
                    f"RTGS: {'✅' if data.get('RTGS') else '❌'} | "
                    f"IMPS: {'✅' if data.get('IMPS') else '❌'} | "
                    f"UPI: {'✅' if data.get('UPI') else '❌'}",
                ]
                return "\n".join(lines)
            else:
                return f"IFSC code '{args.upper()}' not found. Check the code and try again."

        # Not an IFSC code — try bank search
        url = f"https://ifsc.razorpay.com/{args.upper()}"
        data = _http_get(url, timeout=8)
        if data and not data.get("error"):
            lines = [
                f"**IFSC: {data.get('IFSC', args.upper())}**\n",
                f"🏦 Bank: {data.get('BANK', 'N/A')}",
                f"🏢 Branch: {data.get('BRANCH', 'N/A')}",
                f"📍 Address: {data.get('ADDRESS', 'N/A')}",
                f"🌆 City: {data.get('CITY', 'N/A')}",
                f"🏛️ State: {data.get('STATE', 'N/A')}",
            ]
            return "\n".join(lines)

        return (
            f"Could not find IFSC for '{args}'.\n"
            f"Please provide a valid 11-character IFSC code (e.g., SBIN0001234).\n"
            f"Find IFSC at: bankbazaar.com/ifsc-code or google 'IFSC code <bank> <branch>'."
        )

    # ── EMI Calculator ───────────────────────────────────────────────────────

    def _handle_emi(self, args: str) -> str:
        """Calculate EMI for loans."""
        args = args.strip()
        if not args:
            return "Usage: emi: 5000000 for 20 years at 8.5%"

        # Parse: <amount> for <years> years at <rate>%
        match = re.match(
            r'([\d,]+(?:\.\d+)?)\s+(?:for\s+)?(\d+)\s+years?\s+(?:at\s+)?(\d+(?:\.\d+)?)%?',
            args, re.IGNORECASE
        )
        if not match:
            return (
                "Error: Could not parse. Use format:\n"
                "emi: <loan_amount> for <years> years at <interest_rate>%\n"
                "Example: emi: 5000000 for 20 years at 8.5%"
            )

        principal = float(match.group(1).replace(',', ''))
        years = int(match.group(2))
        annual_rate = float(match.group(3))
        months = years * 12
        monthly_rate = annual_rate / 100 / 12

        if monthly_rate == 0:
            emi = principal / months
        else:
            emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)

        total_payment = emi * months
        total_interest = total_payment - principal
        interest_ratio = (total_interest / principal * 100) if principal else 0

        return (
            f"**EMI Calculation:**\n"
            f"  💰 Loan Amount: Rs {principal:,.0f}\n"
            f"  📅 Duration: {years} years ({months} months)\n"
            f"  📈 Interest Rate: {annual_rate}% p.a.\n"
            f"\n"
            f"  ✅ **Monthly EMI: Rs {emi:,.0f}**\n"
            f"  💵 Total Payment: Rs {total_payment:,.0f}\n"
            f"  📊 Total Interest: Rs {total_interest:,.0f} ({interest_ratio:.1f}% of principal)\n"
            f"\n"
            f"**Amortization Summary:**\n"
            f"  Year 1 Interest: ~Rs {principal * annual_rate / 100:,.0f}\n"
            f"  Year {years} Interest: ~Rs {total_interest * 0.1:,.0f} (declines over time)\n"
            f"\n"
            f"*Tip: Prepaying even 1 extra EMI/year can save lakhs in interest!*"
            f"\n\n⚠️ **Disclaimer:** This is an approximate calculation for reference only. Actual EMI may vary based on processing fees, prepayments, floating rates, and lender policies. Always confirm with your bank or financial institution before taking a loan."
        )

    # ── Income Tax Calculator ────────────────────────────────────────────────

    def _handle_tax(self, args: str) -> str:
        """Calculate income tax under old and new regime (FY 2025-26)."""
        args = args.strip()
        if not args:
            return "Usage: tax: 1200000 | tax: income 1500000 with 80c 150000 hra 100000"

        # Parse income
        income = 0
        deductions_80c = 150000  # default max 80C
        hra = 0
        other_deductions = 0

        # Try JSON-like parse
        try:
            data = json.loads(args)
            if isinstance(data, dict):
                income = float(data.get("income", data.get("amount", 0)))
                deductions_80c = float(data.get("80c", 150000))
                hra = float(data.get("hra", 0))
                other_deductions = float(data.get("other", data.get("80d", 25000)))
            elif isinstance(data, (int, float)):
                income = float(data)
            else:
                raise ValueError
        except (json.JSONDecodeError, ValueError, TypeError):
            # Try regex parse
            income_match = re.search(r'([\d,]+)', args)
            if income_match:
                income = float(income_match.group(1).replace(',', ''))

            c80_match = re.search(r'80c\s+([\d,]+)', args, re.IGNORECASE)
            if c80_match:
                deductions_80c = float(c80_match.group(1).replace(',', ''))

            hra_match = re.search(r'hra\s+([\d,]+)', args, re.IGNORECASE)
            if hra_match:
                hra = float(hra_match.group(1).replace(',', ''))

        if income <= 0:
            return "Please provide annual income. Example: tax: 1200000"

        # ── New Tax Regime (FY 2025-26 default, Section 115BAC) ──
        new_slabs = [
            (400000, 0.0),
            (800000, 0.05),
            (1200000, 0.10),
            (1600000, 0.15),
            (2000000, 0.20),
            (2400000, 0.25),
            (float('inf'), 0.30),
        ]

        def _calc_regime_tax(taxable: float, slabs: list) -> float:
            tax = 0
            prev_limit = 0
            for limit, rate in slabs:
                if taxable <= prev_limit:
                    break
                bracket = min(taxable, limit) - prev_limit
                tax += bracket * rate
                prev_limit = limit
            return tax

        # New regime: standard deduction ₹75,000, no other deductions
        new_taxable = max(0, income - 75000)
        new_tax = _calc_regime_tax(new_taxable, new_slabs)
        # New regime rebate u/s 87A: if taxable income ≤ ₹12,00,000 → tax = 0
        if new_taxable <= 1200000:
            new_tax = 0
        # Cess: 4%
        new_tax_with_cess = new_tax * 1.04

        # ── Old Tax Regime ──
        old_slabs = [
            (250000, 0.0),
            (500000, 0.05),
            (1000000, 0.20),
            (float('inf'), 0.30),
        ]
        # For senior citizens (60-80): ₹3L exemption; super senior (80+): ₹5L
        # Using standard 2.5L for simplicity

        # Standard deduction: ₹50,000
        total_deductions = 50000 + deductions_80c + hra + other_deductions
        old_taxable = max(0, income - total_deductions)
        old_tax = _calc_regime_tax(old_taxable, old_slabs)
        # Old regime rebate u/s 87A: if taxable ≤ ₹5,00,000 → tax = 0
        if old_taxable <= 500000:
            old_tax = 0
        # Cess: 4%
        old_tax_with_cess = old_tax * 1.04

        # ── Comparison ──
        savings = old_tax_with_cess - new_tax_with_cess
        better = "New Regime" if new_tax_with_cess < old_tax_with_cess else "Old Regime"

        lines = [
            f"**Income Tax Calculation (FY 2025-26):**\n",
            f"  💰 Gross Income: Rs {income:,.0f}\n",
            f"  📊 **NEW REGIME (Default, u/s 115BAC):**",
            f"    Standard Deduction: Rs 75,000",
            f"    Taxable Income: Rs {new_taxable:,.0f}",
            f"    Tax: Rs {new_tax:,.0f}",
            f"    + Health & Edu Cess (4%): Rs {new_tax * 0.04:,.0f}",
            f"    **Total Tax: Rs {new_tax_with_cess:,.0f}**\n",
            f"  📊 **OLD REGIME:**",
            f"    Standard Deduction: Rs 50,000",
            f"    80C Deductions: Rs {deductions_80c:,.0f}",
            f"    HRA Exemption: Rs {hra:,.0f}",
            f"    Other Deductions: Rs {other_deductions:,.0f}",
            f"    Total Deductions: Rs {total_deductions:,.0f}",
            f"    Taxable Income: Rs {old_taxable:,.0f}",
            f"    Tax: Rs {old_tax:,.0f}",
            f"    + Health & Edu Cess (4%): Rs {old_tax * 0.04:,.0f}",
            f"    **Total Tax: Rs {old_tax_with_cess:,.0f}**\n",
        ]

        if savings > 0:
            lines.extend([
                f"  ✅ **Better: {better}** (saves Rs {savings:,.0f})",
            ])
        elif savings < 0:
            lines.extend([
                f"  ✅ **Better: {better}** (saves Rs {-savings:,.0f})",
            ])
        else:
            lines.append(f"  ⚖️ Both regimes result in equal tax.")

        lines.extend([
            f"\n  💡 Tip: New regime has lower rates but no deductions. "
            f"Old regime is better if you have high deductions (80C + HRA + 80D > ₹2L).",
            f"\n  📝 *Calculations are indicative. Consult a CA for exact filing.*",
            f"\n  ⚠️ **Disclaimer:** This is for informational purposes only and does not constitute tax advice. Tax laws change frequently. Always consult a qualified Chartered Accountant or tax advisor for accurate tax planning and filing.",
        ])

        return "\n".join(lines)

    # ── Registry API ──────────────────────────────────────────────────────────

    def get_tool_descriptions(self) -> str:
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"{name}: {tool['description']} Usage: {tool['usage']}")
        return "\n".join(descriptions)

    def execute(self, tool_name: str, args: str) -> str:
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found. Available: {', '.join(self.tools.keys())}"
        try:
            return tool["handler"](args)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"
