from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.accounts import LedgerAccount
from app.domain.exceptions import AccountNotFoundError
from app.infrastructure.advisory_lock import pg_advisory_lock
from app.models.account import Account


class AccountsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ledger_account(self, account_id: UUID) -> LedgerAccount:
        stmt = select(Account).where(Account.id == account_id)
        result = await self.session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise AccountNotFoundError(f"Account {account_id} not found")

        return LedgerAccount(
            id=account.id,
            currency=account.currency,
            is_active=account.is_active,
            account_type=account.account_type,
        )

    async def get_system_account(self, currency: str) -> LedgerAccount:
        stmt = select(Account).where(
            Account.account_type == "SYSTEM",
            Account.currency == currency,
        )
        result = await self.session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise AccountNotFoundError(
                f"System account with currency {currency} not found"
            )

        return LedgerAccount(
            id=account.id,
            currency=account.currency,
            is_active=account.is_active,
            account_type=account.account_type,
        )

    async def get_settlement_account(self, currency: str) -> LedgerAccount:
        stmt = select(Account).where(
            Account.currency == currency,
            Account.account_type == "SETTLEMENT",
        )
        result = await self.session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise AccountNotFoundError(
                f"Settlement account with currency {currency} not found"
            )

        return LedgerAccount(
            id=account.id,
            currency=account.currency,
            is_active=account.is_active,
            account_type=account.account_type,
        )

    async def get_accounts_for_update(self, account_ids: list[UUID]) -> dict:
        """Fetch multiple accounts and lock their rows FOR UPDATE.

        Returns a dict mapping account_id -> LedgerAccount.
        Caller should pass a deterministic list to avoid deadlocks.
        """
        if not account_ids:
            return {}

        # Issue advisory locks first (Postgres) to provide application-level
        # deterministic locking across multiple process boundaries. This is
        # complementary to SELECT ... FOR UPDATE which locks rows.
        await pg_advisory_lock(self.session, [str(a) for a in account_ids])

        stmt = select(Account).where(Account.id.in_(account_ids)).with_for_update()
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        mapped = {
            r.id: LedgerAccount(
                id=r.id,
                currency=r.currency,
                is_active=r.is_active,
                account_type=r.account_type,
            )
            for r in rows
        }

        # Ensure all requested accounts were found
        for aid in account_ids:
            if aid not in mapped:
                raise AccountNotFoundError(f"Account {aid} not found")

        return mapped
