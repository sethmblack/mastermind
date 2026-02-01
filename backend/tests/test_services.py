"""Tests for service modules."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from src.services.token_counter import TokenCounter, SessionUsageTracker, TokenUsageRecord
from src.services.rate_limiter import RateLimiter, get_rate_limiter


class TestTokenCounter:
    """Tests for TokenCounter service."""

    def test_create_token_counter(self):
        """Test creating token counter."""
        counter = TokenCounter()
        assert counter is not None

    def test_count_tokens(self):
        """Test counting tokens."""
        counter = TokenCounter()
        text = "Hello, this is a test message for counting tokens."
        count = counter.count_tokens(text)
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty_string(self):
        """Test counting tokens for empty string."""
        counter = TokenCounter()
        count = counter.count_tokens("")
        assert count == 0

    def test_count_tokens_long_text(self):
        """Test counting tokens for long text."""
        counter = TokenCounter()
        text = "word " * 1000
        count = counter.count_tokens(text)
        assert count > 500

    def test_count_tokens_with_model(self):
        """Test counting tokens with specific model."""
        counter = TokenCounter()
        text = "Hello world"
        count = counter.count_tokens(text, model="gpt-4")
        assert isinstance(count, int)
        assert count > 0

    def test_count_messages_tokens(self):
        """Test counting tokens for messages."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        count = counter.count_messages_tokens(messages)
        assert isinstance(count, int)
        assert count > 0

    def test_calculate_cost_anthropic(self):
        """Test cost calculation for Anthropic."""
        counter = TokenCounter()
        cost = counter.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )
        assert isinstance(cost, float)
        assert cost > 0

    def test_calculate_cost_openai(self):
        """Test cost calculation for OpenAI."""
        counter = TokenCounter()
        cost = counter.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            provider="openai",
            model="gpt-4",
        )
        assert isinstance(cost, float)
        assert cost > 0

    def test_calculate_cost_ollama_free(self):
        """Test cost calculation for Ollama (should be free)."""
        counter = TokenCounter()
        cost = counter.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            provider="ollama",
            model="llama3.1",
        )
        assert cost == 0.0

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        counter = TokenCounter()
        cost = counter.calculate_cost(
            input_tokens=0,
            output_tokens=0,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )
        assert cost == 0.0

    def test_get_model_pricing(self):
        """Test getting model pricing."""
        counter = TokenCounter()
        pricing = counter.get_model_pricing("anthropic", "claude-sonnet-4-20250514")
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] > 0

    def test_estimate_cost(self):
        """Test cost estimation."""
        counter = TokenCounter()
        estimate = counter.estimate_cost(
            text="Hello, this is a test message.",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )
        assert "input_tokens" in estimate
        assert "estimated_output_tokens" in estimate
        assert "estimated_cost" in estimate


class TestSessionUsageTracker:
    """Tests for SessionUsageTracker."""

    def test_create_tracker(self):
        """Test creating session usage tracker."""
        tracker = SessionUsageTracker(session_id=1)
        assert tracker.session_id == 1

    def test_record_usage(self):
        """Test recording token usage."""
        tracker = SessionUsageTracker(session_id=1)
        record = tracker.record_usage(
            persona_name="einstein",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
        )
        assert isinstance(record, TokenUsageRecord)
        assert record.input_tokens == 100
        assert record.output_tokens == 50

    def test_usage_accumulation(self):
        """Test that usage accumulates."""
        tracker = SessionUsageTracker(session_id=1)
        tracker.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        tracker.record_usage("p2", "anthropic", "claude-sonnet-4-20250514", 200, 100)

        summary = tracker.get_summary()
        assert summary["total"]["input_tokens"] == 300
        assert summary["total"]["output_tokens"] == 150

    def test_usage_by_persona(self):
        """Test usage tracking by persona."""
        tracker = SessionUsageTracker(session_id=1)
        tracker.record_usage("einstein", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        tracker.record_usage("feynman", "anthropic", "claude-sonnet-4-20250514", 200, 100)

        summary = tracker.get_summary()
        assert "einstein" in summary["by_persona"]
        assert "feynman" in summary["by_persona"]
        assert summary["by_persona"]["einstein"]["input_tokens"] == 100

    def test_usage_by_provider(self):
        """Test usage tracking by provider."""
        tracker = SessionUsageTracker(session_id=1)
        tracker.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        tracker.record_usage("p2", "openai", "gpt-4", 200, 100)

        summary = tracker.get_summary()
        assert "anthropic" in summary["by_provider"]
        assert "openai" in summary["by_provider"]

    def test_check_budget_ok(self):
        """Test budget check when within budget."""
        tracker = SessionUsageTracker(session_id=1)
        tracker.record_usage("p1", "ollama", "llama3.1", 1000, 500)  # Free

        budget_status = tracker.check_budget(budget=10.0)
        assert budget_status["status"] == "ok"
        assert budget_status["remaining"] == 10.0

    def test_check_budget_warning(self):
        """Test budget check at warning level."""
        tracker = SessionUsageTracker(session_id=1)
        # Manually set cost
        tracker.summary.total_cost = 8.5

        budget_status = tracker.check_budget(budget=10.0)
        assert budget_status["status"] == "warning"

    def test_check_budget_exceeded(self):
        """Test budget check when exceeded."""
        tracker = SessionUsageTracker(session_id=1)
        tracker.summary.total_cost = 11.0

        budget_status = tracker.check_budget(budget=10.0)
        assert budget_status["status"] == "exceeded"


class TestRateLimiter:
    """Tests for RateLimiter service."""

    def test_create_rate_limiter(self):
        """Test creating rate limiter."""
        limiter = RateLimiter()
        assert limiter is not None

    def test_rate_limiter_with_custom_window(self):
        """Test rate limiter with custom window."""
        limiter = RateLimiter(window_seconds=30)
        assert limiter.window_seconds == 30

    def test_rate_limiter_with_custom_limits(self):
        """Test rate limiter with custom limits."""
        limiter = RateLimiter(custom_limits={
            "test_provider": {"requests": 10, "tokens": 5000}
        })
        assert "test_provider" in limiter.limits

    @pytest.mark.asyncio
    async def test_acquire_allows_request(self):
        """Test that acquire allows requests."""
        limiter = RateLimiter()
        allowed = await limiter.acquire("anthropic")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_acquire_with_tokens(self):
        """Test acquire with token estimate."""
        limiter = RateLimiter()
        allowed = await limiter.acquire("anthropic", estimated_tokens=5000)
        assert allowed is True

    def test_get_status(self):
        """Test getting rate limit status."""
        limiter = RateLimiter()
        status = limiter.get_status("anthropic")
        assert "provider" in status
        assert "requests" in status
        assert "tokens" in status
        assert status["provider"] == "anthropic"

    def test_get_all_status(self):
        """Test getting status for all providers."""
        limiter = RateLimiter()
        all_status = limiter.get_all_status()
        assert "anthropic" in all_status
        assert "openai" in all_status
        assert "ollama" in all_status

    def test_record_rate_limit_error(self):
        """Test recording rate limit error."""
        limiter = RateLimiter()
        limiter.record_rate_limit_error("anthropic", retry_after=30)
        assert "anthropic" in limiter._backoff_until

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_default_limits(self):
        """Test default rate limits."""
        limiter = RateLimiter()
        assert limiter.limits["anthropic"]["requests"] == 50
        assert limiter.limits["openai"]["requests"] == 60
