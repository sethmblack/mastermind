"""Context management for per-persona token budgets."""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class ContextMessage:
    """A message in the context window."""
    role: str
    content: str
    persona_name: Optional[str] = None
    token_count: int = 0
    importance: float = 1.0  # For prioritizing what to keep


@dataclass
class ContextSummary:
    """A summary of truncated context."""
    content: str
    original_messages: int
    token_count: int


class ContextManager:
    """
    Manages context window and token budget for a single persona.

    Handles:
    - Token counting
    - Context truncation when approaching limits
    - Automatic summarization of older messages
    - Prioritization of important messages
    """

    def __init__(
        self,
        persona_name: str,
        budget: int = 50000,
        model: str = "gpt-4",
        reserve_for_response: int = 2000,
    ):
        self.persona_name = persona_name
        self.budget = budget
        self.reserve_for_response = reserve_for_response

        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

        # Context state
        self.messages: List[ContextMessage] = []
        self.summaries: List[ContextSummary] = []
        self.total_tokens_used = 0

        # Statistics
        self.messages_truncated = 0
        self.summaries_created = 0

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.encoding.encode(text))

    def add_message(
        self,
        role: str,
        content: str,
        persona_name: Optional[str] = None,
        importance: float = 1.0,
    ) -> bool:
        """
        Add a message to the context.

        Returns True if the message fit, False if context was truncated.
        """
        token_count = self.count_tokens(content)

        message = ContextMessage(
            role=role,
            content=content,
            persona_name=persona_name,
            token_count=token_count,
            importance=importance,
        )

        self.messages.append(message)
        self.total_tokens_used += token_count

        # Check if we need to truncate
        available = self.budget - self.reserve_for_response
        if self.total_tokens_used > available:
            self._truncate_context(available)
            return False

        return True

    def _truncate_context(self, target_tokens: int):
        """Truncate context to fit within target token count."""
        if not self.messages:
            return

        # Calculate how many tokens to remove
        excess = self.total_tokens_used - target_tokens

        # Strategy: Remove oldest messages with lowest importance first
        # Always keep the most recent messages

        # Sort messages by (recency, importance) - keep high values
        keep_recent = min(5, len(self.messages))  # Always keep last 5 messages
        recent_messages = self.messages[-keep_recent:]
        older_messages = self.messages[:-keep_recent] if len(self.messages) > keep_recent else []

        if not older_messages:
            # Can't truncate more
            return

        # Sort older messages by importance (ascending) to remove least important first
        older_sorted = sorted(older_messages, key=lambda m: m.importance)

        removed_tokens = 0
        messages_to_remove = []

        for msg in older_sorted:
            if removed_tokens >= excess:
                break
            messages_to_remove.append(msg)
            removed_tokens += msg.token_count

        # Remove selected messages
        for msg in messages_to_remove:
            if msg in self.messages:
                self.messages.remove(msg)
                self.total_tokens_used -= msg.token_count
                self.messages_truncated += 1

        logger.info(
            f"Context truncated for {self.persona_name}: "
            f"removed {len(messages_to_remove)} messages, "
            f"{removed_tokens} tokens"
        )

    async def create_summary(self, provider: Any) -> Optional[ContextSummary]:
        """
        Create a summary of older context to preserve information.

        This can be called proactively to compress context while
        retaining key information.
        """
        if len(self.messages) < 10:
            return None

        # Take oldest 50% of messages
        split_point = len(self.messages) // 2
        to_summarize = self.messages[:split_point]

        if not to_summarize:
            return None

        # Create summary prompt
        summary_content = "\n\n".join([
            f"[{m.persona_name or m.role}]: {m.content[:500]}"
            for m in to_summarize
        ])

        summary_prompt = f"""Summarize the key points from this conversation excerpt in 2-3 concise paragraphs.
Focus on: main topics discussed, key decisions or conclusions, important disagreements or questions raised.

CONVERSATION:
{summary_content}

SUMMARY:"""

        from ..providers.base import ChatMessage

        try:
            response = await provider.generate(
                messages=[ChatMessage(role="user", content=summary_prompt)],
                max_tokens=500,
                temperature=0.3,
            )

            summary = ContextSummary(
                content=response.content,
                original_messages=len(to_summarize),
                token_count=self.count_tokens(response.content),
            )

            # Remove summarized messages
            tokens_freed = sum(m.token_count for m in to_summarize)
            self.messages = self.messages[split_point:]
            self.total_tokens_used -= tokens_freed
            self.total_tokens_used += summary.token_count

            # Add summary as a system message at the start
            self.summaries.append(summary)
            self.summaries_created += 1

            logger.info(
                f"Created summary for {self.persona_name}: "
                f"compressed {len(to_summarize)} messages ({tokens_freed} tokens) "
                f"to {summary.token_count} tokens"
            )

            return summary

        except Exception as e:
            logger.error(f"Error creating summary: {e}")
            return None

    def get_context_for_prompt(
        self,
        system_prompt_tokens: int = 0,
    ) -> List[Dict[str, str]]:
        """
        Get the context formatted for an API call.

        Returns messages that fit within the budget, including
        any summaries as context.
        """
        available = self.budget - self.reserve_for_response - system_prompt_tokens

        # Start with summaries
        context = []
        tokens_used = 0

        # Add summaries as system context
        for summary in self.summaries:
            if tokens_used + summary.token_count > available:
                break
            context.append({
                "role": "system",
                "content": f"[Earlier conversation summary]: {summary.content}",
            })
            tokens_used += summary.token_count

        # Add messages from oldest to newest
        for msg in self.messages:
            if tokens_used + msg.token_count > available:
                break

            formatted = {"role": msg.role, "content": msg.content}
            if msg.persona_name:
                formatted["name"] = msg.persona_name

            context.append(formatted)
            tokens_used += msg.token_count

        return context

    def get_stats(self) -> Dict[str, Any]:
        """Get context management statistics."""
        return {
            "persona_name": self.persona_name,
            "budget": self.budget,
            "tokens_used": self.total_tokens_used,
            "tokens_available": self.budget - self.total_tokens_used,
            "utilization": self.total_tokens_used / self.budget,
            "messages": len(self.messages),
            "summaries": len(self.summaries),
            "messages_truncated": self.messages_truncated,
            "summaries_created": self.summaries_created,
        }

    def get_budget_warning(self) -> Optional[str]:
        """Get a warning if budget is running low."""
        utilization = self.total_tokens_used / self.budget

        if utilization > 0.9:
            return f"CRITICAL: Context {int(utilization * 100)}% full for {self.persona_name}"
        elif utilization > 0.75:
            return f"WARNING: Context {int(utilization * 100)}% full for {self.persona_name}"

        return None

    def reset(self):
        """Reset the context manager."""
        self.messages = []
        self.summaries = []
        self.total_tokens_used = 0
        self.messages_truncated = 0
        self.summaries_created = 0
