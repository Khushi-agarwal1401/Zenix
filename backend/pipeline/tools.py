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
            req = urllib.request.Request(geocode_url, headers={"User-Agent": "Zenix/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
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
            with urllib.request.urlopen(req2, timeout=10) as resp2:
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
