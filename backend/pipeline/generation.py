from typing import Any, Dict
from .interface import PipelineModule
from .llm_client import LLMClient
from .system_prompt import get_system_prompt


class GenerativeModule(PipelineModule):
    """
    Handles content generation tasks (emails, summaries, code, reports) using the LLM with system prompts.
    """

    TEMPLATE_EMAIL = "EMAIL"
    TEMPLATE_SUMMARY = "SUMMARY"
    TEMPLATE_CODE = "CODE"
    TEMPLATE_REPORT = "REPORT"

    def __init__(self):
        pass

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        persona = context.get("persona", "desi")
        history = context.get("history", [])

        llm = LLMClient()
        system_prompt = get_system_prompt(persona)
        query = input_data

        # Determine template based on query content
        template_type = self._detect_template(query)

        # Build the generation-specific prompt
        prompt = self._build_prompt(template_type, query)

        # Build chat history
        chat_history = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                chat_history.append({"role": role, "content": content})

        try:
            generated_content = await llm.async_generate(
                prompt=prompt,
                system_prompt=system_prompt,
                history=chat_history,
            )
            if generated_content and generated_content.strip():
                return {"response": generated_content.strip(), "source": f"GEN_{template_type}"}
            return {"response": "I was unable to generate the content. Please try rephrasing.", "source": "GEN_EMPTY"}
        except Exception as e:
            print(f"Content Generation failed: {e}")
            return {"response": "Error generating content.", "source": "GEN_ERROR"}

    def _build_prompt(self, template_type: str, query: str) -> str:
        """Build a structured prompt based on the template type."""
        if template_type == self.TEMPLATE_EMAIL:
            return (
                f"Task: Draft a professional email.\n"
                f"Instructions: {query}\n\n"
                f"Write a well-structured, professional email with proper greeting, body, and closing.\n"
                f"Email Draft:"
            )
        elif template_type == self.TEMPLATE_SUMMARY:
            return (
                f"Task: Summarize the following text concisely.\n"
                f"Input: {query}\n\n"
                f"Provide a clear, accurate summary covering the key points.\n"
                f"Summary:"
            )
        elif template_type == self.TEMPLATE_CODE:
            return (
                f"Task: Write code based on the following instructions.\n"
                f"Instructions: {query}\n\n"
                f"Write clean, well-commented code. Use proper formatting with language tags.\n"
                f"Code:"
            )
        elif template_type == self.TEMPLATE_REPORT:
            return (
                f"Task: Write a structured report.\n"
                f"Topic: {query}\n\n"
                f"Structure: Introduction, Main Analysis, Conclusion.\n"
                f"Write a thorough, well-organized report.\n"
                f"Report:"
            )
        else:
            return query

    def _detect_template(self, query: str) -> str:
        q = query.lower()
        if "email" in q or "mail to" in q or "draft a letter" in q:
            return self.TEMPLATE_EMAIL
        elif "summarize" in q or "summary" in q or "tldr" in q:
            return self.TEMPLATE_SUMMARY
        elif "code" in q or "function" in q or "script" in q or "python" in q or "javascript" in q:
            return self.TEMPLATE_CODE
        elif "report" in q or "article" in q or "essay" in q:
            return self.TEMPLATE_REPORT
        return "GENERAL"
