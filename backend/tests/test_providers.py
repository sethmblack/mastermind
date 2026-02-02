"""Tests for AI provider modules."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.providers.base import BaseProvider, ChatMessage, ProviderResponse, StreamChunk
from src.providers import factory


class TestBaseClasses:
    """Tests for base provider classes."""

    def test_chat_message_creation(self):
        """Test creating a chat message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_message_with_name(self):
        """Test chat message with persona name."""
        msg = ChatMessage(role="assistant", content="Hi", name="einstein")
        assert msg.name == "einstein"

    def test_provider_response_creation(self):
        """Test creating a provider response."""
        resp = ProviderResponse(
            content="Hello!",
            input_tokens=10,
            output_tokens=5,
            model="test-model",
        )
        assert resp.content == "Hello!"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5

    def test_provider_response_total_tokens(self):
        """Test provider response total tokens."""
        resp = ProviderResponse(
            content="Hi",
            input_tokens=100,
            output_tokens=50,
            model="test",
        )
        assert resp.total_tokens == 150

    def test_stream_chunk_creation(self):
        """Test creating a stream chunk."""
        chunk = StreamChunk(content="Hello", is_finished=False)
        assert chunk.content == "Hello"
        assert chunk.is_finished is False

    def test_stream_chunk_finished(self):
        """Test finished stream chunk."""
        chunk = StreamChunk(
            content="Done",
            is_finished=True,
            input_tokens=10,
            output_tokens=5,
            stop_reason="end_turn",
        )
        assert chunk.is_finished is True
        assert chunk.stop_reason == "end_turn"


