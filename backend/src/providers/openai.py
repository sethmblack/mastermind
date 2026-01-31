"""OpenAI provider implementation."""

import logging
from typing import AsyncIterator, List, Optional, Dict, Any

from .base import BaseProvider, ProviderResponse, StreamChunk, ChatMessage
from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI models."""

    provider_name = "openai"
    default_model = "gpt-4o"
    available_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini",
    ]

    # Pricing per 1M tokens (GPT-4o)
    input_price_per_million = 2.5
    output_price_per_million = 10.0

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key or settings.openai_api_key, **kwargs)
        self._client = None

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed")
        return self._client

    def is_available(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.api_key)

    def format_messages(self, messages: List[ChatMessage], system: Optional[str] = None) -> List[Dict[str, str]]:
        """Format messages for OpenAI API, including system message."""
        formatted = []
        if system:
            formatted.append({"role": "system", "content": system})
        for msg in messages:
            if msg.role != "system":
                formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    async def generate(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs,
    ) -> ProviderResponse:
        """Generate a complete response from OpenAI."""
        model = self.get_model(model)
        formatted_messages = self.format_messages(messages, system)

        response = await self.client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        choice = response.choices[0]
        content = choice.message.content or ""

        return ProviderResponse(
            content=content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=model,
            stop_reason=choice.finish_reason,
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
        """Generate a streaming response from OpenAI."""
        model = self.get_model(model)
        formatted_messages = self.format_messages(messages, system)

        stream = await self.client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
            **kwargs,
        )

        input_tokens = 0
        output_tokens = 0

        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta
                content = delta.content or ""

                if choice.finish_reason:
                    # Final chunk
                    yield StreamChunk(
                        content=content,
                        is_finished=True,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        stop_reason=choice.finish_reason,
                    )
                elif content:
                    yield StreamChunk(
                        content=content,
                        is_finished=False,
                    )

            # Usage info comes in a separate chunk
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens
