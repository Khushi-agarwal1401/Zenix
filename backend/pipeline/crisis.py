"""
Crisis Detection & Emergency Response — safety-critical module.

Detects crisis situations and provides:
- Immediate helpline numbers
- Empathetic, culturally appropriate responses
- De-escalation guidance
- Emergency resource links
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Crisis Patterns ─────────────────────────────────────────────────────────

CRISIS_PATTERNS = {
    "suicide": {
        "patterns": [
            r"\b(want to die|want to kill myself|end my life|suicide|kill myself)\b",
            r"\b(no reason to live|better off dead|end it all|cant go on)\b",
            r"\b(mar jaunga|mar jaungi|jeena nahi chahta|zindagi khatam)\b",
            r"\b(jaan de dunga|aatmhatya|khudkushi)\b",
            r"\b(wish i was dead|life is meaningless|give up on life)\b",
            r"\b(overdose|slit my wrists|jump off|hanging)\b",
        ],
        "severity": "critical",
        "helplines": [
            {"name": "Vandrevala Foundation", "number": "1860-2662-345", "hours": "24/7"},
            {"name": "iCall", "number": "9152987821", "hours": "Mon-Sat 8am-10pm"},
            {"name": "AASRA", "number": "9820466726", "hours": "24/7"},
            {"name": "Snehi", "number": "044-24640050", "hours": "24/7"},
            {"name": "Connecting Trust", "number": "022-25460052", "hours": "24/7"},
        ],
        "response": (
            "I hear you, and I want you to know that what you're feeling right now matters. "
            "You are not alone in this.\n\n"
            "**Please reach out to someone who can help right now:**\n"
            "📞 **Vandrevala Foundation:** 1860-2662-345 (24/7)\n"
            "📞 **AASRA:** 9820466726 (24/7)\n"
            "📞 **iCall:** 9152987821\n\n"
            "These are free, confidential, and available in Hindi and English. "
            "They are trained to listen without judgment.\n\n"
            "Your life has value. This feeling is temporary, but help is available right now. "
            "Please make that call. 🙏"
        ),
    },
    "depression": {
        "patterns": [
            r"\b(depressed|depression|hopeless|empty inside|no energy|cant sleep)\b",
            r"\b(always sad|never happy|worthless|useless|burden)\b",
            r"\b(motivation nahi hai|udaas hu|zaroorat nahi|akela feel)\b",
            r"\b(bore ho gaya hu|jee nahi raha|thak gaya hu)\b",
        ],
        "severity": "high",
        "helplines": [
            {"name": "Vandrevala Foundation", "number": "1860-2662-345", "hours": "24/7"},
            {"name": "iCall", "number": "9152987821", "hours": "Mon-Sat 8am-10pm"},
            {"name": "NIMHANS", "number": "080-46110007", "hours": "24/7"},
        ],
        "response": (
            "I'm sorry you're going through this. Feeling this way takes courage to share, "
            "and I want you to know that help is available.\n\n"
            "**You don't have to face this alone:**\n"
            "📞 **Vandrevala Foundation:** 1860-2662-345 (24/7, Hindi/English)\n"
            "📞 **NIMHANS Helpline:** 080-46110007 (24/7)\n"
            "📞 **iCall:** 9152987821\n\n"
            "These are trained counselors who understand what you're going through. "
            "Talking to someone can make a real difference.\n\n"
            "Small steps matter: Try going for a short walk, talking to a friend, or "
            "writing down how you feel. You're not alone in this. 💙"
        ),
    },
    "domestic_violence": {
        "patterns": [
            r"\b(husband hits me|wife beats me|domestic violence|beating me)\b",
            r"\b(ghar pe maar peet|pati maar raha hai|patni maar rahi hai)\b",
            r"\b(hits me|beats me|abuses me physically|throws things)\b",
            r"\b(scared at home|afraid of spouse|threatening me|abusive relationship)\b",
            r"\b(dowry harassment|dowry demands|saas satati hai)\b",
        ],
        "severity": "critical",
        "helplines": [
            {"name": "Women Helpline", "number": "181", "hours": "24/7"},
            {"name": "Police Emergency", "number": "100", "hours": "24/7"},
            {"name": "NCW (National Commission for Women)", "number": "7827-170-170", "hours": "24/7"},
            {"name": "Childline (if children involved)", "number": "1098", "hours": "24/7"},
        ],
        "response": (
            "**You deserve to be safe.** What you're experiencing is not okay, and it's not your fault.\n\n"
            "**Immediate help available:**\n"
            "📞 **Women Helpline:** 181 (24/7, free)\n"
            "📞 **Police:** 100 (for immediate danger)\n"
            "📞 **NCW:** 7827-170-170\n\n"
            "**What you can do:**\n"
            "1. If you're in immediate danger, please call **100** right now\n"
            "2. Contact **181** — they can guide you to the nearest shelter\n"
            "3. You can file an FIR at any police station — **Zero FIR** means you can file anywhere\n"
            "4. The **Protection of Women from Domestic Violence Act, 2005** protects you\n"
            "5. You can get a **protection order** within 72 hours\n\n"
            "Your safety comes first. Please reach out. You are not alone. 🙏"
        ),
    },
    "child_abuse": {
        "patterns": [
            r"\b(abusing me|i am being abused|touching me inappropriately)\b",
            r"\b(molestation|molesting me|sexual abuse|harassing me)\b",
            r"\b(uncle touches|teacher touches|someone touches|groping)\b",
            r"\b(bacche ko maar raha|bacche ko chhu raha|bal atyachar)\b",
        ],
        "severity": "critical",
        "helplines": [
            {"name": "Childline India", "number": "1098", "hours": "24/7"},
            {"name": "Police Emergency", "number": "100", "hours": "24/7"},
            {"name": "POCSO Helpline", "number": "1800-11-0031", "hours": "24/7"},
        ],
        "response": (
            "**What is happening to you is wrong, and it is NOT your fault.**\n\n"
            "**Please tell a trusted adult right now — a teacher, parent, or anyone you trust.**\n\n"
            "**Help is available:**\n"
            "📞 **Childline:** 1098 (24/7, free, confidential)\n"
            "📞 **Police:** 100 (for immediate safety)\n"
            "📞 **POCSO Helpline:** 1800-11-0031\n\n"
            "**You have the right to be safe.** The **POCSO Act** protects children from "
            "sexual abuse, and offenders face strict punishment.\n\n"
            "Please make that call to **1098**. They are trained to help children just like you. 🙏"
        ),
    },
    "disaster_flood": {
        "patterns": [
            r"\b(flood|badh|paani badh gaya|drowning|submerged)\b",
            r"\b(water everywhere|house is flooding| trapped in water)\b",
            r"\b(flood aaya|paani ghar mein|baarish se tabaahi)\b",
        ],
        "severity": "high",
        "helplines": [
            {"name": "National Disaster Helpline", "number": "1070", "hours": "24/7"},
            {"name": "NDRF", "number": "011-24363260", "hours": "24/7"},
            {"name": "Police Emergency", "number": "100", "hours": "24/7"},
        ],
        "response": (
            "**Flood Emergency — Please stay safe:**\n\n"
            "📞 **National Disaster Helpline:** 1070\n"
            "📞 **NDRF (rescue):** 011-24363260\n"
            "📞 **Police:** 100\n\n"
            "**Immediate safety steps:**\n"
            "1. Move to **higher ground** immediately — upper floors, rooftops\n"
            "2. **Don't walk or drive through flood water** — even shallow water can be dangerous\n"
            "3. **Turn off electricity** at the main switch if water is rising\n"
            "4. Keep your **phone charged** and stay reachable\n"
            "5. If trapped, **call 100 or 1070** and share your exact location\n"
            "6. **Don't touch electrical equipment** if you're wet or standing in water\n\n"
            "Stay calm and stay safe. Help is on the way. 🙏"
        ),
    },
    "disaster_earthquake": {
        "patterns": [
            r"\b(earthquake|bhukamp|earthquake aaya|ground shaking)\b",
            r"\b(jhatka laga|zameen hili|quake|seismic)\b",
        ],
        "severity": "high",
        "helplines": [
            {"name": "National Disaster Helpline", "number": "1070", "hours": "24/7"},
            {"name": "Police Emergency", "number": "100", "hours": "24/7"},
            {"name": "NDRF", "number": "011-24363260", "hours": "24/7"},
        ],
        "response": (
            "**Earthquake Safety — Act immediately:**\n\n"
            "📞 **National Disaster Helpline:** 1070\n"
            "📞 **Police:** 100\n\n"
            "**If you're inside:**\n"
            "1. **DROP, COVER, HOLD** — get under a sturdy table or desk\n"
            "2. Stay away from windows, mirrors, heavy furniture\n"
            "3. Protect your head and neck with your arms\n"
            "4. If in bed, stay there and cover your head\n"
            "5. **Don't run outside during shaking** — most injuries happen from falling debris\n\n"
            "**If you're outside:**\n"
            "1. Move to an **open area** away from buildings, trees, power lines\n"
            "2. Stay away from buildings, bridges, and overpasses\n\n"
            "**After the shaking stops:**\n"
            "1. Check for injuries and help others if safe to do so\n"
            "2. **Check for gas leaks** — if you smell gas, leave immediately\n"
            "3. Use stairs, NOT elevators\n"
            "4. Be prepared for **aftershocks**\n\n"
            "Stay calm. Help is available. 🙏"
        ),
    },
    "sexual_assault": {
        "patterns": [
            r"\b(raped|sexual assault|molested|sexually harassed)\b",
            r"\b(rape hua|molestation hua|sexual harassment)\b",
            r"\b(forced me|coerced into sex|drugged and)\b",
        ],
        "severity": "critical",
        "helplines": [
            {"name": "Women Helpline", "number": "181", "hours": "24/7"},
            {"name": "Police Emergency", "number": "100", "hours": "24/7"},
            {"name": "NCW", "number": "7827-170-170", "hours": "24/7"},
            {"name": "RAHI Foundation", "number": "011-24374501", "hours": "Mon-Sat"},
        ],
        "response": (
            "**This was not your fault. You did nothing wrong.**\n\n"
            "**Please get help immediately:**\n"
            "📞 **Women Helpline:** 181 (24/7)\n"
            "📞 **Police:** 100\n"
            "📞 **NCW:** 7827-170-170\n\n"
            "**Important steps:**\n"
            "1. If you're in danger, call **100** right now\n"
            "2. Go to a **safe place** — a friend's house, police station, hospital\n"
            "3. **Don't bathe or change clothes** — preserve evidence (if recent)\n"
            "4. Go to a hospital for **medical care and forensic examination**\n"
            "5. You can file an FIR — **women can file at any police station**\n"
            "6. The police **cannot refuse** to file an FIR for sexual assault\n\n"
            "**You are brave for sharing this. Help is available. You are not alone.** 🙏"
        ),
    },
}


def detect_crisis(message: str) -> Optional[Dict[str, Any]]:
    """
    Detect if a message contains crisis indicators.
    Returns crisis info dict if detected, None otherwise.
    """
    message_lower = message.lower().strip()

    for crisis_type, config in CRISIS_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, message_lower):
                logger.warning(f"Crisis detected: {crisis_type}")
                return {
                    "type": crisis_type,
                    "severity": config["severity"],
                    "helplines": config["helplines"],
                    "response": config["response"],
                }

    return None


def get_emergency_response(crisis_info: Dict[str, Any]) -> str:
    """Get the full emergency response for a detected crisis."""
    return crisis_info.get("response", "Please call emergency services immediately.")


# ── Disaster PINCODE Database (Indian disaster-prone areas) ────────────────

DISASTER_HOTSPOTS = {
    "flood": [
        "Assam (Brahmaputra basin)", "Bihar (Ganga basin)", "Kerala (monsoon floods)",
        "Maharashtra (Konkan coast)", "West Bengal (Sundarbans)", "UP (Ganga-Yamuna)",
    ],
    "cyclone": [
        "Odisha (Bay of Bengal coast)", "Andhra Pradesh", "Tamil Nadu",
        "West Bengal", "Gujarat", "Maharashtra coast",
    ],
    "earthquake": [
        "J&K (seismic zone V)", "Himachal Pradesh", "Uttarakhand",
        "Northeast India", "Bihar (near Nepal border)", "Gujarat (Kutch)",
    ],
    "drought": [
        "Rajasthan", "Maharashtra (Marathwada/Vidarbha)", "Karnataka",
        "Telangana", "Gujarat (Saurashtra)", "Madhya Pradesh",
    ],
}


def get_disaster_info(disaster_type: str = "") -> str:
    """Get disaster preparedness information."""
    if disaster_type.lower() in DISASTER_HOTSPOTS:
        areas = DISASTER_HOTSPOTS[disaster_type.lower()]
        return f"**{disaster_type.title()}-prone areas in India:**\n" + "\n".join(f"  - {a}" for a in areas)

    lines = ["**Disaster Preparedness — India:**\n"]
    for dtype, areas in DISASTER_HOTSPOTS.items():
        lines.append(f"**{dtype.title()}:** {', '.join(areas[:3])}...")
    lines.append("\n📞 **National Disaster Helpline:** 1070")
    lines.append("📞 **NDRF:** 011-24363260")
    return "\n".join(lines)
