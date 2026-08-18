from typing import Any, Dict, List
from .interface import PipelineModule
from .llm_client import LLMClient


class EntityExtractor(PipelineModule):
    """
    Extracts entities from the user message using LLM with a focused system prompt.
    """

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data

        try:
            llm = LLMClient()
            system_prompt = (
                "You are an entity extraction assistant. Extract named entities from the text. "
                "Return entities as a comma-separated list of 'TYPE: VALUE' pairs. "
                "Types: Date, Location, Person, Product, Organization, Amount. "
                "Return 'None' if no entities found."
            )

            prompt = f"Extract entities from this text:\n{message}\nEntities:"

            extracted = llm.generate(prompt=prompt, system_prompt=system_prompt)

            if extracted and "none" not in extracted.lower().strip():
                # Parse comma-separated entity list
                entities = []
                for part in extracted.split(","):
                    part = part.strip()
                    if ":" in part:
                        etype, evalue = part.split(":", 1)
                        entities.append({
                            "type": etype.strip(),
                            "value": evalue.strip(),
                        })
                    elif part:
                        entities.append({"type": "UNKNOWN", "value": part})

                return {"entities": entities, "raw_extraction": extracted}

        except Exception as e:
            print(f"Entity Extraction failed: {e}")

        return {"entities": []}
