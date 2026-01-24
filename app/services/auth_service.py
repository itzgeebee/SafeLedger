"""
Authentication service with bcrypt password hashing.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import SafeLedgerError
from app.models.user import TokenBlacklist, User

logger = logging.getLogger(__name__)


# Custom auth exceptions
class AuthError(SafeLedgerError):
    code = "AUTH_ERROR"
    message = "Authentication error"


class InvalidCredentialsError(AuthError):
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class UserNotFoundError(AuthError):
    code = "USER_NOT_FOUND"
    message = "User not found"


class EmailAlreadyExistsError(AuthError):
    code = "EMAIL_EXISTS"
    message = "Email already registered"


class InvalidResetTokenError(AuthError):
    code = "INVALID_RESET_TOKEN"
    message = "Invalid or expired password reset token"


class AccountDisabledError(AuthError):
    code = "ACCOUNT_DISABLED"
    message = "Account is disabled"


class PasswordValidationError(AuthError):
    code = "PASSWORD_VALIDATION"
    message = "Password does not meet requirements"


def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> None:
    """
    Validate password meets security requirements.
    Raises PasswordValidationError if invalid.
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if len(password) > 128:
        errors.append("Password must be at most 128 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    if errors:
        raise PasswordValidationError("; ".join(errors))


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


class AuthService:
    """Service for user authentication operations."""

    RESET_TOKEN_EXPIRY_HOURS = 1

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """
        Register a new user.

        - Validates password strength
        - Hashes password with bcrypt
        - Checks for duplicate email
        """
        # Normalize email
        email = email.lower().strip()

        # Validate password
        validate_password_strength(password)

        # Hash password
        password_hash = hash_password(password)

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )

        try:
            self.session.add(user)
            await self.session.flush()
            logger.info(f"User registered: {email}")
            return user
        except IntegrityError:
            await self.session.rollback()
            raise EmailAlreadyExistsError(f"Email {email} is already registered")

    async def authenticate(
        self,
        *,
        email: str,
        password: str,
    ) -> User:
        """
        Authenticate user with email and password.
        Returns user if valid, raises exception otherwise.
        """
        email = email.lower().strip()

        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Use constant-time comparison to prevent timing attacks
            # Hash a dummy password to maintain consistent timing
            hash_password("dummy_password_for_timing")
            raise InvalidCredentialsError()

        if not user.is_active:
            raise AccountDisabledError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # Update last login
        user.last_login = datetime.now(UTC)
        await self.session.flush()

        logger.info(f"User authenticated: {email}")
        return user

    async def change_password(
        self,
        *,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change user password.
        Requires current password for verification.
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError()

        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        # Validate new password
        validate_password_strength(new_password)

        # Update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        await self.session.flush()

        logger.info(f"Password changed for user: {user.email}")

    async def request_password_reset(
        self,
        *,
        email: str,
    ) -> str | None:
        """
        Generate password reset token.
        Returns token if user exists, None otherwise.

        Note: Always return success to client to prevent email enumeration.
        """
        email = email.lower().strip()

        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Return None but don't reveal user doesn't exist
            return None

        # Generate reset token
        token = generate_reset_token()
        expires = datetime.now(UTC) + timedelta(hours=self.RESET_TOKEN_EXPIRY_HOURS)

        user.password_reset_token = token
        user.password_reset_expires = expires
        await self.session.flush()

        logger.info(f"Password reset requested for: {email}")
        return token

    async def reset_password(
        self,
        *,
        token: str,
        new_password: str,
    ) -> None:
        """
        Reset password using reset token.
        """
        stmt = select(User).where(
            User.password_reset_token == token,
            User.password_reset_expires > datetime.now(UTC),
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidResetTokenError()

        # Validate new password
        validate_password_strength(new_password)

        # Update password and clear reset token
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.updated_at = datetime.now(UTC)
        await self.session.flush()

        logger.info(f"Password reset completed for: {user.email}")

    async def blacklist_token(
        self,
        *,
        jti: str,
        user_id: UUID,
        token_type: str,
        expires_at: datetime,
    ) -> None:
        """
        Add token to blacklist (for logout).
        """
        blacklist_entry = TokenBlacklist(
            jti=jti,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
        )

        try:
            self.session.add(blacklist_entry)
            await self.session.flush()
            logger.info(f"Token blacklisted for user: {user_id}")
        except IntegrityError:
            # Token already blacklisted, ignore
            await self.session.rollback()

    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        stmt = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke_access_token(
        self,
        token: str,
        secret_key: str,
        user_id: UUID,
    ) -> None:
        """
        Extract JTI and EXP from token and blacklist it.
        """
        from jose import jwt

        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                await self.blacklist_token(
                    jti=jti,
                    user_id=user_id,
                    token_type="ACCESS",
                    expires_at=datetime.fromtimestamp(exp, UTC),
                )
            else:
                logger.warning("Token missing jti or exp during revocation")
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            raise AuthError("Could not process token revocation")

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
