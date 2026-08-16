from typing import Any, Dict
from .interface import PipelineModule
from .llm_client import LLMClient

class GenerativeModule(PipelineModule):
    """
    Handles content generation tasks using templates.
    """
    
    TEMPLATE_EMAIL = "EMAIL"
    TEMPLATE_SUMMARY = "SUMMARY"
    TEMPLATE_CODE = "CODE"
    TEMPLATE_REPORT = "REPORT"
    
    def __init__(self):
        pass
        
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        llm = LLMClient()
        query = input_data
        
        # Determine template based on query content/intent info
        # (Ideally passed from intent classifier, but we can refine here)
        template_type = self._detect_template(query)
        
        prompt = ""
        if template_type == self.TEMPLATE_EMAIL:
            prompt = (
                f"Task: Draft a professional email.\n"
                f"Instructions: {query}\n"
                f"Email Draft:"
            )
        elif template_type == self.TEMPLATE_SUMMARY:
            prompt = (
                f"Task: Summarize the text.\n"
                f"Input: {query}\n"
                f"Summary:"
            )
        elif template_type == self.TEMPLATE_CODE:
            prompt = (
                f"Task: Write code.\n"
                f"Instructions: {query}\n"
                f"Code:"
            )
        elif template_type == self.TEMPLATE_REPORT:
             prompt = (
                f"Task: Write a structured report.\n"
                f"Topic: {query}\n"
                f"Structure: Introduction, Main Analysis, Conclusion.\n"
                f"Report:"
            )
        else:
            # General generation
            prompt = query
            
        try:
            generated_content = llm.generate(prompt).strip()
            return {"response": generated_content, "source": f"GEN_{template_type}"}
        except Exception as e:
            print(f"Content Generation failed: {e}")
            return {"response": "Error generating content.", "source": "GEN_ERROR"}

    def _detect_template(self, query: str) -> str:
        q = query.lower()
        if "email" in q or "mail to" in q:
            return self.TEMPLATE_EMAIL
        elif "summarize" in q or "summary" in q:
            return self.TEMPLATE_SUMMARY
        elif "code" in q or "function" in q or "script" in q or "python" in q:
            return self.TEMPLATE_CODE
        elif "report" in q or "article" in q:
            return self.TEMPLATE_REPORT
        return "GENERAL"
