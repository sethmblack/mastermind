"""Token counting and cost tracking service."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import tiktoken

logger = logging.getLogger(__name__)


# Pricing per 1M tokens (as of 2024)
PRICING = {
    "anthropic": {
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-5-haiku-20241022": {"input": 0.8, "output": 4.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    },
    "openai": {
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "o1-preview": {"input": 15.0, "output": 60.0},
        "o1-mini": {"input": 3.0, "output": 12.0},
    },
}


@dataclass
class TokenUsageRecord:
    """Record of token usage."""
    persona_name: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: Optional[str] = None


@dataclass
class SessionUsageSummary:
    """Summary of session token usage."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    by_persona: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_provider: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    records: List[TokenUsageRecord] = field(default_factory=list)


class TokenCounter:
    """
    Service for counting tokens and tracking costs.

    Provides:
    - Token counting for various models
    - Cost calculation
    - Usage aggregation and reporting
    """

    def __init__(self):
        # Cache tokenizers
        self._encodings: Dict[str, tiktoken.Encoding] = {}

    def get_encoding(self, model: str) -> tiktoken.Encoding:
        """Get or create tokenizer for a model."""
        if model not in self._encodings:
            try:
                self._encodings[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback for unknown models
                self._encodings[model] = tiktoken.get_encoding("cl100k_base")
        return self._encodings[model]

    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Count tokens in text for a specific model."""
        encoding = self.get_encoding(model)
        return len(encoding.encode(text))

    def count_messages_tokens(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
    ) -> int:
        """Count tokens for a list of messages."""
        encoding = self.get_encoding(model)

        # Token overhead per message varies by model
        # This is an approximation
        tokens_per_message = 4  # <|im_start|>{role}\n{content}<|im_end|>

        total = 0
        for message in messages:
            total += tokens_per_message
            for key, value in message.items():
                total += len(encoding.encode(str(value)))

        total += 3  # Reply priming
        return total

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str,
    ) -> float:
        """Calculate cost in USD for token usage."""
        provider_pricing = PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model, provider_pricing.get("default", {"input": 0, "output": 0}))

        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost

    def get_model_pricing(self, provider: str, model: str) -> Dict[str, float]:
        """Get pricing information for a model."""
        provider_pricing = PRICING.get(provider, {})
        return provider_pricing.get(model, provider_pricing.get("default", {"input": 0, "output": 0}))

    def estimate_cost(
        self,
        text: str,
        provider: str,
        model: str,
        response_multiplier: float = 1.5,
    ) -> Dict[str, Any]:
        """Estimate cost for processing text (before making API call)."""
        input_tokens = self.count_tokens(text, model)
        estimated_output = int(input_tokens * response_multiplier)

        cost = self.calculate_cost(input_tokens, estimated_output, provider, model)

        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output,
            "estimated_cost": cost,
            "pricing": self.get_model_pricing(provider, model),
        }


class SessionUsageTracker:
    """Tracks token usage for a session."""

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.summary = SessionUsageSummary()
        self.token_counter = TokenCounter()

    def record_usage(
        self,
        persona_name: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> TokenUsageRecord:
        """Record token usage."""
        cost = self.token_counter.calculate_cost(
            input_tokens, output_tokens, provider, model
        )

        record = TokenUsageRecord(
            persona_name=persona_name,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

        # Update summary
        self.summary.total_input_tokens += input_tokens
        self.summary.total_output_tokens += output_tokens
        self.summary.total_cost += cost
        self.summary.records.append(record)

        # By persona
        if persona_name not in self.summary.by_persona:
            self.summary.by_persona[persona_name] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        self.summary.by_persona[persona_name]["input_tokens"] += input_tokens
        self.summary.by_persona[persona_name]["output_tokens"] += output_tokens
        self.summary.by_persona[persona_name]["cost"] += cost

        # By provider
        if provider not in self.summary.by_provider:
            self.summary.by_provider[provider] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        self.summary.by_provider[provider]["input_tokens"] += input_tokens
        self.summary.by_provider[provider]["output_tokens"] += output_tokens
        self.summary.by_provider[provider]["cost"] += cost

        return record

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "session_id": self.session_id,
            "total": {
                "input_tokens": self.summary.total_input_tokens,
                "output_tokens": self.summary.total_output_tokens,
                "total_tokens": self.summary.total_input_tokens + self.summary.total_output_tokens,
                "cost": round(self.summary.total_cost, 4),
            },
            "by_persona": self.summary.by_persona,
            "by_provider": self.summary.by_provider,
        }

    def check_budget(self, budget: float) -> Dict[str, Any]:
        """Check if usage is within budget."""
        remaining = budget - self.summary.total_cost
        utilization = self.summary.total_cost / budget if budget > 0 else 0

        return {
            "budget": budget,
            "used": self.summary.total_cost,
            "remaining": remaining,
            "utilization": utilization,
            "status": "ok" if utilization < 0.8 else "warning" if utilization < 1.0 else "exceeded",
        }
