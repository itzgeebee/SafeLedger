from sqlalchemy.orm import DeclarativeBase

# IMPORTANT: import all models so Alembic can see them
from app.models.account import Account
from app.models.balance import Balance
from app.models.idempotency import IdempotencyKey
from app.models.ledger_entry import LedgerEntry
from app.models.user import TokenBlacklist, User
from app.services.audit_service import AuditLog


class Base(DeclarativeBase):
    pass


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
