"""
Real-Time Data Tools — petrol/diesel, LPG, gold/silver, AQI, train lookup.

Uses free APIs and government data sources.
Live APIs used:
  - Gold/Silver: metals.live (free, no key)
  - AQI: WAQI API (free demo token) / Open-Meteo air quality
  - Petrol/Diesel: mypetrolprice.com scrape with cache
  - LPG: Static reference (no reliable free API)
  - Train: Static reference (IRCTC API requires auth)
"""

import json
import re
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Shared SSL context for all HTTP requests
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
    except Exception as e:
        logger.warning(f"HTTP GET failed for {url}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Petrol / Diesel Prices
# ═══════════════════════════════════════════════════════════════════════════════

class PetrolPriceService:
    """Get current petrol/diesel prices for Indian cities.

    Strategy:
      1. Try live scrape from mypetrolprice.com (cached for 6 hours)
      2. Fall back to static reference data
    """

    # Static fallback prices (Rs/litre) — used when live scrape fails
    FALLBACK_PRICES = {
        "Mumbai": {"petrol": 103.44, "diesel": 89.97},
        "Delhi": {"petrol": 96.72, "diesel": 89.62},
        "Bangalore": {"petrol": 101.94, "diesel": 87.97},
        "Chennai": {"petrol": 102.63, "diesel": 94.24},
        "Kolkata": {"petrol": 106.31, "diesel": 92.76},
        "Hyderabad": {"petrol": 109.66, "diesel": 97.82},
        "Ahmedabad": {"petrol": 96.39, "diesel": 89.43},
        "Pune": {"petrol": 103.24, "diesel": 90.07},
        "Jaipur": {"petrol": 108.28, "diesel": 93.72},
        "Lucknow": {"petrol": 96.57, "diesel": 89.76},
        "Kanpur": {"petrol": 96.34, "diesel": 89.53},
        "Nagpur": {"petrol": 107.36, "diesel": 95.30},
        "Indore": {"petrol": 107.82, "diesel": 93.78},
        "Bhopal": {"petrol": 107.82, "diesel": 93.78},
        "Patna": {"petrol": 107.46, "diesel": 94.20},
        "Chandigarh": {"petrol": 96.20, "diesel": 84.26},
        "Thiruvananthapuram": {"petrol": 107.71, "diesel": 96.52},
        "Guwahati": {"petrol": 96.01, "diesel": 84.09},
        "Bhubaneswar": {"petrol": 103.19, "diesel": 94.76},
        "Dehradun": {"petrol": 97.34, "diesel": 90.29},
    }

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._CACHE_TTL = 6 * 3600  # 6 hours

    def _fetch_live_prices(self) -> Dict[str, Dict[str, float]]:
        """Try to fetch live prices from mypetrolprice.com."""
        if time.time() - self._cache_time < self._CACHE_TTL and self._cache:
            return self._cache

        try:
            url = "https://www.mypetrolprice.com/2/Petrol-price-in-India"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            })
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # Parse city-wise prices from HTML table
            # Pattern: <td>CityName</td><td>Rs XX.XX</td><td>Rs YY.YY</td>
            prices = {}
            # Find table rows with city data
            rows = re.findall(
                r'<td[^>]*>\s*([A-Za-z\s]+?)\s*</td>\s*'
                r'<td[^>]*>\s*Rs\s*([\d.]+)\s*</td>\s*'
                r'<td[^>]*>\s*Rs\s*([\d.]+)\s*</td>',
                html, re.IGNORECASE
            )
            for city_name, petrol, diesel in rows:
                city_name = city_name.strip()
                if city_name and len(city_name) > 2:
                    try:
                        prices[city_name] = {
                            "petrol": float(petrol),
                            "diesel": float(diesel),
                        }
                    except ValueError:
                        continue

            if prices:
                self._cache = prices
                self._cache_time = time.time()
                logger.info(f"Live petrol prices fetched for {len(prices)} cities")
                return prices

        except Exception as e:
            logger.warning(f"Live petrol price fetch failed: {e}")

        return self.FALLBACK_PRICES

    def get_price(self, city: str = "") -> str:
        """Get petrol/diesel price for a city."""
        prices = self._fetch_live_prices()
        source = "live" if prices is not self.FALLBACK_PRICES else "indicative"

        if not city:
            lines = [f"**Petrol/Diesel Prices (Rs/litre) [{source}]:**\n"]
            for c, p in sorted(prices.items()):
                lines.append(f"  {c}: Petrol Rs {p['petrol']:.2f} | Diesel Rs {p['diesel']:.2f}")
            lines.append(f"\n*Source: mypetrolprice.com | Prices may vary by pump*")
            return "\n".join(lines)

        city = city.strip().title()

        # Exact match
        if city in prices:
            p = prices[city]
            return (
                f"**Fuel Prices in {city}:**\n"
                f"  ⛽ Petrol: Rs {p['petrol']:.2f}/litre\n"
                f"  🛢️ Diesel: Rs {p['diesel']:.2f}/litre\n"
                f"  *Source: mypetrolprice.com ({source})*"
            )

        # Fuzzy match
        for c, p in prices.items():
            if city.lower() in c.lower() or c.lower() in city.lower():
                return (
                    f"**Fuel Prices in {c}:**\n"
                    f"  ⛽ Petrol: Rs {p['petrol']:.2f}/litre\n"
                    f"  🛢️ Diesel: Rs {p['diesel']:.2f}/litre\n"
                    f"  *Source: mypetrolprice.com ({source})*"
                )

        available = ", ".join(sorted(prices.keys())[:10])
        return (
            f"City '{city}' not found.\n"
            f"Available cities: {available}...\n"
            f"Check latest at: mypetrolprice.com"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LPG Prices
# ═══════════════════════════════════════════════════════════════════════════════

class LPGPriceService:
    """Get current LPG cylinder prices in India."""

    def get_price(self) -> str:
        return (
            "**LPG Cylinder Prices (Reference):**\n\n"
            "**Domestic (Household):**\n"
            "  14.2 kg cylinder:\n"
            "    Non-subsidized: Rs 903 (Delhi), Rs 929 (Mumbai)\n"
            "    Non-subsidized: Rs 918 (Chennai), Rs 906 (Kolkata)\n"
            "  Subsidized (via DBT): Rs 0 (direct benefit transfer to bank)\n\n"
            "**Commercial (Shops/Hotels):**\n"
            "  5 kg: Rs 450-500\n"
            "  19 kg: Rs 1,680-1,800\n"
            "  47.5 kg: Rs 4,200-4,500\n\n"
            "**How to Book:**\n"
            "  1. IVRS: Call your distributor's number\n"
            "  2. WhatsApp: Send 'REFILL' to your gas company's WhatsApp number\n"
            "  3. App: Use MyLPG, Bharatgas, HP Gas apps\n"
            "  4. Portal: mylpg.in\n\n"
            "**Subsidy Check:** Check your bank account for DBT credit.\n"
            "  Check status: mylpg.in → Check PA/DA status"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Gold / Silver Prices (Live)
# ═══════════════════════════════════════════════════════════════════════════════

class GoldPriceService:
    """Get current gold and silver prices in India.

    Uses:
      1. Live from metals.live API (free, no key)
      2. Live from goodreturns.in scrape
      3. Static fallback
    """

    def __init__(self):
        self._cache: Optional[str] = None
        self._cache_time: float = 0
        self._CACHE_TTL = 1800  # 30 minutes

    def _fetch_live_gold(self) -> Optional[Dict[str, Any]]:
        """Fetch live gold price from metals.live (free API, no key)."""
        if time.time() - self._cache_time < self._CACHE_TTL and self._cache:
            return self._cache

        # Try metals.live (completely free, no auth)
        data = _http_get("https://api.metals.live/v1/spot/gold", timeout=8)
        if data and isinstance(data, list) and len(data) > 0:
            latest = data[-1]  # most recent
            price_usd = latest.get("price", 0)
            if price_usd > 0:
                # Convert USD to INR (approximate — use currency tool for exact)
                usd_to_inr = _http_get(
                    "https://api.frankfurter.app/latest?from=USD&to=INR", timeout=5
                )
                inr_rate = 83.5  # fallback
                if usd_to_inr and "rates" in usd_to_inr:
                    inr_rate = usd_to_inr["rates"].get("INR", 83.5)

                # Gold price per 10g in India (troy oz = 31.1035g)
                gold_per_10g_usd = price_usd * 10 / 31.1035
                gold_per_10g_inr = gold_per_10g_usd * inr_rate

                self._cache = {
                    "gold_24k_10g": round(gold_per_10g_inr, 0),
                    "gold_22k_10g": round(gold_per_10g_inr * 0.916, 0),
                    "gold_18k_10g": round(gold_per_10g_inr * 0.75, 0),
                    "usd_per_oz": round(price_usd, 2),
                    "usd_to_inr": round(inr_rate, 2),
                    "source": "metals.live (live)",
                }
                self._cache_time = time.time()
                return self._cache

        # Try silver too
        silver_data = _http_get("https://api.metals.live/v1/spot/silver", timeout=8)
        if silver_data and isinstance(silver_data, list) and len(silver_data) > 0:
            silver_latest = silver_data[-1]
            silver_usd = silver_latest.get("price", 0)
            if silver_usd > 0 and self._cache:
                silver_per_kg_inr = silver_usd * 1000 / 31.1035 * self._cache.get("usd_to_inr", 83.5)
                self._cache["silver_per_kg"] = round(silver_per_kg_inr, 0)

        return self._cache

    def get_price(self) -> str:
        live = self._fetch_live_gold()

        if live and live.get("gold_24k_10g"):
            inr = live["usd_to_inr"]
            lines = [
                f"**Gold & Silver Prices [{live.get('source', 'live')}]:**\n",
                "**Gold (per 10 grams):**\n",
                f"  24 Carat (999): Rs {live['gold_24k_10g']:,.0f}",
                f"  22 Carat (916): Rs {live['gold_22k_10g']:,.0f}",
                f"  18 Carat (750): Rs {live['gold_18k_10g']:,.0f}",
            ]
            if live.get("silver_per_kg"):
                lines.append(f"\n**Silver (per kg):**")
                lines.append(f"  Silver: Rs {live['silver_per_kg']:,.0f}")
            lines.extend([
                f"\n*Gold spot: ${live.get('usd_per_oz', '?')}/oz | USD/INR: {inr}*",
                "",
                "**Buying Tips:**",
                "  - Always buy **BIS hallmark** gold (916 for 22K)",
                "  - Check **HUID** (Hallmark Unique Identification) number",
                "  - Making charges: 8-25% (negotiate for bulk)",
                "  - GST: 3% on gold + making charges",
                "  - Check live: goodreturns.in",
            ])
            return "\n".join(lines)

        # Fallback
        return (
            "**Gold & Silver Prices (Indicative):**\n\n"
            "**Gold (per 10 grams):**\n"
            "  24 Carat (999 purity): Rs 72,500-73,000\n"
            "  22 Carat (916 purity): Rs 66,500-67,000\n"
            "  18 Carat (750 purity): Rs 54,500-55,000\n\n"
            "**Silver (per kg):**\n"
            "  Silver: Rs 85,000-87,000\n\n"
            "*Live prices unavailable. Check goodreturns.in for latest.*"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Air Quality Index (Live)
# ═══════════════════════════════════════════════════════════════════════════════

class AQIService:
    """Get Air Quality Index for Indian cities.

    Uses:
      1. Open-Meteo Air Quality API (free, no key) — best for live data
      2. Static fallback
    """

    AQI_LEVELS = [
        (0, 50, "Good", "✅", "Air quality is satisfactory"),
        (51, 100, "Moderate", "🟡", "Acceptable, may affect sensitive people"),
        (101, 150, "Unhealthy for Sensitive", "🟠", "Reduce prolonged outdoor exertion"),
        (151, 200, "Unhealthy", "🔴", "Everyone may experience health effects"),
        (201, 300, "Very Unhealthy", "🟣", "Health alert: avoid outdoor activity"),
        (301, 500, "Hazardous", "☠️", "Emergency: stay indoors"),
    ]

    # City coordinates for Open-Meteo API
    CITY_COORDS = {
        "Delhi": (28.6139, 77.2090),
        "Mumbai": (19.0760, 72.8777),
        "Bangalore": (12.9716, 77.5946),
        "Chennai": (13.0827, 80.2707),
        "Kolkata": (22.5726, 88.3639),
        "Hyderabad": (17.3850, 78.4867),
        "Ahmedabad": (23.0225, 72.5714),
        "Pune": (18.5204, 73.8567),
        "Jaipur": (26.9124, 75.7873),
        "Lucknow": (26.8467, 80.9462),
        "Patna": (25.6093, 85.1376),
        "Chandigarh": (30.7333, 76.7794),
        "Guwahati": (26.1445, 91.7362),
        "Bhubaneswar": (20.2961, 85.8245),
        "Kochi": (9.9312, 76.2673),
        "Indore": (22.7196, 75.8577),
        "Bhopal": (23.2599, 77.4126),
        "Nagpur": (21.1458, 79.0882),
        "Dehradun": (30.3165, 78.0322),
        "Visakhapatnam": (17.6868, 83.2185),
    }

    def _get_aqi_level(self, aqi: int) -> tuple:
        for low, high, name, icon, desc in self.AQI_LEVELS:
            if low <= aqi <= high:
                return name, icon, desc
        return "Unknown", "❓", ""

    def _fetch_live_aqi(self, city: str) -> Optional[Dict[str, Any]]:
        """Fetch live AQI from Open-Meteo Air Quality API (free, no key)."""
        coords = self.CITY_COORDS.get(city)
        if not coords:
            return None

        lat, lon = coords
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&current=us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
            f"&timezone=auto"
        )
        data = _http_get(url, timeout=8)
        if not data or "current" not in data:
            return None

        current = data["current"]
        aqi = current.get("us_aqi", 0)
        if aqi <= 0:
            return None

        return {
            "aqi": int(aqi),
            "pm10": current.get("pm10", "N/A"),
            "pm25": current.get("pm2_5", "N/A"),
            "co": current.get("carbon_monoxide", "N/A"),
            "no2": current.get("nitrogen_dioxide", "N/A"),
            "so2": current.get("sulphur_dioxide", "N/A"),
            "ozone": current.get("ozone", "N/A"),
            "time": current.get("time", ""),
        }

    def get_aqi(self, city: str = "") -> str:
        if not city:
            # Show all cities with live data
            lines = ["**Air Quality Index (Live via Open-Meteo):**\n"]
            for c in sorted(self.CITY_COORDS.keys()):
                live = self._fetch_live_aqi(c)
                if live:
                    name, icon, _ = self._get_aqi_level(live["aqi"])
                    lines.append(f"  {icon} {c}: AQI {live['aqi']} ({name})")
                else:
                    lines.append(f"  ❓ {c}: data unavailable")
            lines.append("\n*Source: Open-Meteo Air Quality API*")
            return "\n".join(lines)

        city = city.strip().title()
        live = self._fetch_live_aqi(city)

        if live:
            name, icon, desc = self._get_aqi_level(live["aqi"])
            lines = [
                f"**Air Quality in {city}:**\n",
                f"  {icon} AQI: {live['aqi']} — {name}",
                f"  📋 {desc}\n",
                f"**Pollutants:**",
                f"  PM2.5: {live['pm25']} µg/m³",
                f"  PM10: {live['pm10']} µg/m³",
                f"  O₃: {live['ozone']} µg/m³",
                f"  NO₂: {live['no2']} µg/m³",
                f"  SO₂: {live['so2']} µg/m³",
                f"  CO: {live['co']} µg/m³\n",
                "**Precautions:**",
            ]
            if live["aqi"] > 200:
                lines.extend([
                    "  ☠️ Avoid ALL outdoor activity",
                    "  😷 Wear N95/KN95 mask if going out",
                    "  🏠 Use air purifier indoors",
                    "  🪟 Keep windows closed",
                ])
            elif live["aqi"] > 100:
                lines.extend([
                    "  😷 Wear mask outdoors",
                    "  🏃 Avoid prolonged outdoor exercise",
                    "  🏠 Consider air purifier indoors",
                ])
            else:
                lines.extend([
                    "  ✅ Safe for outdoor activities",
                    "  🌳 Good time for exercise outdoors",
                ])
            lines.append(f"\n*Source: Open-Meteo Air Quality API*")
            return "\n".join(lines)

        return (
            f"Live AQI data for '{city}' unavailable.\n"
            f"Available cities: {', '.join(sorted(self.CITY_COORDS.keys()))}\n"
            f"Check: safar.aqi.in or aqi.in"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Train Lookup (Static Reference)
# ═══════════════════════════════════════════════════════════════════════════════

class TrainLookupService:
    """Basic Indian train information (static reference data)."""

    POPULAR_TRAINS = {
        "Rajdhani": {
            "12301": {"name": "Howrah Rajdhani", "from": "New Delhi", "to": "Howrah", "time": "17h 20m", "runs": "Daily"},
            "12309": {"name": "Rajendra Nagar Rajdhani", "from": "New Delhi", "to": "Rajendra Nagar", "time": "12h 35m", "runs": "Daily"},
            "12951": {"name": "Mumbai Rajdhani", "from": "New Delhi", "to": "Mumbai Central", "time": "15h 35m", "runs": "Daily"},
            "12431": {"name": "Trivandrum Rajdhani", "from": "Hazrat Nizamuddin", "to": "Trivandrum", "time": "36h 15m", "runs": "Mon,Wed,Fri"},
            "12433": {"name": "Chennai Rajdhani", "from": "Hazrat Nizamuddin", "to": "Chennai Central", "time": "28h 10m", "runs": "Tue,Fri"},
        },
        "Shatabdi": {
            "12002": {"name": "Bhopal Shatabdi", "from": "New Delhi", "to": "Bhopal", "time": "7h 40m", "runs": "Daily"},
            "12010": {"name": "Ahmedabad Shatabdi", "from": "Mumbai Central", "to": "Ahmedabad", "time": "6h 25m", "runs": "Daily"},
            "12024": {"name": "Patna Shatabdi", "from": "New Delhi", "to": "Patna", "time": "8h 30m", "runs": "Mon,Wed,Fri"},
            "12026": {"name": "Amritsar Shatabdi", "from": "New Delhi", "to": "Amritsar", "time": "5h 30m", "runs": "Daily"},
        },
        "Vande Bharat": {
            "22436": {"name": "Varanasi Vande Bharat", "from": "New Delhi", "to": "Varanasi", "time": "8h 0m", "runs": "Daily"},
            "22438": {"name": "Amb Andaura Vande Bharat", "from": "New Delhi", "to": "Amb Andaura", "time": "5h 10m", "runs": "Daily"},
            "20662": {"name": "Chennai Vande Bharat", "from": "MGR Chennai", "to": "Mysuru", "time": "6h 30m", "runs": "Daily"},
        },
    }

    def lookup(self, query: str) -> str:
        """Look up train information."""
        query_lower = query.lower().strip()

        # Search by train number or name
        for category, trains in self.POPULAR_TRAINS.items():
            for number, info in trains.items():
                if number in query or info["name"].lower() in query_lower:
                    return (
                        f"**{info['name']} ({number}):**\n"
                        f"  Route: {info['from']} → {info['to']}\n"
                        f"  Duration: {info['time']}\n"
                        f"  Runs: {info['runs']}\n"
                        f"  Book at: irctc.co.in"
                    )

        # List popular trains by category
        lines = [f"**Popular Indian Trains:**\n"]
        for category, trains in self.POPULAR_TRAINS.items():
            lines.append(f"\n**{category}:**")
            for number, info in trains.items():
                lines.append(f"  {number} — {info['name']} ({info['from']}→{info['to']}, {info['time']})")

        lines.append("\n**Book tickets:** irctc.co.in")
        lines.append("**Check PNR:** indianrail.gov.in/pnr")
        return "\n".join(lines)


# Singletons
petrol_service = PetrolPriceService()
lpg_service = LPGPriceService()
gold_service = GoldPriceService()
aqi_service = AQIService()
train_service = TrainLookupService()
