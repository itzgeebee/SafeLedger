"""
Authentication API endpoints.
"""

import logging
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import map_auth_exception
from app.config import get_settings
from app.db.db import get_db
from app.middleware.auth import (
    CurrentUser,
    create_access_token,
    security,
    verify_jwt,
)
from app.middleware.rate_limit import rate_limit
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    UserProfileResponse,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit)],
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    Password requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    auth_service = AuthService(db)

    try:
        user = await auth_service.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
        await db.commit()

        return RegisterResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
        )
    except Exception as e:
        await db.rollback()
        raise map_auth_exception(e)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit)],
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT access token.
    """
    auth_service = AuthService(db)

    try:
        user = await auth_service.authenticate(
            email=payload.email,
            password=payload.password,
        )
        await db.commit()

        # Create access token
        settings = get_settings()

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        access_token = create_access_token(
            user_id=str(user.id),
            scopes=["transfers:read", "transfers:write", "accounts:read"],
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return LoginResponse(
            access_token=access_token,
            expires_in=expires_in,
            user_id=user.id,
            email=user.email,
        )
    except Exception as e:
        await db.rollback()
        raise map_auth_exception(e)


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    dependencies=[Depends(verify_jwt)],
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout user by blacklisting the current token.

    The token will be rejected for future requests until it expires.
    """
    auth_service = AuthService(db)
    settings = get_settings()

    try:
        await auth_service.revoke_access_token(
            token=credentials.credentials,
            secret_key=settings.SECRET_KEY,
            user_id=UUID(current_user.user_id),
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Still return success response for security/UX, even if revocation failed
        # (Logout is best-effort regarding the DB store)
        await db.rollback()

    return MessageResponse(message="Successfully logged out")


@router.post(
    "/auth/change-password",
    response_model=MessageResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for authenticated user.

    Requires current password for verification.
    """
    auth_service = AuthService(db)

    try:
        await auth_service.change_password(
            user_id=UUID(current_user.user_id),
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        await db.commit()

        return MessageResponse(message="Password changed successfully")
    except Exception as e:
        await db.rollback()
        raise map_auth_exception(e)


@router.post(
    "/auth/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit)],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset.

    If the email exists, a reset token will be generated.
    For security, the response is always successful to prevent email enumeration.

    In production, this would send an email with the reset link.
    """
    auth_service = AuthService(db)

    try:
        token = await auth_service.request_password_reset(email=payload.email)
        await db.commit()

        if token:
            # In production: send email with reset link
            # For development: log the token
            logger.info(f"Password reset token generated for {payload.email}: {token}")

        # Always return success to prevent email enumeration
        return MessageResponse(
            message="If an account exists with this email, a password reset link has been sent."
        )
    except Exception:
        await db.rollback()
        logger.exception("Error during password reset request")
        # Still return success to prevent enumeration
        return MessageResponse(
            message="If an account exists with this email, a password reset link has been sent."
        )


@router.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit)],
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using reset token.

    The token is valid for 24 hours after requesting password reset.
    """
    auth_service = AuthService(db)

    try:
        await auth_service.reset_password(
            token=payload.token,
            new_password=payload.new_password,
        )
        await db.commit()

        return MessageResponse(message="Password reset successfully")
    except Exception as e:
        await db.rollback()
        raise map_auth_exception(e)


@router.get(
    "/auth/me",
    response_model=UserProfileResponse,
    dependencies=[Depends(verify_jwt)],
)
async def get_current_user_profile(
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user's profile.
    """
    auth_service = AuthService(db)

    try:
        user = await auth_service.get_user_by_id(UUID(current_user.user_id))

        if not user:
            from app.api.v1.errors import UserNotFoundError

            raise UserNotFoundError()

        return UserProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )
    except Exception as e:
        raise map_auth_exception(e)
