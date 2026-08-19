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
