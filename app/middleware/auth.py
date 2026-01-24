"""
JWT Authentication middleware and dependencies.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.db import get_db
from app.models.user import TokenBlacklist

logger = logging.getLogger(__name__)

security = HTTPBearer()


class TokenData(BaseModel):
    """Decoded JWT token data."""

    sub: str  # User ID
    jti: str  # JWT ID for revocation
    exp: datetime
    iat: datetime
    scopes: list[str] = []


class CurrentUser(BaseModel):
    """Authenticated user context."""

    user_id: str
    scopes: list[str] = []

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin" in self.scopes


def create_access_token(
    user_id: str,
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
        "scopes": scopes or [],
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def verify_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Verify JWT token and return current user.
    Raises HTTPException 401 if invalid.
    """
    settings = get_settings()
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")

        if user_id is None or jti is None:
            logger.warning("JWT token missing 'sub' or 'jti' claim")
            raise credentials_exception

        # Check blacklist
        stmt = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            logger.info(f"Revoked token used: {jti}")
            raise credentials_exception

        scopes = payload.get("scopes", [])

        return CurrentUser(user_id=user_id, scopes=scopes)

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception


def require_scope(required_scope: str):
    """
    Dependency factory for requiring a specific scope.

    Usage:
        @router.post("/admin/...", dependencies=[Depends(require_scope("admin"))])
    """

    async def scope_checker(
        current_user: Annotated[CurrentUser, Depends(verify_jwt)],
    ) -> CurrentUser:
        if not current_user.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )
        return current_user

    return scope_checker


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> CurrentUser:
    """Alias for verify_jwt for clearer intent in route dependencies."""
    return await verify_jwt(credentials)
