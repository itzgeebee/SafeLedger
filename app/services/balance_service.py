from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import InsufficientFundsError
from app.infrastructure.repositories.balance_repo import BalanceRepository
from app.models.ledger_entry import LedgerEntry


class BalanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.balance_repo = BalanceRepository(session)

    async def get_balance(
        self,
        account_id: UUID,
        currency: str,
    ) -> Decimal:
        """
        Get balance for an account. Uses cached balance table for O(1) lookup.
        Falls back to ledger scan if cache miss (for pre-migration data).
        """
        # Try cache first
        cached = await self.balance_repo.get_balance(account_id, currency)
        if cached is not None:
            return cached

        # Fallback: calculate from ledger entries
        return await self._calculate_from_ledger(account_id, currency)

    async def _calculate_from_ledger(
        self,
        account_id: UUID,
        currency: str,
    ) -> Decimal:
        """
        Calculate balance by scanning ledger entries.
        Used as fallback for accounts without cached balance.
        """
        stmt = select(
            func.coalesce(
                func.sum(LedgerEntry.amount).filter(LedgerEntry.entry_type == "CREDIT"),
                0,
            )
            - func.coalesce(
                func.sum(LedgerEntry.amount).filter(LedgerEntry.entry_type == "DEBIT"),
                0,
            )
        ).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.currency == currency,
        )

        result = await self.session.execute(stmt)
        balance: Decimal = result.scalar_one()

        return balance

    async def ensure_sufficient_funds(
        self,
        account_id: UUID,
        currency: str,
        required_amount: Decimal,
    ) -> None:
        balance = await self.get_balance(account_id, currency)

        if balance < required_amount:
            raise InsufficientFundsError(
                f"Insufficient funds: balance={balance}, required={required_amount}"
            )
