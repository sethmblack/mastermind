"""Base provider interface for AI model providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional, Dict, Any
from enum import Enum


@dataclass
class StreamChunk:
    """A chunk of streaming response."""
    content: str
    is_finished: bool = False
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    stop_reason: Optional[str] = None


@dataclass
class ProviderResponse:
    """Complete response from a provider."""
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    stop_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ChatMessage:
    """A message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None  # For multi-agent identification


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    # Provider identification
    provider_name: str = "base"

    # Default models
    default_model: str = ""
    available_models: List[str] = []

    # Pricing (per 1M tokens)
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs,
    ) -> ProviderResponse:
        """Generate a complete response."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response."""
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of a request in USD."""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_million
        return input_cost + output_cost

    def get_model(self, model: Optional[str] = None) -> str:
        """Get the model to use, falling back to default."""
        if model and model in self.available_models:
            return model
        return self.default_model

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        pass

    def format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Format messages for the provider's API."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role != "system"  # System messages handled separately
        ]
