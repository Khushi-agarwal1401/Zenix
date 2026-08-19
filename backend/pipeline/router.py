from typing import Any, Dict
from .interface import PipelineModule
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .query_rewriter import QueryRewriter
from .modules import SystemModule, ChatModule, RAGModule
from .agent import AgentModule
from .generation import GenerativeModule
from .language_detector import detect_language, normalize_input
from .calendar import get_festival_greeting


class TaskRouter:
    """
    Routes requests to appropriate modules based on intent.
    Now includes language detection and input normalization.
    """

    def __init__(self, rag_engine):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.query_rewriter = QueryRewriter()

        self.system_module = SystemModule()
        self.chat_module = ChatModule()
        self.rag_module = RAGModule(rag_engine)
        self.agent_module = AgentModule(rag_engine)
        self.generative_module = GenerativeModule()

    async def route_and_process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:

        # 0. Normalize and detect language
        normalized = normalize_input(input_data)
        lang_info = detect_language(normalized)
        context["language"] = lang_info

        print(f"Language detected: {lang_info['language']} "
              f"(script={lang_info['script']}, code_mixed={lang_info['is_code_mixed']})")

        # 0.5 Crisis Detection — safety-critical, check before anything else
        try:
            from .crisis import detect_crisis
            crisis = detect_crisis(normalized)
            if crisis:
                return {
                    "response": crisis["response"],
                    "source": "CRISIS",
                    "crisis_type": crisis["type"],
                    "severity": crisis["severity"],
                }
        except ImportError:
            pass

        # 1. Entity Extraction
        entities = await self.entity_extractor.process(normalized, context)
        context["entities"] = entities.get("entities")

        # 2. Classify Intent
        classification = await self.intent_classifier.process(normalized, context)
        intent = classification.get("intent")
        context["intent_info"] = classification

        # 3. Query Rewriting (if needed)
        processed_input = normalized
        if intent == IntentClassifier.INTENT_FACTUAL:
            rewrite_result = await self.query_rewriter.process(normalized, context)
            if rewrite_result.get("rewritten_query"):
                processed_input = rewrite_result.get("rewritten_query")
                context["rewritten_query"] = processed_input
                print(f"Query rewritten to: {processed_input}")

        # 4. Route
        module = None
        persona = context.get("persona", "desi")

        if intent == IntentClassifier.INTENT_GREETING:
            festival_greeting = get_festival_greeting()
            if persona == "desi":
                base = "Arre Namaste! Kaisa hai sab? Batao kya seva karoon?"
                if festival_greeting:
                    base = f"{festival_greeting} Arre Namaste! Kaisa hai sab? Batao kya seva karoon?"
                return {"response": base, "source": "GREETING"}
            else:
                base = "Greetings. I am ready to assist you. Please state your query."
                if festival_greeting:
                    base = f"{festival_greeting} Greetings. I am ready to assist you. Please state your query."
                return {"response": base, "source": "GREETING"}

        elif intent == IntentClassifier.INTENT_SYSTEM:
            module = self.system_module

        elif intent == IntentClassifier.INTENT_FACTUAL:
            module = self.rag_module

        elif intent == IntentClassifier.INTENT_COMPLEX:
            module = self.agent_module

        elif intent == IntentClassifier.INTENT_CONTENT:
            module = self.generative_module

        elif intent == IntentClassifier.INTENT_CHAT:
            module = self.chat_module

        else:
            module = self.chat_module

        # 5. Process
        return await module.process(processed_input, context)
