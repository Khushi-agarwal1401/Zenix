from typing import Any, Dict
import random
from datetime import datetime
from .interface import PipelineModule
from .llm_client import LLMClient
from .system_prompt import get_system_prompt


class SystemModule(PipelineModule):
    """
    Handles system commands like requests for time or status.
    """

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        intent_info = context.get("intent_info", {})
        sub_intent = intent_info.get("sub_intent")
        persona = context.get("persona", "desi")

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
    Handles general chat interactions using the LLM with system prompt and history.
    """

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        persona = context.get("persona", "desi")
        history = context.get("history", [])

        llm = LLMClient()
        system_prompt = get_system_prompt(persona)

        # Build conversation history for the LLM
        chat_history = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                chat_history.append({"role": role, "content": content})

        generated = llm.generate(
            prompt=input_data,
            system_prompt=system_prompt,
            history=chat_history,
        )

        if generated and generated.strip():
            return {"response": generated.strip(), "source": "CHAT_GENERATED"}

        # Fallback responses if LLM fails
        if persona == "desi":
            fallbacks = [
                "Achha, samajh gaya. Thoda detail mein batao na?",
                "Arre wah! Yeh toh interesting hai. Aur batao?",
                "Hmm... ispe thoda sochna padega. Ek minute do.",
                "Sahi pakde hain!",
            ]
        else:
            fallbacks = [
                "I have received your input. Could you please elaborate for clarity?",
                "Processing request... Please provide specific details.",
                "Noted. Further information is required.",
                "That falls within my processing capabilities. Please continue.",
            ]

        return {"response": random.choice(fallbacks), "source": "CHAT_FALLBACK"}


class RAGModule(PipelineModule):
    """
    Handles RAG (Retrieval Augmented Generation) queries.
    """

    def __init__(self, rag_engine):
        self.rag_engine = rag_engine

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        persona = context.get("persona", "desi")
        history = context.get("history", [])

        # Perform Search
        results = []
        if self.rag_engine:
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
                system_prompt = get_system_prompt(persona)

                prompt = (
                    f"Context:\n{context_text}\n\n"
                    f"Question: {input_data}\n\n"
                    f"Instructions: Answer the question using ONLY the context above. "
                    f"If the answer is not in the context, say 'I don't have enough information.' "
                    f"Be accurate and cite specific details from the context."
                )

                # Build chat history
                chat_history = []
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant") and content:
                        chat_history.append({"role": role, "content": content})

                generated_answer = llm.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history=chat_history,
                )

                if generated_answer and generated_answer.strip():
                    response_text = generated_answer.strip()
                    source = "RAG_GENERATED"
                else:
                    response_text = f"Based on my knowledge base:\n{context_text}"
                    source = "RAG_FALLBACK"

            except Exception as e:
                print(f"RAG Generation failed: {e}")
                response_text = f"Based on my knowledge base:\n{context_text}\n(Generation failed)"
                source = "RAG_FALLBACK"
        else:
            response_text = "I couldn't find any relevant information in my knowledge base to answer that."

        return {"response": response_text, "source": source}
