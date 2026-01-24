import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class AccountType(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    SETTLEMENT = "SETTLEMENT"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Nullable: SYSTEM / SETTLEMENT accounts have no human owner
    owner_id = Column(String, nullable=True, index=True)

    currency = Column(String(3), nullable=False)

    account_type = Column(
        SQLEnum(AccountType, name="account_type"),
        nullable=False,
    )

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Currency format
        CheckConstraint(
            "length(currency) = 3",
            name="chk_currency_length",
        ),
        # Enforce owner semantics
        CheckConstraint(
            """
            (account_type = 'USER' AND owner_id IS NOT NULL)
            OR
            (account_type IN ('SYSTEM', 'SETTLEMENT') AND owner_id IS NULL)
            """,
            name="chk_account_owner_by_type",
        ),
        # One account per user per currency
        UniqueConstraint(
            "owner_id",
            "currency",
            name="uq_user_currency_account",
        ),
    )
