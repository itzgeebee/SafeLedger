import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class Balance(Base):
    """
    Materialized balance cache for O(1) balance lookups.
    Updated transactionally alongside ledger entries.
    """

    __tablename__ = "balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    currency = Column(String(3), nullable=False)

    # Current balance (sum of credits - debits)
    balance = Column(Numeric(18, 2), nullable=False, default=0)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # One balance record per account per currency
        UniqueConstraint("account_id", "currency", name="uq_balance_account_currency"),
        Index("idx_balance_account_currency", "account_id", "currency"),
    )
