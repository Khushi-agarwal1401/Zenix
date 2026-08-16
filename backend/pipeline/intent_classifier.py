from typing import Any, Dict, List
from .interface import PipelineModule
from .llm_client import LLMClient

class IntentClassifier(PipelineModule):
    """
    Classifies the user's intent based on the message content.
    """
    
    INTENT_GREETING = "GREETING"
    INTENT_SYSTEM = "SYSTEM_COMMAND"
    INTENT_FACTUAL = "FACTUAL_QUERY" # RAG
    INTENT_COMPLEX = "COMPLEX_QUERY" # Agentic
    INTENT_CONTENT = "CONTENT_GEN" # Summaries, Emails, Code
    INTENT_CHAT = "CHAT" # General conversation
    
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data.lower().strip()
        
        # 1. Greetings
        greetings = ["hi", "hello", "hey", "namaste", "salaam", "vanakkam"]
        if any(word in message.split() for word in greetings):
             return {"intent": self.INTENT_GREETING, "confidence": 1.0}
             
        # 2. System Commands (Time, Status)
        if "time" in message or "samay" in message:
            return {"intent": self.INTENT_SYSTEM, "sub_intent": "TIME", "confidence": 1.0}
            
        if "how are you" in message or "kaise ho" in message:
             return {"intent": self.INTENT_SYSTEM, "sub_intent": "STATUS", "confidence": 1.0}

        # 3. Factual/RAG Queries
        # Heuristic: Questions often start with who, what, where, when, why, how
        # or contain specific domain keywords. For now, we'll lean towards RAG for longer queries
        # or queries that look like information seeking.
        
        # 2.5 Complex / Agentic Queries
        # Look for keywords that imply multi-step reasoning
        complex_keywords = ["compare", "difference", "plan", "steps", "versus", "vs", "analyze"]
        if any(k in message for k in complex_keywords) or (len(message.split()) > 10 and "and" in message):
             return {"intent": self.INTENT_COMPLEX, "confidence": 0.85}

        # 2.8 Content Generation
        content_keywords = ["draft", "write", "generate", "code", "python", "script", "email", "summary", "summarize", "report", "article"]
        if any(k in message for k in content_keywords):
             return {"intent": self.INTENT_CONTENT, "confidence": 0.85}

        question_starters = ["what", "who", "where", "when", "why", "how", "explain", "describe", "tell me about"]
        if any(message.startswith(s) for s in question_starters) or "?" in message:
             return {"intent": self.INTENT_FACTUAL, "confidence": 0.8}
        
        # 4. LLM Fallback / Confirmation
        # If no strong heuristic match, or to refine, use LLM.
        try:
            llm = LLMClient()
            llm = LLMClient()
            prompt = f"Classify the intent of this user query into one of these categories: Greeting, System, Factual, Complex, Content, Chat.\nQuery: {message}\nIntent:"
            generated = llm.generate(prompt).strip().lower()
            
            if "greeting" in generated:
                return {"intent": self.INTENT_GREETING, "confidence": 0.9}
            elif "system" in generated:
                return {"intent": self.INTENT_SYSTEM, "sub_intent": "STATUS", "confidence": 0.9} # Defaulting system to status for now
            elif "factual" in generated:
                return {"intent": self.INTENT_FACTUAL, "confidence": 0.9}
            elif "complex" in generated or "agent" in generated:
                return {"intent": self.INTENT_COMPLEX, "confidence": 0.9}
            elif "content" in generated or "write" in generated:
                return {"intent": self.INTENT_CONTENT, "confidence": 0.9}
            elif "content" in generated or "write" in generated:
                return {"intent": self.INTENT_CONTENT, "confidence": 0.9}
            elif "chat" in generated:
                return {"intent": self.INTENT_CHAT, "confidence": 0.9}
        except Exception as e:
            print(f"LLM Classification failed: {e}")

        # 5. Default to General Chat
        return {"intent": self.INTENT_CHAT, "confidence": 0.5}
