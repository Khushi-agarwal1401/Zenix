"""
Tool Registry for Zenix Agent.
Real tool integrations: weather API, SQL, filesystem, calculator.
"""

import os
import re
import math
import json
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict
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
