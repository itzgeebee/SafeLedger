from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# IMPORTANT: import all models so Alembic can see them
from app.models.account import Account  # noqa: E402
from app.models.balance import Balance  # noqa: E402
from app.models.idempotency import IdempotencyKey  # noqa: E402
from app.models.ledger_entry import LedgerEntry  # noqa: E402
from app.models.user import TokenBlacklist, User  # noqa: E402
from app.services.audit_service import AuditLog  # noqa: E402

__all__ = [
    "Base",
    "Account",
    "LedgerEntry",
    "IdempotencyKey",
    "Balance",
    "User",
    "TokenBlacklist",
    "AuditLog",
]
