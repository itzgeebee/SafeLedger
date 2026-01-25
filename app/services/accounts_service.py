"""
Accounts service - business logic for account operations.
Follows Separation of Concerns: Router → Service → Repository
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAccountError,
)
from app.infrastructure.repositories.accounts_repo import AccountsRepository
from app.models.account import Account, AccountType
from app.services.balance_service import BalanceService

logger = logging.getLogger(__name__)


class AccountsService:
    """
    Service layer for account operations.

    Handles business logic and orchestrates repository calls.
    Should NOT contain HTTP-specific logic.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts_repo = AccountsRepository(session)
        self.balance_service = BalanceService(session)

    async def get_account(self, account_id: UUID) -> Account:
        """
        Get account by ID.

        Returns the full Account model with all fields.
        Raises AccountNotFoundError if not found.
        """
        from sqlalchemy import select

        stmt = select(Account).where(Account.id == account_id)
        result = await self.session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise AccountNotFoundError(f"Account {account_id} not found")

        return account

    async def get_account_balance(
        self,
        account_id: UUID,
        currency: str,
    ) -> Decimal:
        """
        Get account balance for a specific currency.

        First verifies account exists, then retrieves balance.
        """
        # Verify account exists
        await self.accounts_repo.get_ledger_account(account_id)

        # Get balance
        balance = await self.balance_service.get_balance(account_id, currency)
        return balance

    async def create_account(
        self,
        *,
        owner_id: str | None,
        currency: str,
        account_type: str,
    ) -> Account:
        """
        Create a new account.

        Validates:
        - Account type is valid (USER, SYSTEM, SETTLEMENT)
        - USER accounts require owner_id
        - SYSTEM/SETTLEMENT accounts must not have owner_id
        """
        # Validate account type
        try:
            acc_type = AccountType(account_type)
        except ValueError:
            raise InvalidAccountError(
                f"Invalid account_type '{account_type}'. Must be one of: USER, SYSTEM, SETTLEMENT"
            )

        # Validate owner_id requirements
        if acc_type == AccountType.USER and not owner_id:
            raise InvalidAccountError("owner_id is required for USER accounts")

        if acc_type != AccountType.USER and owner_id:
            raise InvalidAccountError(
                "owner_id must be null for SYSTEM and SETTLEMENT accounts"
            )

        # Create account
        account = Account(
            owner_id=owner_id,
            currency=currency.upper(),
            account_type=acc_type,
        )

        from sqlalchemy.exc import IntegrityError

        try:
            self.session.add(account)
            await self.session.flush()
        except IntegrityError:
            raise AccountAlreadyExistsError(
                f"Account for owner {owner_id} with currency {currency} already exists"
            )

        logger.info(
            f"Account created: {account.id} (type={account_type}, currency={currency})"
        )
        return account

    async def deactivate_account(self, account_id: UUID) -> Account:
        """
        Deactivate an account.

        Deactivated accounts cannot be used in transfers.
        """
        account = await self.get_account(account_id)

        if not account.is_active:
            raise InvalidAccountError(f"Account {account_id} is already inactive")

        account.is_active = False
        await self.session.flush()

        logger.info(f"Account deactivated: {account_id}")
        return account

    async def activate_account(self, account_id: UUID) -> Account:
        """
        Activate a deactivated account.
        """
        account = await self.get_account(account_id)

        if account.is_active:
            raise InvalidAccountError(f"Account {account_id} is already active")

        account.is_active = True
        await self.session.flush()

        logger.info(f"Account activated: {account_id}")
        return account

    async def get_accounts_by_owner(self, owner_id: str) -> list[Account]:
        """
        Get all accounts for a specific owner.
        """
        from sqlalchemy import select

        stmt = select(Account).where(Account.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
