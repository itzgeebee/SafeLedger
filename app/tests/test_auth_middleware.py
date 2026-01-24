"""
Unit tests for auth middleware - JWT handling.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.middleware.auth import (
    CurrentUser,
    TokenData,
    create_access_token,
    require_scope,
)


class TestCreateAccessToken:
    def test_create_token_returns_string(self):
        """Token should be a non-empty string."""
        token = create_access_token("user123")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_scopes(self):
        """Token with scopes should be created."""
        token = create_access_token("user123", scopes=["read", "write"])

        assert isinstance(token, str)

    def test_create_token_with_custom_expiry(self):
        """Token with custom expiry should be created."""
        token = create_access_token(
            "user123",
            expires_delta=timedelta(hours=2),
        )

        assert isinstance(token, str)


class TestCurrentUser:
    def test_has_scope_true(self):
        """User with scope should return True."""
        user = CurrentUser(user_id="user123", scopes=["read", "write"])

        assert user.has_scope("read") is True
        assert user.has_scope("write") is True

    def test_has_scope_false(self):
        """User without scope should return False."""
        user = CurrentUser(user_id="user123", scopes=["read"])

        assert user.has_scope("admin") is False

    def test_admin_has_all_scopes(self):
        """Admin user should have all scopes."""
        user = CurrentUser(user_id="admin123", scopes=["admin"])

        assert user.has_scope("read") is True
        assert user.has_scope("write") is True
        assert user.has_scope("anything") is True


class TestRequireScope:
    @pytest.mark.asyncio
    async def test_require_scope_passes_with_scope(self):
        """User with required scope should pass."""
        checker = require_scope("write")
        user = CurrentUser(user_id="user123", scopes=["read", "write"])

        # Mock the dependency injection
        # In practice, this would come from Depends(verify_jwt)
        result = await checker(user)

        assert result == user

    @pytest.mark.asyncio
    async def test_require_scope_fails_without_scope(self):
        """User without required scope should raise 403."""
        checker = require_scope("admin")
        user = CurrentUser(user_id="user123", scopes=["read"])

        with pytest.raises(HTTPException) as exc:
            await checker(user)

        assert exc.value.status_code == 403
        assert "admin" in exc.value.detail


class TestTokenData:
    def test_token_data_creation(self):
        """TokenData should be creatable from dict."""
        data = TokenData(
            sub="user123",
            jti="test-jti",
            exp=datetime.now(UTC) + timedelta(hours=1),
            iat=datetime.now(UTC),
            scopes=["read"],
        )

        assert data.sub == "user123"
        assert len(data.scopes) == 1

    def test_token_data_default_scopes(self):
        """TokenData should have empty scopes by default."""
        data = TokenData(
            sub="user123",
            jti="test-jti",
            exp=datetime.now(UTC),
            iat=datetime.now(UTC),
        )

        assert data.scopes == []
