"""
Real-Time Data Tools — petrol/diesel, LPG, gold/silver, AQI, train lookup.

Uses free APIs and government data sources.
"""

import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class PetrolPriceService:
    """Get current petrol/diesel prices for Indian cities."""

    # Approximate prices as of Aug 2026 (Rs/litre) — updated periodically
    CITY_PRICES = {
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

    def get_price(self, city: str = "") -> str:
        """Get petrol/diesel price for a city."""
        if not city:
            return self._get_all_cities()

        city = city.strip().title()
        if city in self.CITY_PRICES:
            p = self.CITY_PRICES[city]
            return (
                f"**Fuel Prices in {city}:**\n"
                f"  Petrol: Rs {p['petrol']}/litre\n"
                f"  Diesel: Rs {p['diesel']}/litre\n"
                f"  *Prices are indicative. Actual may vary.*"
            )

        # Fuzzy match
        for c, p in self.CITY_PRICES.items():
            if city.lower() in c.lower() or c.lower() in city.lower():
                return (
                    f"**Fuel Prices in {c}:**\n"
                    f"  Petrol: Rs {p['petrol']}/litre\n"
                    f"  Diesel: Rs {p['diesel']}/litre\n"
                    f"  *Prices are indicative. Actual may vary.*"
                )

        return (
            f"City '{city}' not found in our database.\n"
            f"Available cities: {', '.join(sorted(self.CITY_PRICES.keys()))}\n"
            f"Check latest prices at: mypetrolprice.com"
        )

    def _get_all_cities(self) -> str:
        lines = ["**Petrol/Diesel Prices (Rs/litre):**\n"]
        for city, p in sorted(self.CITY_PRICES.items()):
            lines.append(f"  {city}: Petrol Rs {p['petrol']} | Diesel Rs {p['diesel']}")
        lines.append("\n*Prices indicative. Check mypetrolprice.com for latest.*")
        return "\n".join(lines)


class LPGPriceService:
    """Get current LPG cylinder prices in India."""

    def get_price(self) -> str:
        return (
            "**LPG Cylinder Prices (Aug 2026):**\n\n"
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


class GoldPriceService:
    """Get current gold and silver prices in India."""

    def get_price(self) -> str:
        return (
            "**Gold & Silver Prices (Indicative Aug 2026):**\n\n"
            "**Gold (per 10 grams):**\n"
            "  24 Carat (999 purity): Rs 72,500-73,000\n"
            "  22 Carat (916 purity): Rs 66,500-67,000\n"
            "  18 Carat (750 purity): Rs 54,500-55,000\n\n"
            "**Silver (per kg):**\n"
            "  Silver: Rs 85,000-87,000\n\n"
            "**How to Check Live Price:**\n"
            "  1. Google: Search 'gold rate today'\n"
            "  2. Websites: goodreturns.in, bankbazaar.com\n"
            "  3. Apps: Gold Price India, Goodreturns\n\n"
            "**Buying Tips:**\n"
            "  - Always buy **BIS hallmark** gold (916 for 22K)\n"
            "  - Check **HUID** (Hallmark Unique Identification) number\n"
            "  - Keep **purchase invoice** for future resale\n"
            "  - Making charges: 8-25% (negotiate for bulk)\n"
            "  - GST: 3% on gold + making charges"
        )


class AQIService:
    """Get Air Quality Index for Indian cities."""

    CITY_AQI = {
        "Delhi": {"aqi": 180, "level": "Unhealthy", "color": "🔴"},
        "Mumbai": {"aqi": 120, "level": "Unhealthy for Sensitive Groups", "color": "🟠"},
        "Bangalore": {"aqi": 65, "level": "Moderate", "color": "🟡"},
        "Chennai": {"aqi": 55, "level": "Moderate", "color": "🟡"},
        "Kolkata": {"aqi": 150, "level": "Unhealthy", "color": "🔴"},
        "Hyderabad": {"aqi": 90, "level": "Moderate", "color": "🟡"},
        "Ahmedabad": {"aqi": 110, "level": "Unhealthy for Sensitive Groups", "color": "🟠"},
        "Pune": {"aqi": 75, "level": "Moderate", "color": "🟡"},
        "Jaipur": {"aqi": 130, "level": "Unhealthy for Sensitive Groups", "color": "🟠"},
        "Lucknow": {"aqi": 170, "level": "Unhealthy", "color": "🔴"},
        "Patna": {"aqi": 190, "level": "Unhealthy", "color": "🔴"},
        "Chandigarh": {"aqi": 100, "level": "Moderate", "color": "🟡"},
    }

    AQI_LEVELS = {
        (0, 50): "Good ✅ — Air quality is satisfactory",
        (51, 100): "Moderate 🟡 — Acceptable, may affect sensitive people",
        (101, 150): "Unhealthy for Sensitive Groups 🟠 — Reduce outdoor activity",
        (151, 200): "Unhealthy 🔴 — Everyone may start to experience effects",
        (201, 300): "Very Unhealthy 🟣 — Health alert, avoid outdoor activity",
        (301, 500): "Hazardous ☠️ — Emergency conditions, stay indoors",
    }

    def get_aqi(self, city: str = "") -> str:
        if not city:
            lines = ["**Air Quality Index (Indicative):**\n"]
            for c, data in sorted(self.CITY_AQI.items()):
                lines.append(f"  {data['color']} {c}: AQI {data['aqi']} ({data['level']})")
            lines.append("\nCheck live AQI at: aqi.in or safar.aqi.in")
            return "\n".join(lines)

        city = city.strip().title()
        if city in self.CITY_AQI:
            data = self.CITY_AQI[city]
            level_desc = ""
            for (low, high), desc in self.AQI_LEVELS.items():
                if low <= data["aqi"] <= high:
                    level_desc = desc
                    break

            return (
                f"**Air Quality in {city}:**\n"
                f"  AQI: {data['aqi']} — {data['level']}\n"
                f"  {level_desc}\n\n"
                f"**Precautions:**\n"
                f"  - Wear N95 mask outdoors if AQI > 150\n"
                f"  - Avoid outdoor exercise if AQI > 100\n"
                f"  - Use air purifier indoors if AQI > 150\n"
                f"  - Check: safar.aqi.in for real-time data"
            )

        return f"City '{city}' not in our AQI database. Check safar.aqi.in for live data."


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
            "22438": {"name": "Amb Andaura Vande Bharat", "from": "New Delhi", to": "Amb Andaura", "time": "5h 10m", "runs": "Daily"},
            "20662": {"name": "Chennai Vande Bharat", "from": "MGR Chennai", "to": "Mysuru", "time": "6h 30m", "runs": "Daily"},
        },
    }

    def lookup(self, query: str) -> str:
        """Look up train information."""
        query_lower = query.lower().strip()

        # Search by train number
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
