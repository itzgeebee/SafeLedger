"""
Unit tests for AuthService.
Tests password hashing, validation, registration, and authentication.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.auth_service import (
    AccountDisabledError,
    AuthService,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    PasswordValidationError,
    UserNotFoundError,
    generate_reset_token,
    hash_password,
    validate_password_strength,
    verify_password,
)

# ============================================================
# Password Hashing Tests
# ============================================================


class TestPasswordHashing:
    def test_hash_password_returns_different_hash_each_time(self):
        """bcrypt should produce different hashes due to salt."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_verify_password_correct(self):
        """Correct password should verify."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should not verify."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_password_invalid_hash(self):
        """Invalid hash should return False, not raise."""
        assert verify_password("password", "invalid_hash") is False

    def test_verify_password_empty_string(self):
        """Empty password should not verify against valid hash."""
        hashed = hash_password("RealPassword123!")
        assert verify_password("", hashed) is False


# ============================================================
# Password Validation Tests
# ============================================================


class TestPasswordValidation:
    def test_valid_password(self):
        """Valid password should not raise."""
        validate_password_strength("SecurePass123!")  # Should not raise

    def test_password_too_short(self):
        """Password under 8 chars should fail."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password_strength("Ab1!")
        assert "at least 8 characters" in str(exc.value)

    def test_password_too_long(self):
        """Password over 128 chars should fail."""
        long_password = "A1!" + "a" * 130
        with pytest.raises(PasswordValidationError) as exc:
            validate_password_strength(long_password)
        assert "at most 128 characters" in str(exc.value)

    def test_password_missing_uppercase(self):
        """Password without uppercase should fail."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password_strength("lowercase123!")
        assert "uppercase" in str(exc.value)

    def test_password_missing_lowercase(self):
        """Password without lowercase should fail."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password_strength("UPPERCASE123!")
        assert "lowercase" in str(exc.value)

    def test_password_missing_number(self):
        """Password without number should fail."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password_strength("NoNumbers!!")
        assert "number" in str(exc.value)

    def test_password_missing_special_char(self):
        """Password without special char should fail."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password_strength("NoSpecial123")
        assert "special character" in str(exc.value)


# ============================================================
# Reset Token Tests
# ============================================================


class TestResetToken:
    def test_generate_reset_token_unique(self):
        """Each token should be unique."""
        token1 = generate_reset_token()
        token2 = generate_reset_token()

        assert token1 != token2
        assert len(token1) > 20  # Should be sufficiently long


# ============================================================
# AuthService Tests
# ============================================================


class TestAuthServiceRegister:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_register_success(self, mock_session):
        """Successful registration should return user."""
        service = AuthService(mock_session)

        user = await service.register(
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
        )

        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.password_hash != "SecurePass123!"  # Should be hashed
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_normalizes_email(self, mock_session):
        """Email should be lowercased and trimmed."""
        service = AuthService(mock_session)

        user = await service.register(
            email="  TEST@EXAMPLE.COM  ",
            password="SecurePass123!",
        )

        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_register_weak_password_fails(self, mock_session):
        """Weak password should raise PasswordValidationError."""
        service = AuthService(mock_session)

        with pytest.raises(PasswordValidationError):
            await service.register(
                email="test@example.com",
                password="weak",
            )

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, mock_session):
        """Duplicate email should raise EmailAlreadyExistsError."""
        from sqlalchemy.exc import IntegrityError

        mock_session.flush.side_effect = IntegrityError(None, None, None)
        service = AuthService(mock_session)

        with pytest.raises(EmailAlreadyExistsError):
            await service.register(
                email="test@example.com",
                password="SecurePass123!",
            )


class TestAuthServiceAuthenticate:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_authenticate_success(self, mock_session):
        """Valid credentials should return user."""
        # Create mock user
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = hash_password("SecurePass123!")
        mock_user.is_active = True
        mock_user.last_login = None

        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        user = await service.authenticate(
            email="test@example.com",
            password="SecurePass123!",
        )

        assert user == mock_user
        assert user.last_login is not None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, mock_session):
        """Non-existent user should raise InvalidCredentialsError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate(
                email="nonexistent@example.com",
                password="AnyPassword123!",
            )

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, mock_session):
        """Wrong password should raise InvalidCredentialsError."""
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = hash_password("CorrectPass123!")
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate(
                email="test@example.com",
                password="WrongPassword123!",
            )

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, mock_session):
        """Inactive user should raise AccountDisabledError."""
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = hash_password("SecurePass123!")
        mock_user.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with pytest.raises(AccountDisabledError):
            await service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
            )


class TestAuthServiceChangePassword:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_change_password_success(self, mock_session):
        """Valid current password should allow change."""
        user_id = uuid4()
        old_hash = hash_password("OldPassword123!")

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.password_hash = old_hash
        mock_user.updated_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        await service.change_password(
            user_id=user_id,
            current_password="OldPassword123!",
            new_password="NewPassword123!",
        )

        # Password should be updated
        assert mock_user.password_hash != old_hash
        assert verify_password("NewPassword123!", mock_user.password_hash)

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, mock_session):
        """Non-existent user should raise UserNotFoundError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with pytest.raises(UserNotFoundError):
            await service.change_password(
                user_id=uuid4(),
                current_password="OldPassword123!",
                new_password="NewPassword123!",
            )

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, mock_session):
        """Wrong current password should raise InvalidCredentialsError."""
        mock_user = MagicMock()
        mock_user.password_hash = hash_password("CorrectPassword123!")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with pytest.raises(InvalidCredentialsError):
            await service.change_password(
                user_id=uuid4(),
                current_password="WrongPassword123!",
                new_password="NewPassword123!",
            )


class TestAuthServicePasswordReset:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_request_password_reset_user_exists(self, mock_session):
        """Existing user should get reset token."""
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_reset_token = None
        mock_user.password_reset_expires = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        token = await service.request_password_reset(email="test@example.com")

        assert token is not None
        assert mock_user.password_reset_token == token
        assert mock_user.password_reset_expires is not None

    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_found(self, mock_session):
        """Non-existent user should return None (no error)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        token = await service.request_password_reset(email="nonexistent@example.com")

        assert token is None

    @pytest.mark.asyncio
    async def test_reset_password_valid_token(self, mock_session):
        """Valid token should reset password."""
        mock_user = MagicMock()
        mock_user.password_reset_token = "valid_token"
        mock_user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
        mock_user.password_hash = hash_password("OldPassword123!")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        await service.reset_password(
            token="valid_token",
            new_password="NewPassword123!",
        )

        assert mock_user.password_reset_token is None
        assert mock_user.password_reset_expires is None
        assert verify_password("NewPassword123!", mock_user.password_hash)

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, mock_session):
        """Invalid token should raise InvalidResetTokenError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with pytest.raises(InvalidResetTokenError):
            await service.reset_password(
                token="invalid_token",
                new_password="NewPassword123!",
            )


class TestAuthServiceTokenBlacklist:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_blacklist_token(self, mock_session):
        """Token should be added to blacklist."""
        service = AuthService(mock_session)

        await service.blacklist_token(
            jti="test_jti",
            user_id=uuid4(),
            token_type="ACCESS",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, mock_session):
        """Blacklisted token should return True."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Token exists
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        result = await service.is_token_blacklisted("test_jti")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, mock_session):
        """Non-blacklisted token should return False."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        result = await service.is_token_blacklisted("test_jti")

        assert result is False
