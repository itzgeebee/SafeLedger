"""
User model for authentication.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class User(Base):
    """
    User account for authentication.
    Passwords are hashed with bcrypt.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Authentication
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    # Profile
    full_name = Column(String, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_reset_token", "password_reset_token"),
    )


class TokenBlacklist(Base):
    """
    Blacklisted JWT tokens (for logout).
    Tokens are stored until their expiration time.
    """

    __tablename__ = "token_blacklist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    jti = Column(String, unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(String, nullable=False)  # ACCESS, REFRESH
    user_id = Column(UUID(as_uuid=True), nullable=False)

    blacklisted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(
        DateTime(timezone=True), nullable=False
    )  # When token would have expired

    __table_args__ = (
        Index("idx_blacklist_jti", "jti"),
        Index("idx_blacklist_expires", "expires_at"),
    )
