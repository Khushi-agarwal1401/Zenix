from typing import Any, Dict, List
from .interface import PipelineModule
from .llm_client import LLMClient


class IntentClassifier(PipelineModule):
    """
    Classifies the user's intent based on the message content.
    Uses keyword heuristics first, then falls back to LLM classification.
    """

    INTENT_GREETING = "GREETING"
    INTENT_SYSTEM = "SYSTEM_COMMAND"
    INTENT_FACTUAL = "FACTUAL_QUERY"  # RAG
    INTENT_COMPLEX = "COMPLEX_QUERY"  # Agentic
    INTENT_CONTENT = "CONTENT_GEN"  # Summaries, Emails, Code
    INTENT_CHAT = "CHAT"  # General conversation

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data.lower().strip()

        # 1. Greetings
        greetings = [
            "hi", "hello", "hey", "namaste", "salaam", "vanakkam",
            "hii", "helo", "namaskar", "adaab",
        ]
        if any(message == greeting or message.startswith(greeting) for greeting in greetings):
            return {"intent": self.INTENT_GREETING, "confidence": 1.0}

        # 2. System Commands (Time, Status)
        time_words = ["time", "samay", "waqt", "kitne baje", "time kya hai"]
        if any(w in message for w in time_words):
            return {"intent": self.INTENT_SYSTEM, "sub_intent": "TIME", "confidence": 1.0}

        status_words = [
            "how are you", "kaise ho", "kaisa hai", "kaise ho tum",
            "what's up", "what are you", "who are you",
        ]
        if any(w in message for w in status_words):
            return {"intent": self.INTENT_SYSTEM, "sub_intent": "STATUS", "confidence": 1.0}

        # 3. Complex / Agentic Queries
        complex_keywords = [
            "compare", "difference", "plan", "steps", "versus", "vs",
            "analyze", "pros and cons", "trade-off", "which is better",
            "translate", "translation", "convert", "in miles", "in km",
            "to hindi", "to tamil", "to bengali", "to telugu", "to marathi",
            "to english", "fahrenheit", "celsius", "kilogram", "pounds",
            "usd to inr", "inr to usd", "dollars to rupees", "rupees to dollars",
            "euros to", "pounds to", "yen to", "exchange rate", "currency conversion",
            "web search", "search the web", "google", "look up online",
            "news", "headlines", "breaking news", "latest news",
            "stock price", "share price", "nse", "bse", "market price",
            "share price of", "stock of", "reliance share", "tcs stock",
            "location", "coordinates", "where is", "find place", "map of",
            "near me", "nearby", "directions to",
            "festival", "holiday", "chutti", "tyohaar", "calendar",
            "today is what", "aaj kya hai", "kya chutti hai",
        ]
        if any(k in message for k in complex_keywords):
            return {"intent": self.INTENT_COMPLEX, "confidence": 0.85}
        if len(message.split()) > 10 and "and" in message:
            return {"intent": self.INTENT_COMPLEX, "confidence": 0.75}

        # 4. Content Generation
        content_keywords = [
            "draft", "write", "generate", "code", "python", "script",
            "email", "summary", "summarize", "report", "article", "essay",
            "function", "class", "program",
        ]
        if any(k in message for k in content_keywords):
            return {"intent": self.INTENT_CONTENT, "confidence": 0.85}

        # 5. Factual/RAG Queries
        question_starters = [
            "what", "who", "where", "when", "why", "how",
            "explain", "describe", "tell me about", "kya hai", "kaun hai",
            "kahan hai", "kyun", "kaise",
        ]
        if any(message.startswith(s) for s in question_starters) or "?" in message:
            return {"intent": self.INTENT_FACTUAL, "confidence": 0.8}

        # 6. LLM Fallback / Confirmation
        try:
            llm = LLMClient()
            system_prompt = (
                "You are an intent classifier. Classify the user query into exactly one category: "
                "Greeting, System, Factual, Complex, Content, Chat. "
                "Respond with ONLY the category name, nothing else."
            )
            prompt = f"Classify: {message}\nIntent:"
            generated = await llm.async_generate(prompt=prompt, system_prompt=system_prompt)
            generated = generated.strip().lower()

            if "greeting" in generated:
                return {"intent": self.INTENT_GREETING, "confidence": 0.9}
            elif "system" in generated:
                return {"intent": self.INTENT_SYSTEM, "sub_intent": "STATUS", "confidence": 0.9}
            elif "factual" in generated:
                return {"intent": self.INTENT_FACTUAL, "confidence": 0.9}
            elif "complex" in generated or "agent" in generated:
                return {"intent": self.INTENT_COMPLEX, "confidence": 0.9}
            elif "content" in generated or "write" in generated:
                return {"intent": self.INTENT_CONTENT, "confidence": 0.9}
            elif "chat" in generated:
                return {"intent": self.INTENT_CHAT, "confidence": 0.9}
        except Exception as e:
            print(f"LLM Classification failed: {e}")

        # 7. Default to General Chat
        return {"intent": self.INTENT_CHAT, "confidence": 0.5}
