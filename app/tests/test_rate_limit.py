"""
Unit tests for rate limiting middleware.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.middleware.rate_limit import (
    RateLimiter,
    UserRateLimiter,
    get_client_identifier,
)


class TestRateLimiter:
    def test_first_request_allowed(self):
        """First request should be allowed."""
        limiter = RateLimiter(requests_per_minute=60)

        allowed, remaining = limiter.is_allowed("client1")

        assert allowed is True
        assert remaining == 59

    def test_requests_within_limit_allowed(self):
        """Requests within limit should be allowed."""
        limiter = RateLimiter(requests_per_minute=10)

        for i in range(10):
            allowed, remaining = limiter.is_allowed("client1")
            assert allowed is True
            assert remaining == 10 - i - 1

    def test_requests_exceeding_limit_blocked(self):
        """Requests exceeding limit should be blocked."""
        limiter = RateLimiter(requests_per_minute=5)

        # Use up the limit
        for _ in range(5):
            limiter.is_allowed("client1")

        # Next request should be blocked
        allowed, remaining = limiter.is_allowed("client1")

        assert allowed is False
        assert remaining == 0

    def test_different_clients_have_separate_limits(self):
        """Different clients should have separate limits."""
        limiter = RateLimiter(requests_per_minute=2)

        # Client 1 uses up limit
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        allowed1, _ = limiter.is_allowed("client1")

        # Client 2 should still have allowance
        allowed2, remaining = limiter.is_allowed("client2")

        assert allowed1 is False
        assert allowed2 is True
        assert remaining == 1

    def test_get_retry_after(self):
        """Should return seconds until reset."""
        limiter = RateLimiter(requests_per_minute=1)

        limiter.is_allowed("client1")
        retry_after = limiter.get_retry_after("client1")

        assert retry_after > 0
        assert retry_after <= 60

    def test_get_retry_after_no_requests(self):
        """Should return 0 when no requests made."""
        limiter = RateLimiter(requests_per_minute=10)

        retry_after = limiter.get_retry_after("new_client")

        assert retry_after == 0


class TestGetClientIdentifier:
    def test_uses_client_host_by_default(self):
        """Should use client host when no X-Forwarded-For."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"

        identifier = get_client_identifier(mock_request)

        assert identifier == "192.168.1.1"

    def test_uses_x_forwarded_for_when_present(self):
        """Should use X-Forwarded-For when present."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}

        identifier = get_client_identifier(mock_request)

        assert identifier == "10.0.0.1"

    def test_handles_single_x_forwarded_for(self):
        """Should handle single IP in X-Forwarded-For."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1"}

        identifier = get_client_identifier(mock_request)

        assert identifier == "10.0.0.1"

    def test_handles_missing_client(self):
        """Should return 'unknown' when client is None."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        identifier = get_client_identifier(mock_request)

        assert identifier == "unknown"


class TestUserRateLimiter:
    @pytest.mark.asyncio
    async def test_uses_user_id_when_available(self):
        """Should use user ID for rate limiting when available."""
        limiter = UserRateLimiter(requests_per_minute=10)

        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        mock_request.headers = {}
        mock_request.client = None

        # Should not raise
        await limiter(mock_request)

    @pytest.mark.asyncio
    async def test_falls_back_to_ip_when_no_user(self):
        """Should fall back to IP when no user ID."""
        limiter = UserRateLimiter(requests_per_minute=10)

        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user_id attribute
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"

        # Should not raise
        await limiter(mock_request)

    @pytest.mark.asyncio
    async def test_raises_429_when_exceeded(self):
        """Should raise 429 when limit exceeded."""
        limiter = UserRateLimiter(requests_per_minute=1)

        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        mock_request.headers = {}
        mock_request.client = None

        # First request succeeds
        await limiter(mock_request)

        # Second request should fail
        with pytest.raises(HTTPException) as exc:
            await limiter(mock_request)

        assert exc.value.status_code == 429
