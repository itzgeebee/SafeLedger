from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entry_type import EntryType
from app.domain.exceptions import DuplicateTransactionError, InvalidReversalError
from app.domain.ledger import Ledger
from app.infrastructure.repositories.accounts_repo import AccountsRepository
from app.infrastructure.repositories.idempotency_repo import IdempotencyRepository
from app.infrastructure.repositories.ledger_query_repo import LedgerQueryRepository
from app.infrastructure.repositories.ledger_repo import LedgerRepository
from app.schemas.transfer import TransferResponse
from app.services.balance_service import BalanceService
from app.services.idempotency_service import IdempotencyService


class ReversalService:
    IDEMPOTENCY_SCOPE = "reversal"

    def __init__(self, session: AsyncSession):
        self.session = session

        self.accounts_repo = AccountsRepository(session)
        self.ledger_repo = LedgerRepository(session)
        self.query_repo = LedgerQueryRepository(session)
        self.idempotency_repo = IdempotencyRepository(session)
        self.idempotency_service = IdempotencyService(self.idempotency_repo)
        self.balance_service = BalanceService(session)

    async def execute(
        self,
        *,
        original_transaction_id: UUID,
        idempotency_key: str,
    ) -> TransferResponse:
        payload = {"original_transaction_id": str(original_transaction_id)}

        # -----------------------------
        # Perform all operations within a single DB transaction
        # to ensure ACID properties for reversals.
        # -----------------------------

        async with self.session.begin():
            # Check idempotency inside transaction for safety
            existing = await self.idempotency_service.check_or_fail(
                key=idempotency_key,
                scope=self.IDEMPOTENCY_SCOPE,
                payload=payload,
            )

            if existing and existing.response_body:
                return TransferResponse.model_validate_json(existing.response_body)

            # Fetch original transaction
            original_tx = await self.query_repo.get_transaction(original_transaction_id)

            # Check if this transaction was already reversed
            # by looking for a reversal idempotency key with this transaction ID
            existing_reversal = await self.idempotency_repo.get_existing(
                key=f"reversal:{original_transaction_id}",
                scope="reversal_check",
            )
            if existing_reversal:
                raise InvalidReversalError(
                    f"Transaction {original_transaction_id} has already been reversed"
                )

            # Generate reversal transaction
            reversal_tx = Ledger.reversal(original_tx)

            # Collect all account IDs involved in the reversal
            account_ids = list({entry.account_id for entry in reversal_tx.entries})
            account_ids = sorted(account_ids, key=lambda x: str(x))

            # Lock accounts to prevent concurrent modifications
            await self.accounts_repo.get_accounts_for_update(account_ids)

            # Validate that the account being debited has sufficient funds
            for entry in reversal_tx.entries:
                if entry.entry_type == EntryType.DEBIT:
                    await self.balance_service.ensure_sufficient_funds(
                        account_id=entry.account_id,
                        currency=entry.currency,
                        required_amount=entry.amount,
                    )

            # Reserve idempotency key before persisting
            reservation = await self.idempotency_service.record(
                key=idempotency_key,
                scope=self.IDEMPOTENCY_SCOPE,
                payload=payload,
                response_body=None,
            )

            record, created = reservation
            if not created:
                if record.response_body:
                    return TransferResponse.model_validate_json(record.response_body)
                raise DuplicateTransactionError(
                    "Idempotency key already reserved by another in-flight transaction"
                )

            # Persist reversal ledger entries
            await self.ledger_repo.persist_transaction(reversal_tx)

            # Build response
            source_account_id = next(
                entry.account_id
                for entry in reversal_tx.entries
                if entry.entry_type == EntryType.DEBIT
            )
            destination_account_id = next(
                entry.account_id
                for entry in reversal_tx.entries
                if entry.entry_type == EntryType.CREDIT
            )
            amount = next(
                entry.amount
                for entry in reversal_tx.entries
                if entry.entry_type == EntryType.CREDIT
            )
            fee_amount = (
                sum(
                    entry.amount
                    for entry in reversal_tx.entries
                    if entry.entry_type == EntryType.DEBIT
                )
                - amount
            )

            response = TransferResponse(
                transaction_id=reversal_tx.transaction_id,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                amount=amount,
                fee_amount=fee_amount,
                currency=original_tx.entries[0].currency,
                status="REVERSED",
                created_at=datetime.now(UTC),
            )

            # Mark original transaction as reversed to prevent double-reversal
            await self.idempotency_repo.store_new(
                key=f"reversal:{original_transaction_id}",
                scope="reversal_check",
                payload={"reversal_tx_id": str(reversal_tx.transaction_id)},
                response_body=None,
            )

            # Update idempotency record with final response
            await self.idempotency_service.record(
                key=idempotency_key,
                scope=self.IDEMPOTENCY_SCOPE,
                payload=payload,
                response_body=response.model_dump_json(),
            )

        return response
