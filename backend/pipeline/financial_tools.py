"""
SIP Calculator & Crop Advisory — financial and agricultural tools.
"""

import math
from typing import Dict, Any, List


class SIPCalculator:
    """Calculate SIP returns and compare investment options."""

    def calculate_sip(self, monthly_amount: float, years: int, expected_return: float) -> Dict[str, Any]:
        """Calculate SIP maturity value."""
        months = years * 12
        monthly_rate = expected_return / 100 / 12

        if monthly_rate == 0:
            maturity = monthly_amount * months
        else:
            maturity = monthly_amount * ((1 + monthly_rate) ** months - 1) / monthly_rate * (1 + monthly_rate)

        invested = monthly_amount * months
        wealth_gained = maturity - invested

        return {
            "monthly_investment": monthly_amount,
            "years": years,
            "expected_return": expected_return,
            "total_invested": round(invested, 2),
            "maturity_value": round(maturity, 2),
            "wealth_gained": round(wealth_gained, 2),
            "return_percentage": round(wealth_gained / invested * 100, 2) if invested else 0,
        }

    def compare_funds(self, monthly: float, years: int) -> List[Dict]:
        """Compare SIP across different fund types."""
        returns = {
            "PPF (7.1%)": 7.1,
            "FD (6.5%)": 6.5,
            "Debt Fund (7%)": 7.0,
            "Hybrid Fund (10%)": 10.0,
            "Large Cap (12%)": 12.0,
            "Index Fund (12%)": 12.0,
            "Mid Cap (15%)": 15.0,
            "ELSS (14%)": 14.0,
        }
        results = []
        for name, rate in returns.items():
            calc = self.calculate_sip(monthly, years, rate)
            results.append({"fund": name, **calc})
        return results

    def required_sip(self, target: float, years: int, expected_return: float) -> float:
        """Calculate monthly SIP needed to reach a target amount."""
        months = years * 12
        monthly_rate = expected_return / 100 / 12

        if monthly_rate == 0:
            return target / months

        required = target * monthly_rate / ((1 + monthly_rate) ** months - 1) / (1 + monthly_rate)
        return round(required, 2)


class CropAdvisory:
    """Weather-based crop advisories for Indian farmers."""

    CROP_SEASONS = {
        "kharif": {
            "months": "June-October",
            "crops": ["Rice", "Maize", "Cotton", "Soybean", "Sugarcane", "Groundnut", "Bajra", "Jowar"],
            "sowing": "June-July",
            "harvesting": "September-November",
        },
        "rabi": {
            "months": "October-March",
            "crops": ["Wheat", "Mustard", "Gram", "Peas", "Barley", "Rapeseed", "Potato"],
            "sowing": "October-December",
            "harvesting": "March-April",
        },
        "zaid": {
            "months": "March-June",
            "crops": ["Watermelon", "Cucumber", "Fodder", "Muskmelon"],
            "sowing": "March-April",
            "harvesting": "June-July",
        },
    }

    def get_season_advisory(self, month: int) -> Dict[str, Any]:
        """Get crop advisory based on current month."""
        if month in range(6, 11):
            season = "kharif"
        elif month in [10, 11, 12, 1, 2, 3]:
            season = "rabi"
        else:
            season = "zaid"

        info = self.CROP_SEASONS[season]
        return {
            "current_season": season.title(),
            "months": info["months"],
            "crops": info["crops"],
            "sowing_time": info["sowing"],
            "harvesting_time": info["harvesting"],
            "advice": self._get_weather_advice(season, month),
        }

    def _get_weather_advice(self, season: str, month: int) -> str:
        if season == "kharif":
            if month == 6:
                return "Prepare fields for sowing. Ensure water availability. Apply basal fertilizers."
            elif month == 7:
                return "Transplanting season. Maintain water levels in paddy fields. Watch for pests."
            elif month in [8, 9]:
                return "Growth season. Monitor for pest attacks. Apply top-dress fertilizers."
            elif month == 10:
                return "Harvesting time. Dry crops properly before storage. Sell at MSP centers."
        elif season == "rabi":
            if month in [10, 11]:
                return "Prepare fields for Rabi sowing. Apply well-decomposed FYM. Ensure irrigation."
            elif month in [12, 1]:
                return "Peak growing season. Apply second dose of nitrogen. Monitor for rust disease."
            elif month in [2, 3]:
                return "Harvesting approaching. Reduce irrigation. Monitor moisture content."
        else:
            if month in [3, 4]:
                return "Zaid season. Sow summer crops. Ensure irrigation facilities."
            elif month in [5, 6]:
                return "Harvest summer crops. Prepare for Kharif season."
        return "Consult local Krishi Vigyan Kendra for specific advisories."

    def get_mandi_prices(self, crop: str = "") -> str:
        """Get approximate mandi prices (static reference data)."""
        # Static reference prices (Rs/quintal) - approximate 2025-26 MSP
        prices = {
            "Paddy": "2,320", "Wheat": "2,425", "Maize": "2,220",
            "Cotton": "7,121", "Soybean": "4,892", "Groundnut": "6,267",
            "Mustard": "5,650", "Gram": "5,440", "Sugarcane": "315",
            "Potato": "1,200", "Onion": "1,200", "Tomato": "1,500",
        }
        if crop and crop.title() in prices:
            return f"MSP for {crop.title()}: Rs {prices[crop.title()]}/quintal (approximate 2025-26)"

        lines = ["**Approximate MSP Prices (Rs/quintal):**\n"]
        for name, price in prices.items():
            lines.append(f"  🌾 {name}: Rs {price}")
        lines.append("\n*Note: Actual mandi prices vary by location and quality. Check enam.gov.in for real-time prices.*")
        return "\n".join(lines)


# Singletons
sip_calculator = SIPCalculator()
crop_advisory = CropAdvisory()
