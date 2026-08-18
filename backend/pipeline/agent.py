from typing import Any, Dict
from .interface import PipelineModule
from .llm_client import LLMClient
from .tools import ToolRegistry
from .system_prompt import get_system_prompt


class AgentModule(PipelineModule):
    """
    Agent capable of multi-step reasoning and tool use.
    Uses a Plan-and-Execute strategy with system prompts and conversation history.
    """

    def __init__(self, rag_engine):
        self.tools = ToolRegistry(rag_engine)

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        persona = context.get("persona", "desi")
        history = context.get("history", [])

        llm = LLMClient()
        system_prompt = get_system_prompt(persona)
        query = input_data

        # Build chat history
        chat_history = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                chat_history.append({"role": role, "content": content})

        # 1. Planning / Decomposition
        plan_prompt = (
            f"You are a planner. Break down this user query into simple search steps.\n"
            f"Available Tools: {self.tools.get_tool_descriptions()}\n"
            f"Query: {query}\n"
            f"Output format: Step 1: search: <query1> | Step 2: search: <query2>\n"
            f"If the query is simple enough, return a single step.\n"
            f"Plan:"
        )

        try:
            plan_text = llm.generate(
                prompt=plan_prompt,
                system_prompt=system_prompt,
                history=chat_history,
            )
            if not plan_text:
                return {
                    "response": "I couldn't form a plan to answer this query.",
                    "source": "AGENT_FAIL",
                }

            plan_text = plan_text.strip()
            print(f"Agent Plan: {plan_text}")

            # Parse the plan
            steps = []
            if "|" in plan_text:
                steps = plan_text.split("|")
            else:
                steps = plan_text.split("\n")

            collected_info = []

            # 2. Execution
            for step in steps:
                step = step.strip()
                if not step:
                    continue

                # Check for search tool usage
                if "search:" in step.lower():
                    parts = step.split("search:", 1)
                    if len(parts) > 1:
                        sub_query = parts[1].strip()
                        print(f"Agent executing search: {sub_query}")
                        result = self.tools.execute("search", sub_query)
                        collected_info.append(f"Info for '{sub_query}':\n{result}")

            # 3. Synthesis
            if not collected_info:
                return {
                    "response": "I couldn't find relevant information to answer this complex query.",
                    "source": "AGENT_FAIL",
                }

            context_text = "\n\n".join(collected_info)
            synthesis_prompt = (
                f"Context:\n{context_text}\n\n"
                f"User Question: {query}\n\n"
                f"Instructions: Synthesize a comprehensive answer using the context above. "
                f"Be thorough and accurate. If the context is insufficient, acknowledge limitations.\n"
                f"Answer:"
            )

            final_answer = llm.generate(
                prompt=synthesis_prompt,
                system_prompt=system_prompt,
                history=chat_history,
            )

            if final_answer and final_answer.strip():
                return {"response": final_answer.strip(), "source": "AGENT_PLAN_EXECUTE"}

            return {
                "response": "I found some information but couldn't synthesize a complete answer.",
                "source": "AGENT_FAIL",
            }

        except Exception as e:
            print(f"Agent Logic failed: {e}")
            return {"response": "Error in agent processing.", "source": "AGENT_ERROR"}
