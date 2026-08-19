"""
Multi-Step Agent Reasoning — iterative planning, conditional branching, and cross-tool memory.

For complex queries that require multiple steps, this module breaks down the task into
sub-goals and tracks state across tool calls.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class ReasoningChain:
    """Tracks a multi-step reasoning session with memory across steps."""

    def __init__(self, query: str, context: Dict[str, Any] = None):
        self.original_query = query
        self.context = context or {}
        self.steps: List[Dict[str, Any]] = []
        self.memory: Dict[str, Any] = {}  # cross-step memory
        self.current_step = 0
        self.is_complete = False
        self.final_answer: Optional[str] = None

    def add_step(self, step_type: str, description: str, result: Any = None):
        step = {
            "step": self.current_step,
            "type": step_type,
            "description": description,
            "result": result,
        }
        self.steps.append(step)
        self.current_step += 1

    def store_memory(self, key: str, value: Any):
        self.memory[key] = value

    def get_memory(self, key: str, default=None):
        return self.memory.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "steps": self.steps,
            "memory": self.memory,
            "is_complete": self.is_complete,
            "final_answer": self.final_answer,
        }


class MultiStepReasoner:
    """Breaks complex queries into sub-goals and executes them iteratively."""

    def __init__(self, llm_client: LLMClient, agent=None):
        self.llm = llm_client
        self.agent = agent  # the Agent instance for tool execution

    async def decompose(self, query: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Break a complex query into sub-goals using LLM."""
        system = (
            "You break complex questions into 2-5 simple sub-goals.\n"
            "Each sub-goal should be independently answerable.\n"
            "Return a JSON array of objects with 'goal' and 'tools' (list of tool names).\n"
            "Only return the JSON array, nothing else."
        )
        prompt = (
            f"Original query: {query}\n"
            f"Context: {json.dumps(context or {}, ensure_ascii=False)}\n"
            f"Available tools: search, web_search, news, stocks, weather, calendar, "
            f"location, sql, calculator, translate, unit, currency, speech, eligibility\n"
            f"Break this into sub-goals:"
        )
        try:
            result = await self.llm.generate(prompt, system_prompt=system, temperature=0.3, max_tokens=512)
            result = result.strip()
            # Extract JSON from potential markdown fences
            if "```" in result:
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()
            goals = json.loads(result)
            if isinstance(goals, list):
                return goals
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Decomposition failed: {e}, falling back to single goal")

        return [{"goal": query, "tools": []}]

    async def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a multi-step reasoning chain."""
        chain = ReasoningChain(query, context)

        # Step 1: Decompose
        sub_goals = await self.decompose(query, context)
        chain.add_step("decomposition", f"Broke into {len(sub_goals)} sub-goals", sub_goals)

        results = []
        for goal_obj in sub_goals:
            goal = goal_obj.get("goal", "")
            tools_hint = goal_obj.get("tools", [])

            # Execute the sub-goal using the agent
            if self.agent:
                try:
                    response = await self.agent.process_query(goal, context=context)
                    result_text = response.get("response", "")
                    chain.store_memory(f"result_{chain.current_step}", result_text)
                    chain.add_step("execution", goal, result_text)
                    results.append({"goal": goal, "result": result_text})
                except Exception as e:
                    logger.error(f"Sub-goal failed: {e}")
                    chain.add_step("execution", f"FAILED: {goal}", str(e))
                    results.append({"goal": goal, "error": str(e)})
            else:
                chain.add_step("execution", f"(no agent) {goal}", None)
                results.append({"goal": goal, "result": None})

        # Step 2: Synthesize final answer
        synthesis_prompt = (
            f"Original question: {query}\n"
            f"Sub-goal results:\n"
        )
        for r in results:
            synthesis_prompt += f"- Goal: {r['goal']}\n  Result: {r.get('result', r.get('error', 'N/A'))}\n"
        synthesis_prompt += (
            "\nSynthesize these results into a single comprehensive, helpful answer. "
            "If some sub-goals failed, still use the successful results and note what couldn't be answered."
        )

        try:
            final = await self.llm.generate(synthesis_prompt, system_prompt="Synthesize results into one answer.", temperature=0.3, max_tokens=1024)
            chain.final_answer = final
            chain.is_complete = True
        except Exception as e:
            chain.final_answer = f"Partial results:\n" + "\n".join(
                f"**{r['goal']}**: {r.get('result', r.get('error', 'N/A'))}" for r in results
            )
            chain.is_complete = True

        return chain.to_dict()


# Simple heuristic: should a query be multi-step?
def needs_multi_step(query: str) -> bool:
    """Check if a query likely needs multi-step reasoning."""
    indicators = [
        " and ", " then ", " also ", " compare ", " contrast ",
        " first ", " finally ", " step by step ", " report ",
        " summarize and ", " find and ", " get the ",
    ]
    q = query.lower()
    return sum(1 for ind in indicators if ind in q) >= 2 or len(query.split()) > 30
