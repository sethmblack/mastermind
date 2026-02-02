"""Tests for rate limiter service."""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from src.services.rate_limiter import (
    RateLimitState,
    RateLimiter,
    get_rate_limiter,
    _rate_limiter,
)


class TestRateLimitState:
    """Tests for RateLimitState dataclass."""

    def test_create_rate_limit_state(self):
        """Test creating a RateLimitState."""
        state = RateLimitState()
        assert state.requests == 0
        assert state.tokens == 0
        assert state.window_start > 0

    def test_rate_limit_state_with_values(self):
        """Test RateLimitState with custom values."""
        state = RateLimitState(requests=5, tokens=1000, window_start=100.0)
        assert state.requests == 5
        assert state.tokens == 1000
        assert state.window_start == 100.0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_create_rate_limiter(self):
        """Test creating a RateLimiter."""
        limiter = RateLimiter()
        assert limiter.window_seconds == 60
        assert "anthropic" in limiter.limits
        assert "openai" in limiter.limits

    def test_create_with_custom_window(self):
        """Test creating with custom window."""
        limiter = RateLimiter(window_seconds=30)
        assert limiter.window_seconds == 30

    def test_create_with_custom_limits(self):
        """Test creating with custom limits."""
        custom = {"custom_provider": {"requests": 10, "tokens": 5000}}
        limiter = RateLimiter(custom_limits=custom)
        assert "custom_provider" in limiter.limits
        assert limiter.limits["custom_provider"]["requests"] == 10

    def test_default_limits(self):
        """Test default limits are set."""
        limiter = RateLimiter()
        assert limiter.limits["anthropic"]["requests"] == 50
        assert limiter.limits["anthropic"]["tokens"] == 100000
        assert limiter.limits["openai"]["requests"] == 60

    @pytest.mark.asyncio
    async def test_acquire_first_request(self):
        """Test acquiring permission for first request."""
        limiter = RateLimiter()
        result = await limiter.acquire("anthropic", estimated_tokens=1000)
        assert result is True
        assert limiter._state["anthropic"].requests == 1
        assert limiter._state["anthropic"].tokens == 1000

    @pytest.mark.asyncio
    async def test_acquire_multiple_requests(self):
        """Test acquiring permission for multiple requests."""
        limiter = RateLimiter()

        result1 = await limiter.acquire("anthropic", estimated_tokens=500)
        result2 = await limiter.acquire("anthropic", estimated_tokens=500)

        assert result1 is True
        assert result2 is True
        assert limiter._state["anthropic"].requests == 2
        assert limiter._state["anthropic"].tokens == 1000

    @pytest.mark.asyncio
    async def test_acquire_resets_window(self):
        """Test that acquire resets window when expired."""
        limiter = RateLimiter(window_seconds=1)

        # First request
        await limiter.acquire("anthropic", estimated_tokens=1000)
        assert limiter._state["anthropic"].requests == 1

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Second request - should reset window
        await limiter.acquire("anthropic", estimated_tokens=500)
        assert limiter._state["anthropic"].requests == 1  # Reset to 1
        assert limiter._state["anthropic"].tokens == 500

    @pytest.mark.asyncio
    async def test_acquire_unknown_provider(self):
        """Test acquiring for unknown provider uses default limits."""
        limiter = RateLimiter()
        result = await limiter.acquire("unknown_provider", estimated_tokens=100)
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_with_backoff(self):
        """Test acquire respects backoff."""
        limiter = RateLimiter()

        # Set backoff in the past (should be cleared)
        limiter._backoff_until["anthropic"] = time.time() - 1

        result = await limiter.acquire("anthropic", estimated_tokens=100)
        assert result is True
        assert "anthropic" not in limiter._backoff_until

    def test_record_usage(self):
        """Test recording actual usage."""
        limiter = RateLimiter()
        limiter._state["anthropic"].tokens = 1000

        # record_usage currently does nothing (pass)
        limiter.record_usage("anthropic", 500)
        # Just verifying it doesn't raise

    def test_record_rate_limit_error(self):
        """Test recording rate limit error."""
        limiter = RateLimiter()
        limiter.record_rate_limit_error("anthropic", retry_after=30)

        assert "anthropic" in limiter._backoff_until
        assert limiter._backoff_until["anthropic"] > time.time()

    def test_record_rate_limit_error_default_retry(self):
        """Test recording rate limit error with default retry."""
        limiter = RateLimiter()
        limiter.record_rate_limit_error("anthropic")

        assert "anthropic" in limiter._backoff_until
        # Default is 60 seconds
        assert limiter._backoff_until["anthropic"] >= time.time() + 59

    def test_get_status(self):
        """Test getting status for a provider."""
        limiter = RateLimiter()
        limiter._state["anthropic"].requests = 10
        limiter._state["anthropic"].tokens = 5000
        limiter._state["anthropic"].window_start = time.time()

        status = limiter.get_status("anthropic")

        assert status["provider"] == "anthropic"
        assert status["requests"]["used"] == 10
        assert status["requests"]["limit"] == 50
        assert status["requests"]["remaining"] == 40
        assert status["tokens"]["used"] == 5000
        assert "window_remaining_seconds" in status
        assert status["in_backoff"] is False

    def test_get_status_in_backoff(self):
        """Test getting status when in backoff."""
        limiter = RateLimiter()
        limiter._backoff_until["anthropic"] = time.time() + 30

        status = limiter.get_status("anthropic")
        assert status["in_backoff"] is True

    def test_get_all_status(self):
        """Test getting status for all providers."""
        limiter = RateLimiter()
        all_status = limiter.get_all_status()

        assert "anthropic" in all_status
        assert "openai" in all_status