class TestProviderFactory:
    """Tests for provider factory functions."""

    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            # Clear cached providers
            factory._providers.clear()
            provider = factory.get_provider("anthropic")
            assert provider is not None
            assert provider.provider_name == "anthropic"

    def test_get_openai_provider(self):
        """Test getting OpenAI provider."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            factory._providers.clear()
            provider = factory.get_provider("openai")
            assert provider is not None
            assert provider.provider_name == "openai"

    def test_get_unknown_provider(self):
        """Test getting unknown provider raises error."""
        with pytest.raises(ValueError):
            factory.get_provider("unknown")

    def test_provider_caching(self):
        """Test that providers are cached."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            factory._providers.clear()
            provider1 = factory.get_provider("anthropic")
            provider2 = factory.get_provider("anthropic")
            assert provider1 is provider2

    def test_get_all_models(self):
        """Test getting all models."""
        factory._providers.clear()
        models = factory.get_all_models()
        assert isinstance(models, dict)


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    @pytest.fixture
    def provider(self):
        """Create Anthropic provider with mocked client."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from src.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider(api_key="test-key")
            # Mock the internal _client instead of the property
            provider._client = MagicMock()
            return provider

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "anthropic"

    def test_get_available_models(self, provider):
        """Test getting available models."""
        models = provider.available_models
        assert len(models) > 0
        assert "claude-sonnet-4-20250514" in models

    def test_is_available(self, provider):
        """Test is_available when API key is set."""
        assert provider.is_available() is True

    def test_is_not_available_without_key(self):
        """Test is_available when API key is not set."""
        from src.providers.anthropic import AnthropicProvider
        from src.config import settings
        # Save original value and temporarily clear it
        original_key = settings.anthropic_api_key
        settings.anthropic_api_key = None
        try:
            provider = AnthropicProvider(api_key=None)
            assert provider.is_available() is False
        finally:
            settings.anthropic_api_key = original_key

    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        cost = provider.calculate_cost(1000, 500)
        assert isinstance(cost, float)
        assert cost >= 0

    def test_format_messages(self, provider):
        """Test message formatting."""
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi"),
        ]
        formatted = provider.format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_response(self, provider):
        """Test generating a response."""
        # Create mock response
        mock_text_block = MagicMock()
        mock_text_block.text = "Hello!"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.usage = mock_usage
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"

        # Mock the async messages.create method
        provider._client.messages.create = AsyncMock(return_value=mock_response)

        messages = [ChatMessage(role="user", content="Hi")]
        response = await provider.generate(
            messages=messages,
            system="You are helpful.",
            model="claude-sonnet-4-20250514",
        )

        assert response.content == "Hello!"
        assert response.input_tokens == 10
        assert response.output_tokens == 5

    def test_default_model(self, provider):
        """Test default model."""
        assert provider.default_model == "claude-sonnet-4-20250514"

    def test_pricing_attributes(self, provider):
        """Test pricing attributes are set."""
        assert provider.input_price_per_million > 0
        assert provider.output_price_per_million > 0

    @pytest.mark.asyncio
    async def test_generate_stream(self, provider):
        """Test streaming generation."""
        # Create mock events
        mock_content_event = MagicMock()
        mock_content_event.type = "content_block_delta"
        mock_content_event.delta = MagicMock()
        mock_content_event.delta.text = "Hello"

        mock_start_event = MagicMock()
        mock_start_event.type = "message_start"
        mock_start_event.message = MagicMock()
        mock_start_event.message.usage = MagicMock()
        mock_start_event.message.usage.input_tokens = 10

        mock_delta_event = MagicMock()
        mock_delta_event.type = "message_delta"
        mock_delta_event.usage = MagicMock()
        mock_delta_event.usage.output_tokens = 5
        mock_delta_event.delta = MagicMock()
        mock_delta_event.delta.stop_reason = "end_turn"

        async def mock_stream_iter():
            yield mock_start_event
            yield mock_content_event
            yield mock_delta_event

        # Create mock stream context manager
        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: mock_stream_iter()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        provider._client.messages.stream = MagicMock(return_value=mock_stream_ctx)

        messages = [ChatMessage(role="user", content="Hi")]
        chunks = []
        async for chunk in provider.generate_stream(messages=messages):
            chunks.append(chunk)

        # Should have content chunk and final chunk
        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].is_finished is True


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider with mocked client."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            from src.providers.openai import OpenAIProvider
            provider = OpenAIProvider(api_key="test-key")
            # Mock the internal _client instead of the property
            provider._client = MagicMock()
            return provider

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "openai"

    def test_get_available_models(self, provider):
        """Test getting available models."""
        models = provider.available_models
        assert len(models) > 0
        assert "gpt-4o" in models

    def test_is_available(self, provider):
        """Test is_available when API key is set."""
        assert provider.is_available() is True

    def test_is_not_available_without_key(self):
        """Test is_available when API key is not set."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            from src.providers.openai import OpenAIProvider
            provider = OpenAIProvider(api_key=None)
            assert provider.is_available() is False

    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        cost = provider.calculate_cost(1000, 500)
        assert isinstance(cost, float)
        assert cost >= 0

    def test_format_messages(self, provider):
        """Test message formatting for OpenAI."""
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        ]
        formatted = provider.format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"

    def test_format_messages_with_system(self, provider):
        """Test message formatting with system message."""
        messages = [
            ChatMessage(role="user", content="Hello"),
        ]
        formatted = provider.format_messages(messages, system="You are helpful.")
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are helpful."
        assert formatted[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_response(self, provider):
        """Test generating a response."""
        # Create mock response
        mock_message = MagicMock()
        mock_message.content = "Hello!"

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.model = "gpt-4"
        mock_response.id = "chatcmpl_123"

        # Mock the async chat.completions.create method
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [ChatMessage(role="user", content="Hi")]
        response = await provider.generate(messages=messages, model="gpt-4")

        assert response.content == "Hello!"
        assert response.input_tokens == 10
        assert response.output_tokens == 5

    def test_default_model(self, provider):
        """Test default model."""
        assert provider.default_model == "gpt-4o"

    def test_pricing_attributes(self, provider):
        """Test pricing attributes are set."""
        assert provider.input_price_per_million > 0
        assert provider.output_price_per_million > 0

    @pytest.mark.asyncio
    async def test_generate_stream(self, provider):
        """Test streaming generation."""
        # Create mock chunks
        mock_delta1 = MagicMock()
        mock_delta1.content = "Hello"

        mock_choice1 = MagicMock()
        mock_choice1.delta = mock_delta1
        mock_choice1.finish_reason = None

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [mock_choice1]
        mock_chunk1.usage = None

        mock_delta2 = MagicMock()
        mock_delta2.content = " world"

        mock_choice2 = MagicMock()
        mock_choice2.delta = mock_delta2
        mock_choice2.finish_reason = "stop"

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [mock_choice2]
        mock_chunk2.usage = None

        mock_usage_chunk = MagicMock()
        mock_usage_chunk.choices = []
        mock_usage_chunk.usage = MagicMock()
        mock_usage_chunk.usage.prompt_tokens = 10
        mock_usage_chunk.usage.completion_tokens = 5

        async def mock_stream_iter():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_usage_chunk

        # Create async iterator
        class MockAsyncIterator:
            def __init__(self):
                self._iter = mock_stream_iter()

            def __aiter__(self):
                return self

            async def __anext__(self):
                return await self._iter.__anext__()

        provider._client.chat.completions.create = AsyncMock(return_value=MockAsyncIterator())

        messages = [ChatMessage(role="user", content="Hi")]
        chunks = []
        async for chunk in provider.generate_stream(messages=messages):
            chunks.append(chunk)

        # Should have 2 chunks: content and final
        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].is_finished is True
        assert chunks[1].stop_reason == "stop"


class TestBaseProvider:
    """Tests for BaseProvider methods."""

    def test_get_model_with_valid_model(self):
        """Test get_model with valid model."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from src.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider(api_key="test-key")
            model = provider.get_model("claude-sonnet-4-20250514")
            assert model == "claude-sonnet-4-20250514"

    def test_get_model_with_none_returns_default(self):
        """Test get_model with None returns default."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from src.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider(api_key="test-key")
            model = provider.get_model(None)
            assert model == provider.default_model

    def test_format_messages_basic(self):
        """Test basic message formatting."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            factory._providers.clear()
            provider = factory.get_provider("anthropic")
            messages = [
                ChatMessage(role="user", content="Test"),
            ]
            formatted = provider.format_messages(messages)
            assert formatted[0]["role"] == "user"
            assert formatted[0]["content"] == "Test"
