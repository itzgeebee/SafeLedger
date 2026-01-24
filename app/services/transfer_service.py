from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.exceptions import DuplicateTransactionError, InvalidTransferError
from app.domain.ledger import Ledger
from app.infrastructure.repositories.accounts_repo import AccountsRepository
from app.infrastructure.repositories.idempotency_repo import IdempotencyRepository
from app.infrastructure.repositories.ledger_repo import LedgerRepository
from app.observability import record_metric
from app.schemas.transfer import Transfer, TransferRequest, TransferResponse
from app.services.balance_service import BalanceService
from app.services.idempotency_service import IdempotencyService


class TransferService:
    IDEMPOTENCY_SCOPE = "transfer"

    def __init__(self, session: AsyncSession):
        self.session = session

        self.accounts_repo = AccountsRepository(session)
        self.ledger_repo = LedgerRepository(session)
        self.idempotency_repo = IdempotencyRepository(session)

        self.balance_service = BalanceService(session)
        self.idempotency_service = IdempotencyService(self.idempotency_repo)

    async def execute(
        self,
        *,
        payload: TransferRequest | Transfer,
        idempotency_key: str,
        is_external: bool = False,
    ) -> TransferResponse:

        payload_dict = payload.model_dump(
            exclude_unset=True,
        )

        # -----------------------------
        # Idempotency check - use string representation for amounts
        # to preserve Decimal precision in hash calculation
        # -----------------------------

        payload_dict["amount"] = str(payload_dict["amount"])
        payload_dict["fee_amount"] = str(payload_dict["fee_amount"])
        payload_dict["source_account_id"] = str(payload_dict["source_account_id"])
        payload_dict["destination_account_id"] = (
            "" if is_external else str(payload_dict["destination_account_id"])
        )

        # -----------------------------
        # Perform idempotency check, balance validation and persist
        # within a single DB transaction to ensure ACID properties. We
        # also lock the involved account rows with SELECT FOR UPDATE to
        # serialize concurrent transfers against the same accounts.
        # -----------------------------

        total_debit = payload.amount + payload.fee_amount

        # Validate transaction amount limits
        settings = get_settings()
        if total_debit > Decimal(settings.MAX_TRANSACTION_AMOUNT):
            raise InvalidTransferError(
                f"Transaction amount {total_debit} exceeds maximum allowed {settings.MAX_TRANSACTION_AMOUNT}"
            )

        async with self.session.begin():
            # Re-check idempotency inside transaction for stronger safety
            existing = await self.idempotency_service.check_or_fail(
                key=idempotency_key,
                scope=self.IDEMPOTENCY_SCOPE,
                payload=payload_dict,
            )

            if existing and existing.response_body:
                return TransferResponse.model_validate_json(existing.response_body)

            # Resolve destination / fee accounts (may query by type)
            source_id = payload.source_account_id

            if is_external:
                destination_acc = await self.accounts_repo.get_settlement_account(
                    currency=payload.currency
                )
                destination_id = destination_acc.id
            else:
                destination_id = payload.destination_account_id

            fee_account_id = None
            if payload.fee_amount > 0:
                fee_acc = await self.accounts_repo.get_system_account(
                    currency=payload.currency
                )
                fee_account_id = fee_acc.id

            # Lock involved accounts deterministically (sorted by id) to avoid deadlocks
            ids_to_lock = [source_id]
            if destination_id:
                ids_to_lock.append(destination_id)
            if fee_account_id:
                ids_to_lock.append(fee_account_id)

            # sort and deduplicate (sort by string representation to make order deterministic)
            ids_to_lock = sorted(set(ids_to_lock), key=lambda x: str(x))

            locked = await self.accounts_repo.get_accounts_for_update(ids_to_lock)

            # Build LedgerAccount domain objects from locked rows
            source = locked[source_id]
            destination = locked.get(destination_id) if destination_id else None
            fee_account = locked.get(fee_account_id) if fee_account_id else None

            # Balance check (reads are isolated by the FOR UPDATE lock)
            await self.balance_service.ensure_sufficient_funds(
                account_id=source.id,
                currency=payload.currency,
                required_amount=total_debit,
            )
            # Reserve idempotency key before persisting ledger entries to
            # prevent duplicate writes from concurrent transactions.

            reservation = await self.idempotency_service.record(
                key=idempotency_key,
                scope=self.IDEMPOTENCY_SCOPE,
                payload=payload_dict,
                response_body=None,
            )

            record_metric("transfer.idempotency.reserved", 1)

            # `store_new` returns (record, created_flag) when reserving
            record, created = reservation
            if not created:
                # existing reservation: if response present, replay; otherwise another
                # transaction is currently processing this key — treat as duplicate in-flight
                if record.response_body:
                    return TransferResponse.model_validate_json(record.response_body)
                record_metric("transfer.idempotency.duplicate_inflight", 1)
                raise DuplicateTransactionError(
                    "Idempotency key already reserved by another in-flight transaction"
                )

            # Domain ledger transaction
            ledger_tx = Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=fee_account,
                amount=payload.amount,
                fee_amount=payload.fee_amount,
                currency=payload.currency,
            )

            # Persist ledger entries (still within same transaction)
            await self.ledger_repo.persist_transaction(ledger_tx)

            # Build response (still inside transaction so we can save it atomically)
            response = TransferResponse(
                transaction_id=ledger_tx.transaction_id,
                source_account_id=payload.source_account_id,
                destination_account_id=destination.id,
                amount=payload.amount,
                fee_amount=payload.fee_amount,
                currency=payload.currency,
                status="SUCCESS",
                created_at=datetime.now(UTC),
            )

            # Update idempotency record with final response body before commit
            await self.idempotency_service.record(
                key=idempotency_key,
                scope=self.IDEMPOTENCY_SCOPE,
                payload=payload_dict,
                response_body=response.model_dump_json(),
            )
            record_metric("transfer.success", 1, {"currency": payload.currency})

        return response
