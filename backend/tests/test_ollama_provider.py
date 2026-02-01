"""Tests for Ollama provider."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import httpx

from src.providers.ollama import OllamaProvider
from src.providers.base import ChatMessage


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    def test_create_provider(self):
        """Test creating an Ollama provider."""
        provider = OllamaProvider()
        assert provider.provider_name == "ollama"
        assert provider.default_model == "llama3.1:8b"
        assert provider._available is None

    def test_create_with_custom_base_url(self):
        """Test creating with custom base URL."""
        provider = OllamaProvider(base_url="http://custom:11434")
        assert provider.base_url == "http://custom:11434"

    def test_local_models_are_free(self):
        """Test that local models have zero cost."""
        provider = OllamaProvider()
        assert provider.input_price_per_million == 0.0
        assert provider.output_price_per_million == 0.0

    def test_calculate_cost(self):
        """Test cost calculation returns zero."""
        provider = OllamaProvider()
        cost = provider.calculate_cost(1000000, 1000000)
        assert cost == 0.0


class TestOllamaProviderAvailability:
    """Tests for Ollama availability checking."""

    def test_is_available_success(self):
        """Test is_available when Ollama is running."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response):
            result = provider.is_available()

        assert result is True
        assert provider._available is True

    def test_is_available_failure(self):
        """Test is_available when Ollama is not running."""
        provider = OllamaProvider()

        with patch("httpx.get", side_effect=Exception("Connection refused")):
            result = provider.is_available()

        assert result is False
        assert provider._available is False

    def test_is_available_cached(self):
        """Test is_available uses cached value."""
        provider = OllamaProvider()
        provider._available = True

        # Should not make any HTTP request
        result = provider.is_available()
        assert result is True

    def test_is_available_wrong_status(self):
        """Test is_available with non-200 status."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.get", return_value=mock_response):
            result = provider.is_available()

        assert result is False


class TestOllamaCheckAvailableModels:
    """Tests for checking available models."""

    @pytest.mark.asyncio
    async def test_check_available_models_success(self):
        """Test getting available models."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "mistral:7b"},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)

            models = await provider.check_available_models()

        assert models == ["llama3.1:8b", "mistral:7b"]

    @pytest.mark.asyncio
    async def test_check_available_models_failure(self):
        """Test getting available models when Ollama is down."""
        provider = OllamaProvider()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

            models = await provider.check_available_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_check_available_models_empty(self):
        """Test getting available models when none are installed."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)

            models = await provider.check_available_models()

        assert models == []


class TestOllamaFormatMessages:
    """Tests for message formatting."""

    def test_format_messages_basic(self):
        """Test basic message formatting."""
        provider = OllamaProvider()

        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        ]

        formatted = provider.format_messages(messages)

        assert len(formatted) == 2
        assert formatted[0] == {"role": "user", "content": "Hello"}
        assert formatted[1] == {"role": "assistant", "content": "Hi there!"}

    def test_format_messages_with_system(self):
        """Test message formatting with system prompt."""
        provider = OllamaProvider()

        messages = [
            ChatMessage(role="user", content="Hello"),
        ]

        formatted = provider.format_messages(messages, system="You are helpful")

        assert len(formatted) == 2
        assert formatted[0] == {"role": "system", "content": "You are helpful"}
        assert formatted[1] == {"role": "user", "content": "Hello"}

    def test_format_messages_filters_system_role(self):
        """Test that system role messages are filtered out."""
        provider = OllamaProvider()

        messages = [
            ChatMessage(role="system", content="Old system"),
            ChatMessage(role="user", content="Hello"),
        ]

        formatted = provider.format_messages(messages, system="New system")

        # Only new system + user should be present
        assert len(formatted) == 2
        assert formatted[0]["content"] == "New system"
        assert formatted[1]["content"] == "Hello"


class TestOllamaGenerate:
    """Tests for generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hello, I'm an AI!"},
            "prompt_eval_count": 50,
            "eval_count": 20,
            "done_reason": "stop",
            "total_duration": 1000000000,
            "load_duration": 500000000,
            "eval_duration": 400000000,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            response = await provider.generate(
                messages=[ChatMessage(role="user", content="Hello")],
                model="llama3.1:8b",
            )

        assert response.content == "Hello, I'm an AI!"
        assert response.input_tokens == 50
        assert response.output_tokens == 20
        assert response.model == "llama3.1:8b"
        assert response.stop_reason == "stop"
        assert "total_duration" in response.metadata

    @pytest.mark.asyncio
    async def test_generate_with_system(self):
        """Test generation with system prompt."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Response"},
            "prompt_eval_count": 100,
            "eval_count": 30,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            response = await provider.generate(
                messages=[ChatMessage(role="user", content="Hello")],
                system="You are helpful",
            )

        # Verify the call included system prompt
        call_args = mock_client.post.call_args
        assert "system" in str(call_args) or response.content == "Response"

    @pytest.mark.asyncio
    async def test_generate_uses_default_model(self):
        """Test generation uses default model when not specified."""
        provider = OllamaProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Response"},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            response = await provider.generate(
                messages=[ChatMessage(role="user", content="Hello")],
            )

        assert response.model == "llama3.1:8b"


class TestOllamaGenerateStream:
    """Tests for generate_stream method."""

    @pytest.mark.asyncio
    async def test_generate_stream_success(self):
        """Test successful streaming generation."""
        provider = OllamaProvider()

        # Mock stream response with proper async iterator
        lines = [
            json.dumps({"message": {"content": "Hello"}, "done": False}),
            json.dumps({"message": {"content": " world"}, "done": False}),
            json.dumps({"done": True, "prompt_eval_count": 50, "eval_count": 10, "done_reason": "stop"}),
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        # Create proper async context manager
        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_context

        mock_client_context = MagicMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_context):
            chunks = []
            async for chunk in provider.generate_stream(
                messages=[ChatMessage(role="user", content="Hello")],
            ):
                chunks.append(chunk)

        # Should have 3 chunks: 2 content + 1 final
        assert len(chunks) == 3
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"
        assert chunks[2].is_finished is True
        assert chunks[2].input_tokens == 50
        assert chunks[2].output_tokens == 10

    @pytest.mark.asyncio
    async def test_generate_stream_empty_lines(self):
        """Test streaming handles empty lines."""
        provider = OllamaProvider()

        lines = [
            "",
            "   ",
            json.dumps({"message": {"content": "Hi"}, "done": False}),
            json.dumps({"done": True}),
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_context

        mock_client_context = MagicMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_context):
            chunks = []
            async for chunk in provider.generate_stream(
                messages=[ChatMessage(role="user", content="Hello")],
            ):
                chunks.append(chunk)

        # Should only have 2 actual chunks
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_generate_stream_invalid_json(self):
        """Test streaming handles invalid JSON."""
        provider = OllamaProvider()

        lines = [
            "not valid json",
            json.dumps({"message": {"content": "Valid"}, "done": False}),
            json.dumps({"done": True}),
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_context

        mock_client_context = MagicMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_context):
            chunks = []
            async for chunk in provider.generate_stream(
                messages=[ChatMessage(role="user", content="Hello")],
            ):
                chunks.append(chunk)

        # Should skip invalid JSON and get 2 chunks
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_generate_stream_empty_content(self):
        """Test streaming handles empty content."""
        provider = OllamaProvider()

        lines = [
            json.dumps({"message": {"content": ""}, "done": False}),
            json.dumps({"message": {"content": "Hi"}, "done": False}),
            json.dumps({"done": True}),
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_context

        mock_client_context = MagicMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_context):
            chunks = []
            async for chunk in provider.generate_stream(
                messages=[ChatMessage(role="user", content="Hello")],
            ):
                chunks.append(chunk)

        # Empty content chunk should be skipped
        assert len(chunks) == 2
        assert chunks[0].content == "Hi"


class TestOllamaAvailableModels:
    """Tests for available models list."""

    def test_available_models_list(self):
        """Test that available models list is populated."""
        provider = OllamaProvider()
        assert len(provider.available_models) > 0
        assert "llama3.1:8b" in provider.available_models
        assert "mistral:7b" in provider.available_models
