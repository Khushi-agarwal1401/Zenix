from typing import Any, Dict
from .interface import PipelineModule
from .llm_client import LLMClient
from .tools import ToolRegistry

class AgentModule(PipelineModule):
    """
    Agent capable of multi-step reasoning and tool use.
    Uses a Plan-and-Execute strategy.
    """
    def __init__(self, rag_engine):
        self.tools = ToolRegistry(rag_engine)
        
    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        llm = LLMClient()
        query = input_data
        
        # 1. Planning / Decomposition
        # We ask the LLM to break down the task
        plan_prompt = (
            f"You are a planner. Break down this user query into simple search steps.\n"
            f"Available Tools: {self.tools.get_tool_descriptions()}\n"
            f"Query: {query}\n"
            f"Output format: Step 1: search: <query1> | Step 2: search: <query2>\n"
            f"Plan:"
        )
        
        try:
            plan_text = llm.generate(plan_prompt).strip()
            print(f"Agent Plan: {plan_text}")
            
            # Simple parsing of the plan (splitting by pipe or newline)
            steps = []
            if "|" in plan_text:
                steps = plan_text.split("|")
            else:
                steps = plan_text.split("\n")
                
            collected_info = []
            
            # 2. Execution
            for step in steps:
                step = step.strip()
                if not step: continue
                
                # Check for search tool usage
                if "search:" in step.lower():
                    # Extract query
                    parts = step.split("search:", 1)
                    if len(parts) > 1:
                        sub_query = parts[1].strip()
                        print(f"Agent executing search: {sub_query}")
                        result = self.tools.execute("search", sub_query)
                        collected_info.append(f"Info for '{sub_query}':\n{result}")
            
            # 3. Synthesis
            if not collected_info:
                 # Fallback if no valid plan execution
                 return {"response": "I couldn't form a valid plan to answer this complex query.", "source": "AGENT_FAIL"}
                 
            context_text = "\n\n".join(collected_info)
            synthesis_prompt = (
                f"Context:\n{context_text}\n\n"
                f"User Question: {query}\n\n"
                f"Instructions: Synthesize a comprehensive answer provided the context above.\n"
                f"Answer:"
            )
            
            final_answer = llm.generate(synthesis_prompt).strip()
            return {"response": final_answer, "source": "AGENT_PLAN_EXECUTE"}
            
        except Exception as e:
            print(f"Agent Logic failed: {e}")
            return {"response": "Error in agent processing.", "source": "AGENT_ERROR"}
