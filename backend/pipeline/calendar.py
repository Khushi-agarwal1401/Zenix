"""
Indian Calendar Module for Zenix AI.
Provides dynamic awareness of Indian festivals, holidays, and cultural dates.
Supports Hindu Panchang approximate dates, Islamic Hijri dates, and national holidays.
Covers 2026 and 2027 with fixed national + calculated Islamic/Regional dates.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple


# ── Indian National Holidays by Year ──────────────────────────────────────────

NATIONAL_HOLIDAYS = {
    2026: {
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
        date(2026, 9, 5): {"name": "Ganesh Chaturthi", "type": "festival", "greeting_en": "Ganpati Bappa Morya! Happy Ganesh Chaturthi!", "greeting_hi": "Ganesh Chaturthi ki Shubhkamnayein! Ganpati Bappa Morya!"},
        date(2026, 10, 2): {"name": "Gandhi Jayanti", "type": "national", "greeting_en": "Remembering the Father of the Nation. Happy Gandhi Jayanti.", "greeting_hi": "Gandhi Jayanti ki Shubhkamnayein."},
        date(2026, 10, 20): {"name": "Dussehra", "type": "festival", "greeting_en": "Happy Dussehra! Victory of good over evil.", "greeting_hi": "Vijayadashami ki Hardik Shubhkamnayein! Buri par jeet ka tyohaar!"},
        date(2026, 11, 8): {"name": "Diwali", "type": "festival", "greeting_en": "Shubh Deepavali! May the festival of lights bring joy and prosperity.", "greeting_hi": "Diwali ki Hardik Shubhkamnayein! Roshni aur khushiyan aayein ghar mein!"},
        date(2026, 11, 9): {"name": "Diwali (Day 2 - Govardhan Puja)", "type": "festival", "greeting_en": "Happy Govardhan Puja!", "greeting_hi": "Govardhan Puja ki Shubhkamnayein!"},
        date(2026, 11, 10): {"name": "Bhai Dooj", "type": "festival", "greeting_en": "Happy Bhai Dooj! Celebrating sibling love.", "greeting_hi": "Bhai Dooj ki Hardik Shubhkamnayein!"},
        date(2026, 11, 24): {"name": "Guru Nanak Jayanti", "type": "festival", "greeting_en": "Happy Gurpurab! Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh!", "greeting_hi": "Guru Nanak Jayanti ki Shubhkamnayein!"},
        date(2026, 12, 25): {"name": "Christmas", "type": "festival", "greeting_en": "Merry Christmas! Joy to the world.", "greeting_hi": "Christmas ki Hardik Shubhkamnayein!"},
    },
    2027: {
        date(2027, 1, 1): {"name": "New Year's Day", "type": "observance", "greeting_en": "Happy New Year 2027!", "greeting_hi": "Naye Saal ki Hardik Shubhkamnayein!"},
        date(2027, 1, 13): {"name": "Lohri", "type": "festival", "greeting_en": "Happy Lohri! Bonfire and celebrations.", "greeting_hi": "Lohri diyan Hardik Shubhkamnayein!"},
        date(2027, 1, 14): {"name": "Makar Sankranti / Pongal", "type": "festival", "greeting_en": "Happy Makar Sankranti! Fly high with your dreams.", "greeting_hi": "Makar Sankranti ki Hardik Shubhkamnayein! Patang udao aur khush raho!"},
        date(2027, 1, 26): {"name": "Republic Day", "type": "national", "greeting_en": "Happy Republic Day! Jai Hind!", "greeting_hi": "Ganatantra Diwas ki Hardik Shubhkamnayein! Jai Hind!"},
        date(2027, 2, 21): {"name": "Holi", "type": "festival", "greeting_en": "Happy Holi! May your life be filled with colors of joy.", "greeting_hi": "Holi ki Hardik Shubhkamnayein! Rango ka tyohaar manao!"},
        date(2027, 3, 10): {"name": "Ugadi / Gudi Padwa", "type": "festival", "greeting_en": "Happy Ugadi! New beginnings await.", "greeting_hi": "Ugadi ki Shubhkamnayein!"},
        date(2027, 3, 21): {"name": "Mahavir Jayanti", "type": "festival", "greeting_en": "Happy Mahavir Jayanti! Peace and non-violence.", "greeting_hi": "Mahavir Jayanti ki Shubhkamnayein!"},
        date(2027, 3, 26): {"name": "Ram Navami", "type": "festival", "greeting_en": "Happy Ram Navami! Jai Shri Ram.", "greeting_hi": "Ram Navami ki Hardik Shubhkamnayein! Jai Shri Ram!"},
        date(2027, 4, 2): {"name": "Good Friday", "type": "festival", "greeting_en": "Blessed Good Friday.", "greeting_hi": "Good Friday ki Shubhkamnayein."},
        date(2027, 4, 14): {"name": "Dr. Ambedkar Jayanti / Baisakhi", "type": "national", "greeting_en": "Jai Bhim! Happy Baisakhi!", "greeting_hi": "Dr. Ambedkar Jayanti aur Baisakhi ki Shubhkamnayein!"},
        date(2027, 5, 1): {"name": "Maharashtra Day / Labour Day", "type": "regional", "greeting_en": "Happy Maharashtra Day! Happy Labour Day!", "greeting_hi": "Maharashtra Din ki Shubhkamnayein!"},
        date(2027, 5, 26): {"name": "Buddha Purnima", "type": "festival", "greeting_en": "Happy Buddha Purnima! May peace prevail.", "greeting_hi": "Buddha Purnima ki Shubhkamnayein!"},
        date(2027, 6, 16): {"name": "Eid ul-Adha (Bakrid)", "type": "festival", "greeting_en": "Eid Mubarak! May your sacrifices be accepted.", "greeting_hi": "Eid Mubarak! Khushiyan baato."},
        date(2027, 7, 7): {"name": "Muharram", "type": "festival", "greeting_en": "Muharram greetings. Peace be upon you.", "greeting_hi": "Muharram ki Shubhkamnayein."},
        date(2027, 8, 15): {"name": "Independence Day", "type": "national", "greeting_en": "Happy Independence Day! Jai Hind!", "greeting_hi": "Swatantrata Diwas ki Hardik Shubhkamnayein! Jai Hind!"},
        date(2027, 8, 8): {"name": "Raksha Bandhan", "type": "festival", "greeting_en": "Happy Raksha Bandhan! Celebrating sibling bonds.", "greeting_hi": "Raksha Bandhan ki Hardik Shubhkamnayein!"},
        date(2027, 8, 16): {"name": "Janmashtami", "type": "festival", "greeting_en": "Happy Janmashtami! Hare Krishna!", "greeting_hi": "Janmashtami ki Hardik Shubhkamnayein! Hare Krishna!"},
        date(2027, 8, 25): {"name": "Ganesh Chaturthi", "type": "festival", "greeting_en": "Ganpati Bappa Morya! Happy Ganesh Chaturthi!", "greeting_hi": "Ganesh Chaturthi ki Shubhkamnayein! Ganpati Bappa Morya!"},
        date(2027, 10, 2): {"name": "Gandhi Jayanti", "type": "national", "greeting_en": "Remembering the Father of the Nation. Happy Gandhi Jayanti.", "greeting_hi": "Gandhi Jayanti ki Shubhkamnayein."},
        date(2027, 10, 9): {"name": "Dussehra", "type": "festival", "greeting_en": "Happy Dussehra! Victory of good over evil.", "greeting_hi": "Vijayadashami ki Hardik Shubhkamnayein! Buri par jeet ka tyohaar!"},
        date(2027, 10, 14): {"name": "Karva Chauth", "type": "festival", "greeting_en": "Happy Karva Chauth!", "greeting_hi": "Karva Chauth ki Hardik Shubhkamnayein!"},
        date(2027, 10, 18): {"name": "Durga Puja", "type": "festival", "greeting_en": "Happy Durga Puja!", "greeting_hi": "Durga Puja ki Hardik Shubhkamnayein!"},
        date(2027, 10, 26): {"name": "Chhath Puja", "type": "festival", "greeting_en": "Happy Chhath Puja! Worshipping the Sun God.", "greeting_hi": "Chhath Puja ki Hardik Shubhkamnayein!"},
        date(2027, 11, 6): {"name": "Diwali", "type": "festival", "greeting_en": "Shubh Deepavali! May the festival of lights bring joy and prosperity.", "greeting_hi": "Diwali ki Hardik Shubhkamnayein! Roshni aur khushiyan aayein ghar mein!"},
        date(2027, 11, 7): {"name": "Govardhan Puja", "type": "festival", "greeting_en": "Happy Govardhan Puja!", "greeting_hi": "Govardhan Puja ki Shubhkamnayein!"},
        date(2027, 11, 8): {"name": "Bhai Dooj", "type": "festival", "greeting_en": "Happy Bhai Dooj! Celebrating sibling love.", "greeting_hi": "Bhai Dooj ki Hardik Shubhkamnayein!"},
        date(2027, 11, 14): {"name": "Guru Nanak Jayanti", "type": "festival", "greeting_en": "Happy Gurpurab! Waheguru Ji Ka Khalsa, Waheguru Ji Ki Fateh!", "greeting_hi": "Guru Nanak Jayanti ki Shubhkamnayein!"},
        date(2027, 12, 25): {"name": "Christmas", "type": "festival", "greeting_en": "Merry Christmas! Joy to the world.", "greeting_hi": "Christmas ki Hardik Shubhkamnayein!"},
    },
}

# ── Islamic Calendar (Hijri) Approximate Dates ───────────────────────────────
# Islamic calendar is lunar, so dates shift ~11 days earlier each Gregorian year

ISLAMIC_EVENTS = {
    2026: {
        "Eid ul-Fitr": {"approx_date": date(2026, 3, 20), "greeting": "Eid Mubarak! Ramadan Mubarak ke baad khushiyan aayein."},
        "Eid ul-Adha": {"approx_date": date(2026, 5, 27), "greeting": "Eid Mubarak! sacrifice aur devotion ka tyohaar."},
        "Muharram": {"approx_date": date(2026, 6, 17), "greeting": "Muharram Mubarak."},
        "Milad-un-Nabi": {"approx_date": date(2026, 8, 26), "greeting": "Milad-un-Nabi Mubarak!"},
    },
    2027: {
        "Eid ul-Fitr": {"approx_date": date(2027, 3, 9), "greeting": "Eid Mubarak! Ramadan Mubarak ke baad khushiyan aayein."},
        "Eid ul-Adha": {"approx_date": date(2027, 5, 16), "greeting": "Eid Mubarak! sacrifice aur devotion ka tyohaar."},
        "Muharram": {"approx_date": date(2027, 6, 7), "greeting": "Muharram Mubarak."},
        "Milad-un-Nabi": {"approx_date": date(2027, 8, 16), "greeting": "Milad-un-Nabi Mubarak!"},
    },
}

# ── Regional / Sikh Events ───────────────────────────────────────────────────

REGIONAL_EVENTS = {
    2026: {
        "Lohri": date(2026, 1, 13),
        "Baisakhi": date(2026, 4, 14),
        "Onam": date(2026, 8, 26),
        "Pongal": date(2026, 1, 14),
        "Navratri Start": date(2026, 10, 11),
        "Durga Puja": date(2026, 10, 18),
        "Karva Chauth": date(2026, 10, 15),
        "Chhath Puja": date(2026, 10, 26),
    },
    2027: {
        "Lohri": date(2027, 1, 13),
        "Baisakhi": date(2027, 4, 14),
        "Onam": date(2027, 8, 15),
        "Pongal": date(2027, 1, 14),
        "Navratri Start": date(2027, 9, 30),
        "Durga Puja": date(2027, 10, 7),
        "Karva Chauth": date(2027, 10, 4),
        "Chhath Puja": date(2027, 10, 15),
    },
}

# ── Sikh Nanakshahi Calendar (approximate Gurpurabs) ─────────────────────────

SIKH_EVENTS = {
    2026: {
        "Guru Gobind Singh Jayanti": date(2026, 1, 5),
        "Baisakhi (Sikh New Year)": date(2026, 4, 14),
        "Guru Arjan Dev Martyrdom": date(2026, 6, 1),
        "Guru Nanak Jayanti": date(2026, 11, 24),
    },
    2027: {
        "Guru Gobind Singh Jayanti": date(2027, 1, 5),
        "Baisakhi (Sikh New Year)": date(2027, 4, 14),
        "Guru Arjan Dev Martyrdom": date(2027, 6, 1),
        "Guru Nanak Jayanti": date(2027, 11, 14),
    },
}

# ── Jain Calendar (approximate) ───────────────────────────────────────────────

JAIN_EVENTS = {
    2026: {
        "Mahavir Jayanti": date(2026, 3, 31),
        "Paryushan": date(2026, 8, 22),
        "Diwali (Jain New Year)": date(2026, 11, 8),
    },
    2027: {
        "Mahavir Jayanti": date(2027, 3, 21),
        "Paryushan": date(2027, 8, 11),
        "Diwali (Jain New Year)": date(2027, 11, 6),
    },
}


def _get_all_events_for_date(check_date: date) -> List[Dict]:
    """Gather all events (national, Islamic, regional, Sikh, Jain) for a given date."""
    events = []
    year = check_date.year

    # National holidays
    national = NATIONAL_HOLIDAYS.get(year, {}).get(check_date)
    if national:
        events.append({"name": national["name"], "type": national["type"], "source": "national"})

    # Regional events
    for name, fdate in REGIONAL_EVENTS.get(year, {}).items():
        if fdate == check_date:
            events.append({"name": name, "type": "regional", "source": "regional"})

    # Islamic events (1-day tolerance for moon sighting)
    for name, edata in ISLAMIC_EVENTS.get(year, {}).items():
        approx = edata["approx_date"]
        if abs((approx - check_date).days) <= 1:
            events.append({"name": name, "type": "festival", "source": "islamic"})

    # Sikh events
    for name, fdate in SIKH_EVENTS.get(year, {}).items():
        if fdate == check_date:
            events.append({"name": name, "type": "festival", "source": "sikh"})

    # Jain events
    for name, fdate in JAIN_EVENTS.get(year, {}).items():
        if fdate == check_date:
            events.append({"name": name, "type": "festival", "source": "jain"})

    return events


class IndianCalendar:
    """
    Provides dynamic awareness of Indian festivals, holidays, and cultural events.
    Supports 2026 and 2027 with fallback for unsupported years.
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
            "year_supported": self.today.year in NATIONAL_HOLIDAYS,
        }

        events = _get_all_events_for_date(self.today)
        if events:
            info["festivals_today"] = [e["name"] for e in events]
            national = next((e for e in events if e["source"] == "national"), None)
            if national:
                info["is_gazetted_holiday"] = True
            # Get greeting from national holidays
            holiday = NATIONAL_HOLIDAYS.get(self.today.year, {}).get(self.today)
            if holiday:
                info["greeting"] = holiday.get("greeting_hi") or holiday.get("greeting_en")
            else:
                # Try Islamic greeting
                for name, edata in ISLAMIC_EVENTS.get(self.today.year, {}).items():
                    if abs((edata["approx_date"] - self.today).days) <= 1:
                        info["greeting"] = edata["greeting"]
                        break

        info["upcoming_festival"] = self._get_next_festival()
        return info

    def _get_next_festival(self) -> Optional[Dict]:
        """Find the next upcoming festival from all sources."""
        upcoming = []
        year = self.today.year

        # National festival holidays
        for fdate, fdata in NATIONAL_HOLIDAYS.get(year, {}).items():
            if fdate > self.today and fdata["type"] == "festival":
                days_until = (fdate - self.today).days
                upcoming.append({
                    "name": fdata["name"],
                    "date": fdate.isoformat(),
                    "days_until": days_until,
                    "greeting": fdata.get("greeting_hi") or fdata.get("greeting_en"),
                })

        # Regional events
        for name, fdate in REGIONAL_EVENTS.get(year, {}).items():
            if fdate > self.today:
                days_until = (fdate - self.today).days
                upcoming.append({
                    "name": name,
                    "date": fdate.isoformat(),
                    "days_until": days_until,
                })

        # Sikh events
        for name, fdate in SIKH_EVENTS.get(year, {}).items():
            if fdate > self.today:
                days_until = (fdate - self.today).days
                upcoming.append({
                    "name": name,
                    "date": fdate.isoformat(),
                    "days_until": days_until,
                })

        # Jain events
        for name, fdate in JAIN_EVENTS.get(year, {}).items():
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

    def get_holiday_calendar(self, month: int = None, year: int = None) -> List[Dict]:
        """Get holidays for a specific month or entire year."""
        year = year or self.today.year
        holidays = []

        for fdate, fdata in sorted(NATIONAL_HOLIDAYS.get(year, {}).items()):
            if month and fdate.month != month:
                continue
            holidays.append({
                "date": fdate.isoformat(),
                "day": fdate.strftime("%A"),
                "name": fdata["name"],
                "type": fdata["type"],
            })

        # Add regional events
        for name, fdate in REGIONAL_EVENTS.get(year, {}).items():
            if month and fdate.month != month:
                continue
            holidays.append({
                "date": fdate.isoformat(),
                "day": fdate.strftime("%A"),
                "name": name,
                "type": "regional",
            })

        # Add Sikh events
        for name, fdate in SIKH_EVENTS.get(year, {}).items():
            if month and fdate.month != month:
                continue
            holidays.append({
                "date": fdate.isoformat(),
                "day": fdate.strftime("%A"),
                "name": name,
                "type": "sikh",
            })

        # Add Jain events
        for name, fdate in JAIN_EVENTS.get(year, {}).items():
            if month and fdate.month != month:
                continue
            holidays.append({
                "date": fdate.isoformat(),
                "day": fdate.strftime("%A"),
                "name": name,
                "type": "jain",
            })

        holidays.sort(key=lambda x: x["date"])
        return holidays

    def check_if_holiday(self, check_date: date = None) -> Dict:
        """Check if a specific date is a holiday."""
        check_date = check_date or self.today

        events = _get_all_events_for_date(check_date)

        return {
            "date": check_date.isoformat(),
            "is_holiday": bool(events),
            "events": events,
            "banks_closed": bool(events) or check_date.weekday() == 6,
        }

    def format_calendar_response(self, persona: str = "desi") -> str:
        """Format a natural language calendar response for today."""
        info = self.get_today_info()

        if persona == "desi":
            lines = [f"\ud83d\udcc5 Aaj hai {info['day_of_week']}, {self.today.strftime('%d %B %Y')}"]
        else:
            lines = [f"Today is {info['day_of_week']}, {self.today.strftime('%d %B %Y')}"]

        if not info["year_supported"]:
            lines.append(f"\u26a0\ufe0f Calendar data for {self.today.year} is approximate.")

        if info["festivals_today"]:
            festival_str = " aur ".join(info["festivals_today"])
            lines.append(f"\n\ud83c\udf89 Aaj ka tyohaar: {festival_str}")
            if info["greeting"]:
                lines.append(f"\ud83d\ude4f {info['greeting']}")

        if info["upcoming_festival"]:
            uf = info["upcoming_festival"]
            days = uf["days_until"]
            if persona == "desi":
                lines.append(f"\n\u23ed\ufe0f Agla tyohaar: {uf['name']} ({days} din baad)")
            else:
                lines.append(f"\nNext festival: {uf['name']} (in {days} days)")

        if info["is_gazetted_holiday"]:
            lines.append("\n\ud83c\udfdb\ufe0f Aaj gazetted holiday hai \u2014 banks aur sarkari daftar band honge.")

        return "\n".join(lines)


# ── Module-level singleton ─────────────────────────────────────────────────────

indian_calendar = IndianCalendar()


def get_calendar_response(persona: str = "desi") -> str:
    """Convenience function for getting calendar info."""
    return indian_calendar.format_calendar_response(persona)


def get_festival_greeting() -> Optional[str]:
    """Get today's festival greeting if applicable."""
    return indian_calendar.get_festival_greeting()
