from typing import Any, Dict
from .interface import PipelineModule
from .interface import PipelineModule
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .query_rewriter import QueryRewriter
from .modules import SystemModule, ChatModule, RAGModule
from .agent import AgentModule
from .generation import GenerativeModule

class TaskRouter:
    """
    Routes requests to appropriate modules based on intent.
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
        
        # 0. Entity Extraction (Parallel or Sequential)
        # We run this for all queries as it might be useful
        entities = await self.entity_extractor.process(input_data, context)
        context["entities"] = entities.get("entities")
        
        # 1. Classify Intent
        classification = await self.intent_classifier.process(input_data, context)
        intent = classification.get("intent")
        
        # Update context with intent info
        context["intent_info"] = classification
        
        # 1.5 Query Rewriting (if needed)
        # We check intent first, if RAG/Factual, we try to rewrite
        processed_input = input_data
        if intent == IntentClassifier.INTENT_FACTUAL:
             rewrite_result = await self.query_rewriter.process(input_data, context)
             if rewrite_result.get("rewritten_query"):
                 processed_input = rewrite_result.get("rewritten_query")
                 context["rewritten_query"] = processed_input
                 print(f"Query rewritten to: {processed_input}")
        
        # 2. Route
        module = None
        
        if intent == IntentClassifier.INTENT_GREETING:
             # Greetings are simple enough to handle directly or typically routed to CHAT/SYSTEM with a specific flag
             # For this iteration, we'll just handle it inline or use SystemModule if we wanted to be strict.
             # Let's map it to a simple response here for simplicity, OR create a GreetingModule.
             # Re-using legacy logic:
             persona = context.get("persona", "default")
             if persona == "desi":
                return {"response": "Arre Namaste! Kaisa hai sab? Batao kya seva karoon?", "source": "GREETING"}
             else:
                return {"response": "Greetings. I am ready to assist you. Please state your query.", "source": "GREETING"}
                
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
             # Default fallback
             module = self.chat_module
             
        # 3. Process
        return await module.process(processed_input, context)
