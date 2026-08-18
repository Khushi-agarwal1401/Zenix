from typing import Any, Dict
from .interface import PipelineModule
from .llm_client import LLMClient


class QueryRewriter(PipelineModule):
    """
    Rewrites user queries to be more effective for search/RAG.
    Uses a focused system prompt for query rewriting.
    """

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data
        intent = context.get("intent_info", {}).get("intent")

        # Only rewrite if it's a Factual query
        if intent != "FACTUAL_QUERY":
            return {"rewritten_query": message}

        try:
            llm = LLMClient()
            system_prompt = (
                "You are a query rewriting assistant. Your job is to reformulate user queries "
                "to make them more effective for semantic search. Preserve the original meaning "
                "while making the query clearer, more specific, and search-friendly. "
                "Output ONLY the rewritten query, nothing else."
            )

            prompt = (
                f"Rewrite this query for better semantic search results.\n"
                f"Original: {message}\n"
                f"Rewritten:"
            )

            rewritten = llm.generate(prompt=prompt, system_prompt=system_prompt)

            if rewritten and len(rewritten.strip()) > 3:
                return {"rewritten_query": rewritten.strip()}

        except Exception as e:
            print(f"Query Rewriting failed: {e}")

        return {"rewritten_query": message}
