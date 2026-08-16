from typing import Any, Dict, List
from .interface import PipelineModule
from .llm_client import LLMClient

class EntityExtractor(PipelineModule):
    """
    Extracts entities from the user message using LLM.
    """
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data
        
        try:
            llm = LLMClient()
            # Flan-T5 is good at simple extraction if prompted well
            prompt = f"Extract entities (Date, Location, Person, Product) from this text. Return 'None' if none found.\nText: {message}\nEntities:"
            
            extracted = llm.generate(prompt).strip()
            
            if extracted and "none" not in extracted.lower():
                # Naive parsing or just storing the string for now
                # In a real system, we'd force JSON output or parse strict format
                return {"entities": extracted, "raw_extraction": True}
                
        except Exception as e:
            print(f"Entity Extraction failed: {e}")
            
        return {"entities": []}
