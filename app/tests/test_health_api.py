"""
Tests for Health API endpoints.
"""

from unittest.mock import AsyncMock

import pytest


class TestHealthEndpoint:
    """Tests for GET /health"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Health endpoint should return ok status."""
        from app.api.v1.health import health

        response = await health()

        assert response["status"] == "ok"


class TestReadinessEndpoint:
    """Tests for GET /health/ready"""

    @pytest.mark.asyncio
    async def test_readiness_success(self):
        """Readiness should return ok when DB is connected."""
        from app.api.v1.health import readiness

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        response = await readiness(mock_db)

        assert response["status"] == "ok"
        assert response["database"] == "connected"

    @pytest.mark.asyncio
    async def test_readiness_db_failure(self):
        """Readiness should return degraded when DB fails."""
        from app.api.v1.health import readiness

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Connection failed"))

        response = await readiness(mock_db)

        assert response["status"] == "degraded"
        assert response["database"] == "disconnected"
        assert "Connection failed" in response["error"]
