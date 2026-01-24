import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaction_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Amount is always POSITIVE
    amount = Column(Numeric(18, 2), nullable=False)

    # DEBIT or CREDIT
    entry_type = Column(String, nullable=False)

    currency = Column(String(3), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_amount_positive"),
        CheckConstraint(
            "entry_type IN ('DEBIT', 'CREDIT')",
            name="chk_entry_type",
        ),
        CheckConstraint("length(currency) = 3", name="chk_currency_length"),
        Index(
            "idx_transaction_account",
            "transaction_id",
            "account_id",
        ),
    )
