"""
Audit logging service for financial compliance.
Records all state-changing operations with full context.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """
    Immutable audit log for all state-changing operations.
    This table should have DELETE and UPDATE disabled at DB level.
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # When
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Who
    actor_id = Column(String, nullable=True)  # User ID, null for system actions
    actor_type = Column(String, nullable=False)  # USER, SYSTEM, ADMIN

    # What
    action = Column(
        String, nullable=False
    )  # CREATE, UPDATE, DELETE, TRANSFER, REVERSAL
    resource_type = Column(String, nullable=False)  # ACCOUNT, TRANSACTION, LEDGER_ENTRY
    resource_id = Column(String, nullable=True)  # ID of affected resource

    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_id = Column(String, nullable=True)  # Correlation ID

    # State change
    old_state = Column(JSONB, nullable=True)
    new_state = Column(JSONB, nullable=True)
    extra_data = Column(
        JSONB, nullable=True
    )  # Additional context (renamed from metadata)

    # Integrity
    previous_hash = Column(String, nullable=True)  # Hash of previous log entry
    entry_hash = Column(String, nullable=True)  # Hash of this entry for integrity

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_actor", "actor_id"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_action", "action"),
    )


class AuditService:
    """Service for recording audit events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: str | None = None,
        actor_type: str = "USER",
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        old_state: dict | None = None,
        new_state: dict | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        """
        Record an audit event.
        Called within the same transaction as the operation being logged.
        """
        import hashlib
        import json

        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            actor_type=actor_type,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            old_state=old_state,
            new_state=new_state,
            extra_data=extra_data,
        )

        # Compute entry hash for integrity verification
        hash_content = json.dumps(
            {
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "actor_id": actor_id,
                "new_state": new_state,
            },
            sort_keys=True,
            default=str,
        )

        entry.entry_hash = hashlib.sha256(hash_content.encode()).hexdigest()

        self.session.add(entry)
        await self.session.flush()

        logger.info(
            f"AUDIT: {action} {resource_type}:{resource_id} by {actor_type}:{actor_id}"
        )

        return entry

    async def log_transfer(
        self,
        *,
        transaction_id: str,
        source_account_id: str,
        destination_account_id: str,
        amount: str,
        currency: str,
        actor_id: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Convenience method for logging transfers."""
        return await self.log(
            action="TRANSFER",
            resource_type="TRANSACTION",
            resource_id=transaction_id,
            actor_id=actor_id,
            actor_type="USER" if actor_id else "SYSTEM",
            ip_address=ip_address,
            request_id=request_id,
            new_state={
                "source_account_id": source_account_id,
                "destination_account_id": destination_account_id,
                "amount": amount,
                "currency": currency,
            },
        )

    async def log_reversal(
        self,
        *,
        reversal_transaction_id: str,
        original_transaction_id: str,
        actor_id: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Convenience method for logging reversals."""
        return await self.log(
            action="REVERSAL",
            resource_type="TRANSACTION",
            resource_id=reversal_transaction_id,
            actor_id=actor_id,
            actor_type="USER" if actor_id else "SYSTEM",
            ip_address=ip_address,
            request_id=request_id,
            extra_data={"original_transaction_id": original_transaction_id},
        )
