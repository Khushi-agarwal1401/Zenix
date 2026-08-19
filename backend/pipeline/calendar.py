"""
Indian Calendar Module for Zenix AI.
Provides dynamic awareness of Indian festivals, holidays, and cultural dates.
Supports Hindu Panchang approximate dates, Islamic Hijri dates, and national holidays.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple


# ── Indian National Holidays 2026 (Gazetted) ──────────────────────────────────
# These are fixed-date or calculated holidays

NATIONAL_HOLIDAYS_2026 = {
    date(2026, 1, 1): {"name": "New Year's Day", "type": "observance", "greeting_en": "Happy New Year!", "greeting_hi": "Naye Saal ki Hardik Shubhkamnayein!"},
    date(2026, 1, 14): {"name": "Makar Sankranti / Pongal", "type": "festival", "greeting_en": "Happy Makar Sankranti! Fly high with your dreams.", "greeting_hi": "Makar Sankranti ki Hardik Shubhkamnayein! Patang udao aur khush raho!"},
    date(2026, 1, 26): {"name": "Republic Day", "type": "national", "greeting_en": "Happy Republic Day! Jai Hind!", "greeting_hi": "Ganatantra Diwas ki Hardik Shubhkamnayein! Jai Hind!"},
    date(2026, 3, 4): {"name": "Holi", "type": "festival", "greeting_en": "Happy Holi! May your life be filled with colors of joy.", "greeting_hi": "Holi ki Hardik Shubhkamnayein! Rango ka tyohaar manao!"},
    date(2026, 3, 20): {"name": "Ugadi / Gudi Padwa", "type": "festival", "greeting_en": "Happy Ugadi! New beginnings await.", "greeting_hi": "Ugadi ki Shubhkamnayein!"},
    date(2026, 3, 31): {"name": "Mahavir Jayanti", "type": "festival", "greeting_en": "Happy Mahavir Jayanti! Peace and non-violence.", "greeting_hi": "Mahavir Jayanti ki Shubhkamnayein!"},
    date(2026, 4, 2): {"name": "Ram Navami", "type": "festival", "greeting_en": "Happy Ram Navami! Jai Shri Ram.", "greeting_hi": "Ram Navami ki Hardik Shubhkamnayein! Jai Shri Ram!"},
    date(2026, 4, 3): {"name": "Good Friday", "type": "festival", "greeting_en": "Blessed Good Friday.", "greeting_hi": "Good Friday ki Shubhkamnayein."},
    date(2026, 4, 14): {"name": "Dr. Ambedkar Jayanti", "type": "national", "greeting_en": "Jai Bhim! Honoring Dr. B.R. Ambedkar.", "greeting_hi": "Dr. Ambedkar Jayanti ki Shubhkamnayein! Jai Bhim!"},
    date(2026, 5, 1): {"name": "Maharashtra Day / Labour Day", "type": "regional", "greeting_en": "Happy Maharashtra Day! Happy Labour Day!", "greeting_hi": "Maharashtra Din ki Shubhkamnayein!"},
    date(2026, 5, 7): {"name": "Buddha Purnima", "type": "festival", "greeting_en": "Happy Buddha Purnima! May peace prevail.", "greeting_hi": "Buddha Purnima ki Shubhkamnayein!"},
    date(2026, 6, 27): {"name": "Eid ul-Adha (Bakrid)", "type": "festival", "greeting_en": "Eid Mubarak! May your sacrifices be accepted.", "greeting_hi": "Eid Mubarak! Khushiyan baato."},
    date(2026, 7, 17): {"name": "Muharram", "type": "festival", "greeting_en": "Muharram greetings. Peace be upon you.", "greeting_hi": "Muharram ki Shubhkamnayein."},
    date(2026, 8, 15): {"name": "Independence Day", "type": "national", "greeting_en": "Happy Independence Day! Jai Hind!", "greeting_hi": "Swatantrata Diwas ki Hardik Shubhkamnayein! Jai Hind!"},
    date(2026, 8, 19): {"name": "Raksha Bandhan", "type": "festival", "greeting_en": "Happy Raksha Bandhan! Celebrating sibling bonds.", "greeting_hi": "Raksha Bandhan ki Hardik Shubhkamnayein!"},
    date(2026, 8, 27): {"name": "Janmashtami", "type": "festival", "greeting_en": "Happy Janmashtami! Hare Krishna!", "greeting_hi": "Janmashtami ki Hardik Shubhkamnayein! Hare Krishna!"},
    date(2026, 9, 5): {"name": "Ganesh Chaturthi", "type": "festival", "greeting_en": "Ganpati Bappa Morya! Happy Ganesh Chaturthi!", "greeting_hi": "Ganesh Chaturthi ki Hardik Shubhkamnayein! Ganpati Bappa Morya!"},
    date(2026, 10, 2): {"name": "Gandhi Jayanti", "type": "national", "greeting_en": "Remembering the Father of the Nation. Happy Gandhi Jayanti.", "greeting_hi": "Gandhi Jayanti ki Shubhkamnayein."},
    date(2026, 10, 20): {"name": "Dussehra", "type": "festival", "greeting_en": "Happy Dussehra! Victory of good over evil.", "greeting_hi": "Vijayadashami ki Hardik Shubhkamnayein! Buri par jeet ka tyohaar!"},
    date(2026, 11, 8): {"name": "Diwali", "type": "festival", "greeting_en": "Shubh Deepavali! May the festival of lights bring joy and prosperity.", "greeting_hi": "Diwali ki Hardik Shubhkamnayein! Roshni aur khushiyan aayein ghar mein!"},
    date(2026, 11, 9): {"name": "Diwali (Day 2 - Govardhan Puja)", "type": "festival", "greeting_en": "Happy Govardhan Puja!", "greeting_hi": "Govardhan Puja ki Shubhkamnayein!"},
    date(2026, 11, 10): {"name": "Bhai Dooj", "type": "festival", "greeting_en": "Happy Bhai Dooj! Celebrating sibling love.", "greeting_hi": "Bhai Dooj ki Hardik Shubhkamnayein!"},
    date(2026, 11, 24): {"name": "Guru Nanak Jayanti", "type": "festival", "greeting_en": "Happy Gurpurab! Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh!", "greeting_hi": "Guru Nanak Jayanti ki Shubhkamnayein!"},
    date(2026, 12, 25): {"name": "Christmas", "type": "festival", "greeting_en": "Merry Christmas! Joy to the world.", "greeting_hi": "Christmas ki Hardik Shubhkamnayein!"},
}

# ── Islamic Calendar (Hijri) Approximate Dates for 2026 ────────────────────────
# Note: Islamic calendar is lunar, so dates shift ~11 days earlier each Gregorian year

ISLAMIC_EVENTS_2026 = {
    # Approximate dates (may vary by 1-2 days based on moon sighting)
    "Eid ul-Fitr": {"approx_date": date(2026, 3, 20), "greeting": "Eid Mubarak! Ramadan Mubarak ke baad khushiyan aayein."},
    "Eid ul-Adha": {"approx_date": date(2026, 5, 27), "greeting": "Eid Mubarak! sacrifice aur devotion ka tyohaar."},
    "Muharram": {"approx_date": date(2026, 6, 17), "greeting": "Muharram Mubarak."},
    "Milad-un-Nabi": {"approx_date": date(2026, 8, 26), "greeting": "Milad-un-Nabi Mubarak!"},
}

# ── Sikh / Regional Events ─────────────────────────────────────────────────────

REGIONAL_EVENTS = {
    "Lohri": date(2026, 1, 13),
    "Baisakhi": date(2026, 4, 14),
    "Onam": date(2026, 8, 26),
    "Pongal": date(2026, 1, 14),
    "Navratri Start": date(2026, 10, 11),
    "Durga Puja": date(2026, 10, 18),
    "Karva Chauth": date(2026, 10, 15),
    "Chhath Puja": date(2026, 10, 26),
}


class IndianCalendar:
    """
    Provides dynamic awareness of Indian festivals, holidays, and cultural events.
    """

    def __init__(self):
        self.today = date.today()

    def get_today_info(self) -> Dict:
        """Get comprehensive info about today."""
        info = {
            "date": self.today.isoformat(),
            "day_of_week": self.today.strftime("%A"),
            "day_of_year": self.today.timetuple().tm_yday,
            "is_gazetted_holiday": False,
            "festivals_today": [],
            "greeting": None,
            "upcoming_festival": None,
        }

        # Check national holidays
        holiday = NATIONAL_HOLIDAYS_2026.get(self.today)
        if holiday:
            info["is_gazetted_holiday"] = True
            info["festivals_today"].append(holiday["name"])
            info["greeting"] = holiday.get("greeting_hi") or holiday.get("greeting_en")

        # Check regional events
        for name, fdate in REGIONAL_EVENTS.items():
            if fdate == self.today:
                info["festivals_today"].append(name)

        # Check Islamic events
        for name, edata in ISLAMIC_EVENTS_2026.items():
            approx = edata["approx_date"]
            if abs((approx - self.today).days) <= 1:
                info["festivals_today"].append(name)
                info["greeting"] = edata["greeting"]

        # Find next upcoming festival
        info["upcoming_festival"] = self._get_next_festival()

        return info

    def _get_next_festival(self) -> Optional[Dict]:
        """Find the next upcoming festival."""
        upcoming = []
        for fdate, fdata in sorted(NATIONAL_HOLIDAYS_2026.items()):
            if fdate > self.today and fdata["type"] == "festival":
                days_until = (fdate - self.today).days
                upcoming.append({
                    "name": fdata["name"],
                    "date": fdate.isoformat(),
                    "days_until": days_until,
                    "greeting": fdata.get("greeting_hi") or fdata.get("greeting_en"),
                })

        for name, fdate in REGIONAL_EVENTS.items():
            if fdate > self.today:
                days_until = (fdate - self.today).days
                upcoming.append({
                    "name": name,
                    "date": fdate.isoformat(),
                    "days_until": days_until,
                })

        upcoming.sort(key=lambda x: x["days_until"])
        return upcoming[0] if upcoming else None

    def get_festival_greeting(self) -> Optional[str]:
        """Get a greeting if today is a festival."""
        info = self.get_today_info()
        return info.get("greeting")

    def get_holiday_calendar(self, month: int = None, year: int = 2026) -> List[Dict]:
        """Get holidays for a specific month or entire year."""
        holidays = []
        for fdate, fdata in sorted(NATIONAL_HOLIDAYS_2026.items()):
            if month and fdate.month != month:
                continue
            if fdate.year == year:
                holidays.append({
                    "date": fdate.isoformat(),
                    "day": fdate.strftime("%A"),
                    "name": fdata["name"],
                    "type": fdata["type"],
                })
        return holidays

    def check_if_holiday(self, check_date: date = None) -> Dict:
        """Check if a specific date is a holiday."""
        check_date = check_date or self.today
        holiday = NATIONAL_HOLIDAYS_2026.get(check_date)

        # Check regional
        regional = [name for name, fdate in REGIONAL_EVENTS.items() if fdate == check_date]

        # Check Islamic (approximate)
        islamic = []
        for name, edata in ISLAMIC_EVENTS_2026.items():
            if abs((edata["approx_date"] - check_date).days) <= 1:
                islamic.append(name)

        return {
            "date": check_date.isoformat(),
            "is_holiday": bool(holiday) or bool(regional) or bool(islamic),
            "national_holiday": holiday["name"] if holiday else None,
            "regional_events": regional,
            "islamic_events": islamic,
            "banks_closed": bool(holiday) or check_date.weekday() == 6,  # Sundays
        }

    def format_calendar_response(self, persona: str = "desi") -> str:
        """Format a natural language calendar response for today."""
        info = self.get_today_info()

        if persona == "desi":
            lines = [f"📅 Aaj hai {info['day_of_week']}, {self.today.strftime('%d %B %Y')}"]
        else:
            lines = [f"Today is {info['day_of_week']}, {self.today.strftime('%d %B %Y')}"]

        if info["festivals_today"]:
            festival_str = " aur ".join(info["festivals_today"])
            lines.append(f"\n🎉 Aaj ka tyohaar: {festival_str}")
            if info["greeting"]:
                lines.append(f"🙏 {info['greeting']}")

        if info["upcoming_festival"]:
            uf = info["upcoming_festival"]
            days = uf["days_until"]
            if persona == "desi":
                lines.append(f"\n⏭️ Agla tyohaar: {uf['name']} ({days} din baad)")
            else:
                lines.append(f"\nNext festival: {uf['name']} (in {days} days)")

        if info["is_gazetted_holiday"]:
            lines.append("\n🏛️ Aaj gazetted holiday hai — banks aur sarkari daftar band honge.")

        return "\n".join(lines)


# ── Module-level singleton ─────────────────────────────────────────────────────

indian_calendar = IndianCalendar()


def get_calendar_response(persona: str = "desi") -> str:
    """Convenience function for getting calendar info."""
    return indian_calendar.format_calendar_response(persona)


def get_festival_greeting() -> Optional[str]:
    """Get today's festival greeting if applicable."""
    return indian_calendar.get_festival_greeting()
