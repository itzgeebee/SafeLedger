"""
Integration tests for Auth API endpoints.
Tests request/response models and exception mapping.
"""

from datetime import UTC, datetime
from uuid import uuid4


class TestAuthRegisterEndpoint:
    """Tests for POST /api/v1/auth/register"""

    def test_register_request_model(self):
        """RegisterRequest should validate email and password."""
        from app.schemas.auth import RegisterRequest

        request = RegisterRequest(
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
        )

        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"

    def test_register_response_model(self):
        """RegisterResponse should format correctly."""
        from app.schemas.auth import RegisterResponse

        response = RegisterResponse(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
        )

        assert response.email == "test@example.com"
        assert response.message == "Registration successful. Please verify your email."


class TestAuthLoginEndpoint:
    """Tests for POST /api/v1/auth/login"""

    def test_login_request_model(self):
        """LoginRequest should have email and password."""
        from app.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="Password123!",
        )

        assert request.email == "test@example.com"

    def test_login_response_model(self):
        """LoginResponse should include token info."""
        from app.schemas.auth import LoginResponse

        response = LoginResponse(
            access_token="eyJ...",
            token_type="bearer",
            expires_in=3600,
            user_id=uuid4(),
            email="test@example.com",
        )

        assert response.token_type == "bearer"
        assert response.expires_in == 3600


class TestAuthChangePasswordEndpoint:
    """Tests for POST /api/v1/auth/change-password"""

    def test_change_password_request_model(self):
        """ChangePasswordRequest should have current and new password."""
        from app.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="OldPass123!",
            new_password="NewPass123!",
        )

        assert request.current_password == "OldPass123!"
        assert request.new_password == "NewPass123!"


class TestAuthForgotPasswordEndpoint:
    """Tests for POST /api/v1/auth/forgot-password"""

    def test_forgot_password_request_model(self):
        """ForgotPasswordRequest should have email."""
        from app.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="test@example.com")
        assert request.email == "test@example.com"


class TestAuthResetPasswordEndpoint:
    """Tests for POST /api/v1/auth/reset-password"""

    def test_reset_password_request_model(self):
        """ResetPasswordRequest should have token and new password."""
        from app.schemas.auth import ResetPasswordRequest

        request = ResetPasswordRequest(
            token="reset_token_123",
            new_password="NewSecure123!",
        )

        assert request.token == "reset_token_123"


class TestAuthExceptionMapping:
    """Tests for exception to HTTP mapping."""

    def test_map_invalid_credentials(self):
        """InvalidCredentialsError should map to 401."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import InvalidCredentialsError

        exc = InvalidCredentialsError()
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 401

    def test_map_email_exists(self):
        """EmailAlreadyExistsError should map to 409."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import EmailAlreadyExistsError

        exc = EmailAlreadyExistsError()
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 409

    def test_map_account_disabled(self):
        """AccountDisabledError should map to 403."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import AccountDisabledError

        exc = AccountDisabledError()
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 403

    def test_map_password_validation(self):
        """PasswordValidationError should map to 400."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import PasswordValidationError

        exc = PasswordValidationError("Too short")
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 400

    def test_map_user_not_found(self):
        """UserNotFoundError should map to 404."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import UserNotFoundError

        exc = UserNotFoundError()
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 404

    def test_map_reset_token_invalid(self):
        """InvalidResetTokenError should map to 400."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import InvalidResetTokenError

        exc = InvalidResetTokenError()
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 400

    def test_map_generic_auth_error(self):
        """AuthError should map to 400."""
        from app.api.v1.errors import map_auth_exception
        from app.services.auth_service import AuthError

        exc = AuthError("Generic error")
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 400

    def test_map_unknown_exception(self):
        """Unknown exception should map to 500."""
        from app.api.v1.errors import map_auth_exception

        exc = RuntimeError("Unexpected")
        http_exc = map_auth_exception(exc)

        assert http_exc.status_code == 500


class TestUserProfileResponse:
    """Tests for user profile response model."""

    def test_user_profile_response_model(self):
        """UserProfileResponse should include user details."""
        from app.schemas.auth import UserProfileResponse

        response = UserProfileResponse(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            is_verified=True,
            created_at=datetime.now(UTC),
        )

        assert response.email == "test@example.com"
        assert response.is_verified is True


class TestMessageResponse:
    """Tests for MessageResponse model."""

    def test_message_response_model(self):
        """MessageResponse should have message field."""
        from app.schemas.auth import MessageResponse

        response = MessageResponse(message="Success!")
        assert response.message == "Success!"
