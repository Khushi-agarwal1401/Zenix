"""
Proactive Suggestions Engine — context-aware follow-up suggestions.

Analyzes conversation context to suggest relevant next actions:
- Related government schemes
- Tool suggestions (weather, stocks, news)
- Deep-dive topics
- Actionable next steps
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Topic → suggestion mappings (keyword-based)
TOPIC_SUGGESTIONS = {
    "aadhaar": [
        {"text": "How to update Aadhaar address?", "icon": "📝"},
        {"text": "Link Aadhaar with PAN card", "icon": "🔗"},
        {"text": "Find nearest Aadhaar centre", "icon": "📍"},
    ],
    "upi": [
        {"text": "Set up UPI for the first time", "icon": "💳"},
        {"text": "Troubleshoot failed UPI transaction", "icon": "🔧"},
        {"text": "Check UPI transaction limits", "icon": "📊"},
    ],
    "farmer": [
        {"text": "Check PM-Kisan eligibility", "icon": "🌾"},
        {"text": "View current crop mandi prices", "icon": "💰"},
        {"text": "Weather advisory for farming", "icon": "🌤️"},
    ],
    "stock": [
        {"text": "Compare Nifty vs Sensex performance", "icon": "📈"},
        {"text": "Check mutual fund options", "icon": "💼"},
        {"text": "Learn about SIP investing", "icon": "📚"},
    ],
    "education": [
        {"text": "Check scholarship eligibility", "icon": "🎓"},
        {"text": "Upcoming exam dates", "icon": "📅"},
        {"text": "Top engineering colleges in India", "icon": "🏛️"},
    ],
    "health": [
        {"text": "Check Ayushman Bharat eligibility", "icon": "🏥"},
        {"text": "Find nearby hospitals", "icon": "🏨"},
        {"text": "Health insurance options", "icon": "🛡️"},
    ],
    "job": [
        {"text": "Government job openings", "icon": "💼"},
        {"text": "PMKVY skill development programs", "icon": "🛠️"},
        {"text": "MUDRA loan for business", "icon": "🏦"},
    ],
    "weather": [
        {"text": "7-day weather forecast", "icon": "📅"},
        {"text": "Air quality index", "icon": "💨"},
        {"text": "Weather alerts for your area", "icon": "⚠️"},
    ],
    "news": [
        {"text": "More headlines on this topic", "icon": "📰"},
        {"text": "Related stock market impact", "icon": "📊"},
        {"text": "Expert opinions on this", "icon": "💬"},
    ],
    "translation": [
        {"text": "Translate in another language", "icon": "🌐"},
        {"text": "Learn this phrase in Hindi", "icon": "📖"},
        {"text": "Pronunciation guide", "icon": "🔊"},
    ],
    "legal": [
        {"text": "How to file RTI application", "icon": "📋"},
        {"text": "Know your consumer rights", "icon": "⚖️"},
        {"text": "Free legal aid services", "icon": "🏛️"},
    ],
    "travel": [
        {"text": "Check train availability", "icon": "🚂"},
        {"text": "Compare flight prices", "icon": "✈️"},
        {"text": "Hotel recommendations", "icon": "🏨"},
    ],
}


class SuggestionEngine:
    """Generate proactive suggestions based on conversation context."""

    def __init__(self):
        self.conversation_topics: List[str] = []

    def analyze_message(self, message: str, response: str) -> List[Dict[str, str]]:
        """Analyze the latest exchange and return relevant suggestions."""
        combined = (message + " " + response).lower()
        suggestions = []
        matched_topics = []

        # Find matching topics
        for topic, topic_suggestions in TOPIC_SUGGESTIONS.items():
            if topic in combined:
                matched_topics.append(topic)
                for s in topic_suggestions[:2]:  # Max 2 per topic
                    if s not in suggestions:
                        suggestions.append(s)

        # Track topics for cross-referencing
        self.conversation_topics.extend(matched_topics)
        self.conversation_topics = self.conversation_topics[-10:]  # Keep last 10

        # Add contextual suggestions based on conversation history
        if len(self.conversation_topics) > 1:
            # If user asked about multiple topics, suggest combining them
            if "farmer" in self.conversation_topics and "weather" in self.conversation_topics:
                suggestions.append({"text": "Weather-based crop advisory", "icon": "🌾🌤️"})
            if "education" in self.conversation_topics and "job" in self.conversation_topics:
                suggestions.append({"text": "Career guidance after education", "icon": "🎯"})
            if "aadhaar" in self.conversation_topics and "upi" in self.conversation_topics:
                suggestions.append({"text": "Link Aadhaar to bank for UPI", "icon": "🔗"})

        # Limit total suggestions
        return suggestions[:5]

    def get_followup_questions(self, response: str, persona: str = "desi") -> List[str]:
        """Generate natural follow-up questions the user might ask."""
        import random

        # Generic follow-ups that work for any response
        generic = [
            "Tell me more about this",
            "How do I get started?",
            "What are the alternatives?",
        ]

        desi_followups = [
            "Aur detail mein batao",
            "Iska kya fayda hai?",
            "Kaise karein ye sab?",
            "Koi aur option hai kya?",
        ]

        sarkari_followups = [
            "Please provide more details",
            "What are the prerequisites?",
            "Are there any deadlines?",
            "What documents are required?",
        ]

        if persona == "desi":
            return random.sample(desi_followups, min(3, len(desi_followups)))
        return random.sample(sarkari_followups, min(3, len(sarkari_followups)))

    def reset(self):
        """Reset conversation topic tracking."""
        self.conversation_topics = []


# Singleton
suggestion_engine = SuggestionEngine()
