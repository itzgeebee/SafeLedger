"""
Tests for request logging middleware.
"""

from unittest.mock import MagicMock

import pytest


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_generates_request_id_when_missing(self):
        """Should generate request ID when not provided."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        middleware = RequestLoggingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.state = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers

    @pytest.mark.asyncio
    async def test_uses_provided_request_id(self):
        """Should use X-Request-ID from headers if provided."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        middleware = RequestLoggingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {"X-Request-ID": "custom-id-123"}
        mock_request.method = "POST"
        mock_request.url.path = "/api/test"
        mock_request.client.host = "10.0.0.1"
        mock_request.state = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Request-ID"] == "custom-id-123"

    @pytest.mark.asyncio
    async def test_logs_exception_and_reraises(self):
        """Should log exception and re-raise it."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        middleware = RequestLoggingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.method = "GET"
        mock_request.url.path = "/error"
        mock_request.client.host = "127.0.0.1"
        mock_request.state = MagicMock()

        async def mock_call_next(request):
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc:
            await middleware.dispatch(mock_request, mock_call_next)

        assert "Test error" in str(exc.value)

    def test_get_client_ip_with_forwarded(self):
        """Should extract first IP from X-Forwarded-For."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        middleware = RequestLoggingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}

        ip = middleware._get_client_ip(mock_request)

        assert ip == "1.2.3.4"

    def test_get_client_ip_fallback(self):
        """Should fall back to client.host."""
        from app.middleware.request_logging import RequestLoggingMiddleware

        middleware = RequestLoggingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.1"
