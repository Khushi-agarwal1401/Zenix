"""
Conversation Summarizer for Zenix AI.
Compresses old conversation history using LLM-based summarization
before truncation to preserve context.
"""

from typing import List, Dict, Optional
from .llm_client import LLMClient


class ConversationSummarizer:
    """
    Summarizes old conversation messages to preserve context
    when history exceeds the maximum length.
    """

    def __init__(self, keep_recent: int = 10):
        """
        Args:
            keep_recent: Number of recent messages to keep unsummarized.
        """
        self.keep_recent = keep_recent

    def should_summarize(self, history: List[Dict[str, str]], max_messages: int = 40) -> bool:
        """Check if the history needs summarization."""
        return len(history) > max_messages

    def summarize_and_compress(
        self,
        history: List[Dict[str, str]],
        max_messages: int = 40,
        persona: str = "desi",
    ) -> List[Dict[str, str]]:
        """
        Summarize old messages and keep recent ones intact.

        Returns a compressed history list with:
        - A single system message containing the summary
        - The most recent `keep_recent` messages unchanged
        """
        if not self.should_summarize(history, max_messages):
            return history

        # Split into old (to summarize) and recent (to keep)
        split_point = len(history) - self.keep_recent
        old_messages = history[:split_point]
        recent_messages = history[split_point:]

        # Generate summary of old messages
        summary = self._generate_summary(old_messages, persona)

        if summary:
            # Prepend summary as a system context message
            compressed = [
                {
                    "role": "system",
                    "content": f"[Conversation Summary]\n{summary}\n[End Summary — Recent messages follow]",
                }
            ]
            compressed.extend(recent_messages)
            return compressed

        # Fallback: just keep recent messages
        return recent_messages

    def _generate_summary(self, messages: List[Dict[str, str]], persona: str) -> Optional[str]:
        """Use LLM to generate a summary of old messages."""
        if not messages:
            return None

        try:
            llm = LLMClient()

            # Format conversation for summarization
            conversation_text = ""
            for msg in messages:
                role = "User" if msg["role"] == "user" else "Zenix"
                conversation_text += f"{role}: {msg['content'][:500]}\n"

            # Truncate if too long for the summarizer
            if len(conversation_text) > 4000:
                conversation_text = conversation_text[:4000] + "..."

            system_prompt = (
                "You are a conversation summarizer. Create a concise summary of the "
                "following conversation between a user and Zenix AI assistant. "
                "Focus on: key topics discussed, decisions made, important facts mentioned, "
                "and any ongoing tasks or questions. "
                "Keep the summary under 200 words. "
                "Write in third person (e.g., 'The user asked about...', 'Zenix explained...')."
            )

            prompt = (
                f"Summarize this conversation:\n\n{conversation_text}\n\n"
                f"Summary:"
            )

            summary = llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=300,
            )

            if summary and len(summary.strip()) > 20:
                return summary.strip()

        except Exception as e:
            print(f"Summarization failed: {e}")

        return None


# Module-level singleton
conversation_summarizer = ConversationSummarizer(keep_recent=10)
