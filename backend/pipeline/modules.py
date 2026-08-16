from typing import Any, Dict
import random
from datetime import datetime
from .interface import PipelineModule
from .llm_client import LLMClient

class SystemModule(PipelineModule):
    """
    Handles system commands like requests for time or status.
    """
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        intent_info = context.get("intent_info", {})
        sub_intent = intent_info.get("sub_intent")
        persona = context.get("persona", "default")
        
        response_text = ""
        
        if sub_intent == "TIME":
            current_time = datetime.now().strftime("%I:%M %p")
            if persona == "desi":
                response_text = f"Abhi toh {current_time} ho raha hai. Chai ka time hai kya?"
            else:
                response_text = f"Current local time is {current_time}."
                
        elif sub_intent == "STATUS":
             if persona == "desi":
                 response_text = "Main badhiya hoon, bas aapka wait kar raha tha! Aap sunao?"
             else:
                 response_text = "System is operating at optimal efficiency. Thank you for asking."
        
        else:
             response_text = "System command recognized but not handled."

        return {"response": response_text, "source": "SYSTEM"}

class ChatModule(PipelineModule):
    """
    Handles general chat interactions.
    """
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        persona = context.get("persona", "default")
        
        if persona == "desi":
            fallbacks = [
                "Achha, samajh gaya. Thoda detail mein batao na?",
                "Arre wah! Yeh toh interesting hai. Aur batao?",
                "Hmm... ispe thoda sochna padega. Ek minute do.",
                "Sahi pakde hain!"
            ]
        else:
            fallbacks = [
                "I have received your input. Could you please elaborate for clarity?",
                "Processing request... Please provide specific details.",
                "Noted. Further information is required.",
                "That falls within my processing capabilities. Please continue."
            ]
            
        return {"response": random.choice(fallbacks), "source": "CHAT_FALLBACK"}

class RAGModule(PipelineModule):
    """
    Handles RAG (Retrieval Augmented Generation) queries.
    """
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Perform Search
        results = []
        if self.rag_engine:
            # Use rewritten query if available
            query = context.get("rewritten_query", input_data)
            results = self.rag_engine.search(query, k=3)
            
        # Format Context
        context_text = ""
        if results:
             context_text = "\n".join([f"- {r['content']}" for r in results])
        
        # Save results to context for logging
        context["retrieved_results"] = results
        
        # Generation Step
        response_text = ""
        source = "RAG_NO_CONTEXT"
        
        if context_text:
            try:
                llm = LLMClient()
                prompt = (
                    f"Context:\n{context_text}\n\n"
                    f"Question: {input_data}\n\n"
                    f"Instructions: Answer the question using ONLY the context above. If the answer is not in the context, say 'I don't have enough information.'\n"
                    f"Answer:"
                )
                
                generated_answer = llm.generate(prompt).strip()
                response_text = generated_answer
                source = "RAG_GENERATED"
                
            except Exception as e:
                print(f"RAG Generation failed: {e}")
                response_text = f"Based on my knowledge base:\n{context_text}\n(Generation failed)"
                source = "RAG_FALLBACK"
        else:
            response_text = "I couldn't find any relevant information in my knowledge base to answer that."
            
        return {"response": response_text, "source": source}
