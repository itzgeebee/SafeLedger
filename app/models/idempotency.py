import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base

# Default expiration time for idempotency keys (48 hours)
IDEMPOTENCY_KEY_TTL_HOURS = 48


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    key = Column(String, nullable=False)
    scope = Column(String, nullable=False)

    request_hash = Column(String, nullable=False)
    response_body = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Expiration time for automatic cleanup
    expires_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
        + text(f"interval '{IDEMPOTENCY_KEY_TTL_HOURS} hours'"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "key",
            "scope",
            name="uq_idempotency_key_scope",
        ),
        Index("idx_idempotency_expires_at", "expires_at"),
    )
