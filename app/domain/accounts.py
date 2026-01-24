from dataclasses import dataclass
from uuid import UUID

from app.domain.exceptions import (
    AccountInactiveError,
    CurrencyMismatchError,
)


@dataclass(frozen=True)
class LedgerAccount:
    id: UUID
    currency: str
    is_active: bool

    def ensure_active(self) -> None:
        if not self.is_active:
            raise AccountInactiveError(f"Account {self.id} is inactive")

    def ensure_currency(self, currency: str) -> None:
        if self.currency != currency:
            raise CurrencyMismatchError(
                f"Account {self.id} currency mismatch: {self.currency} != {currency}"
            )
