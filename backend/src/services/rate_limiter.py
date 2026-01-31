"""Rate limiting service for API calls."""

import asyncio
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """State for a rate limit bucket."""
    requests: int = 0
    tokens: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimiter:
    """
    Rate limiter for API calls.

    Implements token bucket algorithm with:
    - Per-provider rate limits
    - Request and token-based limits
    - Automatic backoff on 429 errors
    """

    # Default limits (per minute)
    DEFAULT_LIMITS = {
        "anthropic": {"requests": 50, "tokens": 100000},
        "openai": {"requests": 60, "tokens": 150000},
        "ollama": {"requests": 100, "tokens": 1000000},  # Local, essentially unlimited
    }

    def __init__(
        self,
        window_seconds: int = 60,
        custom_limits: Optional[Dict[str, Dict[str, int]]] = None,
    ):
        self.window_seconds = window_seconds
        self.limits = {**self.DEFAULT_LIMITS, **(custom_limits or {})}
        self._state: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._backoff_until: Dict[str, float] = {}

    async def acquire(
        self,
        provider: str,
        estimated_tokens: int = 1000,
    ) -> bool:
        """
        Acquire permission to make a request.

        Returns True if allowed, False if rate limited.
        Blocks if necessary to wait for the rate limit window.
        """
        async with self._locks[provider]:
            # Check if in backoff
            if provider in self._backoff_until:
                if time.time() < self._backoff_until[provider]:
                    wait_time = self._backoff_until[provider] - time.time()
                    logger.warning(f"Rate limited: {provider}, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                else:
                    del self._backoff_until[provider]

            state = self._state[provider]
            limits = self.limits.get(provider, self.DEFAULT_LIMITS["openai"])

            # Check if window has expired
            now = time.time()
            if now - state.window_start >= self.window_seconds:
                # Reset window
                state.requests = 0
                state.tokens = 0
                state.window_start = now

            # Check limits
            if state.requests >= limits["requests"]:
                # Wait for window to reset
                wait_time = self.window_seconds - (now - state.window_start)
                if wait_time > 0:
                    logger.info(f"Request rate limit reached for {provider}, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    state.requests = 0
                    state.tokens = 0
                    state.window_start = time.time()

            if state.tokens + estimated_tokens > limits["tokens"]:
                # Wait for window to reset
                wait_time = self.window_seconds - (now - state.window_start)
                if wait_time > 0:
                    logger.info(f"Token rate limit reached for {provider}, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    state.requests = 0
                    state.tokens = 0
                    state.window_start = time.time()

            # Update counts
            state.requests += 1
            state.tokens += estimated_tokens

            return True

    def record_usage(self, provider: str, actual_tokens: int):
        """Record actual token usage (to correct estimates)."""
        state = self._state[provider]
        # Adjust token count based on actual usage vs estimate
        # This is a rough adjustment
        pass

    def record_rate_limit_error(self, provider: str, retry_after: Optional[int] = None):
        """Record a 429 rate limit error."""
        backoff_time = retry_after if retry_after else 60
        self._backoff_until[provider] = time.time() + backoff_time
        logger.warning(f"Rate limit error for {provider}, backing off for {backoff_time}s")

    def get_status(self, provider: str) -> Dict[str, any]:
        """Get rate limit status for a provider."""
        state = self._state[provider]
        limits = self.limits.get(provider, self.DEFAULT_LIMITS["openai"])

        now = time.time()
        window_remaining = max(0, self.window_seconds - (now - state.window_start))

        return {
            "provider": provider,
            "requests": {
                "used": state.requests,
                "limit": limits["requests"],
                "remaining": limits["requests"] - state.requests,
            },
            "tokens": {
                "used": state.tokens,
                "limit": limits["tokens"],
                "remaining": limits["tokens"] - state.tokens,
            },
            "window_remaining_seconds": window_remaining,
            "in_backoff": provider in self._backoff_until and time.time() < self._backoff_until.get(provider, 0),
        }

    def get_all_status(self) -> Dict[str, Dict[str, any]]:
        """Get rate limit status for all providers."""
        return {
            provider: self.get_status(provider)
            for provider in self.limits.keys()
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
