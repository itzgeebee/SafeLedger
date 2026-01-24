"""
Rate limiting middleware using in-memory store.
For production, replace with Redis-backed implementation.
"""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    For production, use Redis with INCR + EXPIRE for distributed rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_seconds = 60

        # In-memory store: {key: [(timestamp, count), ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(self, key: str, now: float) -> None:
        """Remove requests outside the current window."""
        cutoff = now - self.window_seconds
        self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        Returns (allowed, remaining_requests).
        """
        now = time.time()
        self._clean_old_requests(key, now)

        current_count = len(self._requests[key])

        if current_count >= self.requests_per_minute:
            return False, 0

        # Record this request
        self._requests[key].append(now)
        remaining = self.requests_per_minute - current_count - 1

        return True, remaining

    def get_retry_after(self, key: str) -> int:
        """Get seconds until rate limit resets."""
        if not self._requests[key]:
            return 0

        oldest = min(self._requests[key])
        retry_after = int(oldest + self.window_seconds - time.time())
        return max(0, retry_after)


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=60, burst_limit=10)


def get_client_identifier(request: Request) -> str:
    """
    Get unique client identifier for rate limiting.
    Uses X-Forwarded-For if behind proxy, otherwise client IP.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    """
    Rate limiting dependency.
    Raises HTTPException 429 if limit exceeded.
    """
    client_id = get_client_identifier(request)

    allowed, remaining = _rate_limiter.is_allowed(client_id)

    # Add rate limit headers to response
    request.state.rate_limit_remaining = remaining

    if not allowed:
        retry_after = _rate_limiter.get_retry_after(client_id)
        logger.warning(f"Rate limit exceeded for client: {client_id}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(_rate_limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )


class UserRateLimiter:
    """Per-user rate limiter for authenticated endpoints."""

    def __init__(self, requests_per_minute: int = 30):
        self.limiter = RateLimiter(requests_per_minute=requests_per_minute)

    async def __call__(self, request: Request) -> None:
        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)

        if user_id is None:
            # Fall back to IP-based limiting
            key = get_client_identifier(request)
        else:
            key = f"user:{user_id}"

        allowed, remaining = self.limiter.is_allowed(key)

        if not allowed:
            retry_after = self.limiter.get_retry_after(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )


# Pre-configured rate limiters for different use cases
rate_limit_transfers = UserRateLimiter(requests_per_minute=30)
rate_limit_auth = RateLimiter(requests_per_minute=10, burst_limit=3)
