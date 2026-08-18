"""
Agent Module for Zenix AI.
Plan-and-Execute agent that can use ALL registered tools:
search, weather, sql, calculator, file, datetime.
"""

import re
from typing import Any, Dict, List, Tuple
from .interface import PipelineModule
from .llm_client import LLMClient
from .tools import ToolRegistry
from .system_prompt import get_system_prompt


# Map of tool keywords → tool names for plan parsing
TOOL_KEYWORDS = {
    "search:": "search",
    "weather:": "weather",
    "sql:": "sql",
    "calculator:": "calculator",
    "calc:": "calculator",
    "file:": "file",
    "read:": "file",
    "datetime:": "datetime",
    "time:": "datetime",
    "date:": "datetime",
    "day:": "datetime",
}


class AgentModule(PipelineModule):
    """
    Agent capable of multi-step reasoning and tool use.
    Uses a Plan-and-Execute strategy with system prompts and conversation history.
    Can dispatch to all registered tools: search, weather, sql, calculator, file, datetime.
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
            f"You are a planner. Break down this user query into steps using available tools.\n"
            f"Available Tools:\n{self.tools.get_tool_descriptions()}\n\n"
            f"Query: {query}\n\n"
            f"Output format — one step per line, use pipe separator:\n"
            f"Step 1: <tool>: <args> | Step 2: <tool>: <args>\n\n"
            f"Examples:\n"
            f"- 'weather in Mumbai' → Step 1: weather: Mumbai\n"
            f"- 'highest salary in Delhi' → Step 1: sql: SELECT name, salary FROM employees WHERE city='Delhi' ORDER BY salary DESC LIMIT 1\n"
            f"- 'what is 2**10' → Step 1: calculator: 2**10\n"
            f"- 'today date' → Step 1: datetime: date\n"
            f"- 'read report.txt' → Step 1: file: read report.txt\n"
            f"- 'compare AI vs ML' → Step 1: search: artificial intelligence | Step 2: search: machine learning comparison\n\n"
            f"If the query is simple and only needs one tool, return a single step.\n"
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

            # 2. Parse and Execute steps
            steps = self._parse_plan(plan_text)
            collected_info: List[str] = []

            for tool_name, args in steps:
                print(f"Agent executing {tool_name}: {args}")
                result = self.tools.execute(tool_name, args)
                collected_info.append(f"[{tool_name}] {result}")

            # 3. Synthesis
            if not collected_info:
                return {
                    "response": "I couldn't find relevant information to answer this query.",
                    "source": "AGENT_FAIL",
                }

            context_text = "\n\n".join(collected_info)
            synthesis_prompt = (
                f"Tool Results:\n{context_text}\n\n"
                f"User Question: {query}\n\n"
                f"Instructions: Synthesize a comprehensive answer using the tool results above. "
                f"Be thorough and accurate. If the results are insufficient, acknowledge limitations. "
                f"Format your response clearly."
            )

            final_answer = llm.generate(
                prompt=synthesis_prompt,
                system_prompt=system_prompt,
                history=chat_history,
            )

            if final_answer and final_answer.strip():
                return {"response": final_answer.strip(), "source": "AGENT_PLAN_EXECUTE"}

            # Fallback: return raw tool results if synthesis failed
            return {
                "response": f"Here's what I found:\n\n{context_text}",
                "source": "AGENT_RAW_RESULTS",
            }

        except Exception as e:
            print(f"Agent Logic failed: {e}")
            return {"response": "Error in agent processing.", "source": "AGENT_ERROR"}

    def _parse_plan(self, plan_text: str) -> List[Tuple[str, str]]:
        """
        Parse the LLM-generated plan into (tool_name, args) tuples.

        Handles formats like:
        - "Step 1: search: query | Step 2: weather: Mumbai"
        - "Step 1: search: query\nStep 2: weather: Mumbai"
        - "search: query"
        - "1. search: query"
        """
        steps: List[Tuple[str, str]] = []

        # Split by pipe or newline
        if "|" in plan_text:
            parts = plan_text.split("|")
        else:
            parts = re.split(r'\n+', plan_text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Strip step numbering like "Step 1:", "1.", "1)"
            part = re.sub(r'^(?:Step\s+)?\d+[\.\)]\s*', '', part, flags=re.IGNORECASE)
            part = part.strip()

            # Try to match a tool keyword
            tool_name, args = self._extract_tool_and_args(part)
            if tool_name and args:
                steps.append((tool_name, args))

        return steps

    def _extract_tool_and_args(self, text: str) -> Tuple[str, str]:
        """
        Extract tool name and arguments from a plan step.
        Returns (tool_name, args) or ("", "") if no tool matched.
        """
        text_lower = text.lower().strip()

        for keyword, tool_name in TOOL_KEYWORDS.items():
            if keyword in text_lower:
                # Extract everything after the keyword
                idx = text_lower.index(keyword) + len(keyword)
                args = text[idx:].strip()
                if args:
                    return tool_name, args

        # Fallback: if text looks like a search query, treat it as search
        if len(text) > 3:
            return "search", text

        return "", ""
