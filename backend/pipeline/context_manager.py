"""
Context Manager for Zenix AI.

Manages conversation context window by:
  1. Proactive summarization before hitting limits
  2. Injecting user memory facts into context
  3. Token counting (approximate)
  4. Smart truncation strategies
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Approximate tokens per character for Indian languages + English
# English: ~4 chars/token, Hindi/Devanagari: ~2 chars/token, mixed: ~3 chars/token
CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    """Estimate token count from text (approximate)."""
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def estimate_history_tokens(history: List[Dict[str, str]]) -> int:
    """Estimate total tokens in conversation history."""
    total = 0
    for msg in history:
        content = msg.get("content", "")
        # Add ~4 tokens overhead per message (role, separators)
        total += estimate_tokens(content) + 4
    return total


class ContextManager:
    """
    Manages the context window for LLM calls.

    Strategies:
      1. If history fits within limit, use as-is
      2. If too long, summarize old messages + keep recent
      3. Inject user memory facts at the start
      4. Smart truncation: keep user's last question + relevant context
    """

    def __init__(
        self,
        max_context_tokens: int = 4000,
        keep_recent_messages: int = 10,
        memory_injection: bool = True,
    ):
        """
        Args:
            max_context_tokens: Maximum tokens for the full context (prompt + history + response)
            keep_recent_messages: Minimum messages to keep unsummarized
            memory_injection: Whether to inject user memory into context
        """
        self.max_context_tokens = max_context_tokens
        self.keep_recent_messages = keep_recent_messages
        self.memory_injection = memory_injection

    def prepare_context(
        self,
        history: List[Dict[str, str]],
        session_id: str = "default",
        persona: str = "desi",
        system_prompt: str = "",
    ) -> List[Dict[str, str]]:
        """
        Prepare conversation history for LLM call.

        Returns a list of messages ready for the LLM:
        - Optional: system context with memory
        - Optional: summary of old messages
        - Recent messages (unsummarized)
        """
        messages = []

        # Estimate available tokens
        system_tokens = estimate_tokens(system_prompt)
        available_tokens = self.max_context_tokens - system_tokens - 500  # 500 for response

        # ── Step 1: Inject user memory ──────────────────────────────────
        memory_context = ""
        if self.memory_injection and session_id:
            memory_context = self._get_memory_context(session_id)
            if memory_context:
                available_tokens -= estimate_tokens(memory_context)

        # ── Step 2: Check if history fits ───────────────────────────────
        history_tokens = estimate_history_tokens(history)

        if history_tokens <= available_tokens:
            # History fits — use as-is
            if memory_context:
                messages.append({
                    "role": "system",
                    "content": f"[User Memory]\n{memory_context}\n[End Memory]",
                })
            messages.extend(history)
            return messages

        # ── Step 3: History too long — summarize old messages ────────────
        # Calculate how many recent messages we can keep
        recent_tokens = 0
        recent_start = len(history)
        for i in range(len(history) - 1, -1, -1):
            msg_tokens = estimate_tokens(history[i].get("content", "")) + 4
            if recent_tokens + msg_tokens > available_tokens * 0.7:  # keep 70% for recent
                break
            recent_tokens += msg_tokens
            recent_start = i

        # Ensure minimum recent messages
        recent_start = min(recent_start, len(history) - self.keep_recent_messages)
        recent_start = max(0, recent_start)

        old_messages = history[:recent_start]
        recent_messages = history[recent_start:]

        # ── Step 4: Create compressed context ────────────────────────────
        if memory_context:
            messages.append({
                "role": "system",
                "content": f"[User Memory]\n{memory_context}\n[End Memory]",
            })

        if old_messages:
            # Create a summary placeholder (actual summarization happens async)
            old_summary = self._quick_summarize(old_messages)
            if old_summary:
                messages.append({
                    "role": "system",
                    "content": f"[Earlier Conversation Summary]\n{old_summary}\n[End Summary]",
                })

        messages.extend(recent_messages)

        return messages

    def _get_memory_context(self, session_id: str) -> str:
        """Get user memory facts for context injection."""
        try:
            from .memory import conversation_memory
            context = conversation_memory.get_context_string(session_id)
            return context if context else ""
        except ImportError:
            return ""
        except Exception as e:
            logger.warning(f"Memory injection failed: {e}")
            return ""

    def _quick_summarize(self, messages: List[Dict[str, str]]) -> str:
        """
        Quick extractive summary of old messages.
        Does NOT call LLM — just extracts key facts.
        For full LLM summarization, use the ConversationSummarizer.
        """
        if not messages:
            return ""

        # Extract user questions and key topics
        topics = []
        facts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and content:
                # Keep the user's question/topic
                short = content[:150]
                if "..." not in short:
                    topics.append(short)
            elif role == "assistant" and content:
                # Extract key facts (first sentence of each response)
                first_sentence = content.split(".")[0].split("।")[0].strip()
                if len(first_sentence) > 10:
                    facts.append(first_sentence[:200])

        # Build compact summary
        parts = []
        if topics:
            topics_text = "; ".join(topics[:5])
            parts.append(f"Topics discussed: {topics_text}")
        if facts:
            facts_text = "; ".join(facts[:3])
            parts.append(f"Key points: {facts_text}")

        summary = ". ".join(parts)
        return summary[:500] if summary else ""

    def get_stats(self, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get context window statistics."""
        total_tokens = estimate_history_tokens(history)
        return {
            "message_count": len(history),
            "estimated_tokens": total_tokens,
            "max_tokens": self.max_context_tokens,
            "utilization": f"{total_tokens / self.max_context_tokens * 100:.0f}%",
            "needs_summarization": total_tokens > self.max_context_tokens,
        }


# Module-level singleton
context_manager = ContextManager()
