from typing import Any, Dict
from .interface import PipelineModule
from .llm_client import LLMClient

class QueryRewriter(PipelineModule):
    """
    Rewrites user queries to be more suitable for search/RAG.
    """
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data
        intent = context.get("intent_info", {}).get("intent")
        
        # Only rewrite if it's a Factual query or we aren't sure
        if intent != "FACTUAL_QUERY":
            return {"rewritten_query": message}
            
        try:
            llm = LLMClient()
            prompt = f"Rewrite this query to be more effective for a semantic search engine.\nOriginal: {message}\nRewritten:"
            
            rewritten = llm.generate(prompt).strip()
            
            # Simple check to ensure we didn't lose the meaning or generate garbage
            if len(rewritten) > 3:
                return {"rewritten_query": rewritten}
                
        except Exception as e:
            print(f"Query Rewriting failed: {e}")
            
        return {"rewritten_query": message}
