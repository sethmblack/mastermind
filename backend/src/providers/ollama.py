"""Ollama provider for local models."""

import logging
from typing import AsyncIterator, List, Optional, Dict, Any
import httpx
import json

from .base import BaseProvider, ProviderResponse, StreamChunk, ChatMessage
from ..config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Provider for local Ollama models."""

    provider_name = "ollama"
    default_model = "llama3.2:3b"
    available_models = [
        "llama3.2:3b",
    ]

    # Local models are free
    input_price_per_million = 0.0
    output_price_per_million = 0.0

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        super().__init__(None, **kwargs)
        self.base_url = base_url or settings.ollama_base_url
        self._available = None

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        if self._available is not None:
            return self._available
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            self._available = response.status_code == 200
        except Exception:
            self._available = False
        return self._available

    async def check_available_models(self) -> List[str]:
        """Get list of actually available models from Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to get Ollama models: {e}")
        return []

    def format_messages(self, messages: List[ChatMessage], system: Optional[str] = None) -> List[Dict[str, str]]:
        """Format messages for Ollama API."""
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
        """Generate a complete response from Ollama."""
        model = model or self.default_model
        formatted_messages = self.format_messages(messages, system)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")

        # Ollama provides token counts in the response
        prompt_eval_count = data.get("prompt_eval_count", 0)
        eval_count = data.get("eval_count", 0)

        return ProviderResponse(
            content=content,
            input_tokens=prompt_eval_count,
            output_tokens=eval_count,
            model=model,
            stop_reason=data.get("done_reason"),
            metadata={
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "eval_duration": data.get("eval_duration"),
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
        """Generate a streaming response from Ollama."""
        model = model or self.default_model
        formatted_messages = self.format_messages(messages, system)

        input_tokens = 0
        output_tokens = 0

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": formatted_messages,
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
                timeout=120.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if data.get("done"):
                        input_tokens = data.get("prompt_eval_count", 0)
                        output_tokens = data.get("eval_count", 0)
                        yield StreamChunk(
                            content="",
                            is_finished=True,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            stop_reason=data.get("done_reason"),
                        )
                    else:
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield StreamChunk(
                                content=content,
                                is_finished=False,
                            )
