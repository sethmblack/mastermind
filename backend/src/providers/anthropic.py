"""Anthropic Claude provider implementation."""

import logging
from typing import AsyncIterator, List, Optional, Dict, Any

from .base import BaseProvider, ProviderResponse, StreamChunk, ChatMessage
from ..config import settings

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""

    provider_name = "anthropic"
    default_model = "claude-sonnet-4-20250514"
    available_models = [
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ]

    # Pricing per 1M tokens (approximate)
    input_price_per_million = 3.0  # Sonnet pricing
    output_price_per_million = 15.0

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key or settings.anthropic_api_key, **kwargs)
        self._client = None

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed")
        return self._client

    def is_available(self) -> bool:
        """Check if Anthropic is configured."""
        return bool(self.api_key)

    async def generate(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs,
    ) -> ProviderResponse:
        """Generate a complete response from Claude."""
        model = self.get_model(model)
        formatted_messages = self.format_messages(messages)

        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=formatted_messages,
            **kwargs,
        )

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return ProviderResponse(
            content=content,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
            stop_reason=response.stop_reason,
            metadata={
                "id": response.id,
            },
        )

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Claude."""
        model = self.get_model(model)
        formatted_messages = self.format_messages(messages)

        input_tokens = 0
        output_tokens = 0

        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=formatted_messages,
            **kwargs,
        ) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield StreamChunk(
                                content=event.delta.text,
                                is_finished=False,
                            )
                    elif event.type == "message_start":
                        if hasattr(event.message, "usage"):
                            input_tokens = event.message.usage.input_tokens
                    elif event.type == "message_delta":
                        if hasattr(event, "usage"):
                            output_tokens = event.usage.output_tokens
                        yield StreamChunk(
                            content="",
                            is_finished=True,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            stop_reason=getattr(event.delta, "stop_reason", None),
                        )