class TestGlobalRateLimiter:
    """Tests for global rate limiter functions."""

    def test_get_rate_limiter_creates_instance(self):
        """Test get_rate_limiter creates instance."""
        import src.services.rate_limiter as rl_module

        # Reset global
        rl_module._rate_limiter = None

        limiter = get_rate_limiter()
        assert limiter is not None
        assert isinstance(limiter, RateLimiter)

    def test_get_rate_limiter_returns_same_instance(self):
        """Test get_rate_limiter returns same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2


# Need to import asyncio for sleep
import asyncio


class TestRateLimiterWaiting:
    """Tests for rate limiter waiting behavior."""

    @pytest.mark.asyncio
    async def test_acquire_waits_during_backoff(self):
        """Test acquire waits when in active backoff."""
        limiter = RateLimiter(window_seconds=60)

        # Set backoff to 0.1 second in the future
        limiter._backoff_until["anthropic"] = time.time() + 0.1

        start = time.time()
        result = await limiter.acquire("anthropic", estimated_tokens=100)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.05  # Should have waited
        # Backoff entry may still exist but should be expired now

    @pytest.mark.asyncio
    async def test_acquire_waits_on_request_limit(self):
        """Test acquire waits when request limit is reached."""
        limiter = RateLimiter(window_seconds=1)

        # Manually set state to hit request limit
        limiter._state["anthropic"].requests = 50  # Default limit
        limiter._state["anthropic"].window_start = time.time()

        start = time.time()
        result = await limiter.acquire("anthropic", estimated_tokens=100)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.5  # Should have waited for window

    @pytest.mark.asyncio
    async def test_acquire_waits_on_token_limit(self):
        """Test acquire waits when token limit is reached."""
        limiter = RateLimiter(window_seconds=1)

        # Manually set state to hit token limit
        limiter._state["anthropic"].tokens = 99000  # Close to 100000 limit
        limiter._state["anthropic"].window_start = time.time()

        start = time.time()
        result = await limiter.acquire("anthropic", estimated_tokens=2000)  # Would exceed
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.5  # Should have waited for window


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_no_wait_when_backoff_expired(self):
        """Test acquire doesn't wait when backoff has expired."""
        limiter = RateLimiter()

        # Set backoff in the past
        limiter._backoff_until["anthropic"] = time.time() - 10

        start = time.time()
        result = await limiter.acquire("anthropic", estimated_tokens=100)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.5  # Should not have waited significantly

    @pytest.mark.asyncio
    async def test_acquire_request_limit_no_wait_needed(self):
        """Test acquire when at request limit but window expired."""
        limiter = RateLimiter(window_seconds=1)

        # Set state with expired window
        limiter._state["anthropic"].requests = 50
        limiter._state["anthropic"].window_start = time.time() - 2  # Expired

        result = await limiter.acquire("anthropic", estimated_tokens=100)

        assert result is True
        # Window should have been reset
        assert limiter._state["anthropic"].requests == 1

    @pytest.mark.asyncio
    async def test_acquire_token_limit_no_wait_needed(self):
        """Test acquire when at token limit but window expired."""
        limiter = RateLimiter(window_seconds=1)

        # Set state with expired window
        limiter._state["anthropic"].tokens = 100000
        limiter._state["anthropic"].window_start = time.time() - 2  # Expired

        result = await limiter.acquire("anthropic", estimated_tokens=5000)

        assert result is True
        # Window should have been reset
        assert limiter._state["anthropic"].tokens == 5000
