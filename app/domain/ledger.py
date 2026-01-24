import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List
from uuid import UUID

from app.config import get_settings
from app.domain.accounts import LedgerAccount
from app.domain.entry_type import EntryType
from app.domain.exceptions import InvalidTransferError, LedgerInvariantViolation


@dataclass(frozen=True)
class LedgerEntrySpec:
    account_id: UUID
    amount: Decimal
    entry_type: EntryType
    currency: str


@dataclass(frozen=True)
class LedgerTransaction:
    transaction_id: UUID
    entries: List[LedgerEntrySpec]


class Ledger:
    @staticmethod
    def transfer(
        *,
        source: LedgerAccount,
        destination: LedgerAccount,
        fee_account: LedgerAccount | None,
        amount: Decimal,
        fee_amount: Decimal,
        currency: str,
    ) -> LedgerTransaction:
        """
        Create a ledger transaction for a transfer with optional fees.
        """
        settings = get_settings()

        if amount <= 0:
            raise InvalidTransferError("Transfer amount must be positive")

        if amount < Decimal(str(settings.MIN_TRANSACTION_AMOUNT)):
            raise InvalidTransferError(
                f"Transfer amount must be at least {settings.MIN_TRANSACTION_AMOUNT}"
            )

        if fee_amount < 0:
            raise InvalidTransferError("Fee amount cannot be negative")

        source.ensure_active()
        destination.ensure_active()

        source.ensure_currency(currency)
        destination.ensure_currency(currency)

        if fee_account:
            fee_account.ensure_currency(currency)

        tx_id = uuid.uuid4()
        entries: list[LedgerEntrySpec] = []

        # --- Principal transfer ---
        entries.append(
            LedgerEntrySpec(
                account_id=source.id,
                amount=amount + fee_amount,
                entry_type=EntryType.DEBIT,
                currency=currency,
            )
        )

        entries.append(
            LedgerEntrySpec(
                account_id=destination.id,
                amount=amount,
                entry_type=EntryType.CREDIT,
                currency=currency,
            )
        )

        # --- Fee settlement ---
        if fee_amount > 0:
            if not fee_account:
                raise InvalidTransferError("Fee account required when fee_amount > 0")

            entries.append(
                LedgerEntrySpec(
                    account_id=fee_account.id,
                    amount=fee_amount,
                    entry_type=EntryType.CREDIT,
                    currency=currency,
                )
            )

        # --- Zero-sum validation ---
        Ledger._validate_zero_sum(entries)

        return LedgerTransaction(
            transaction_id=tx_id,
            entries=entries,
        )

    @staticmethod
    def reversal(
        original_tx: LedgerTransaction,
    ) -> LedgerTransaction:
        """
        Generate a reversing transaction by inverting all entries.
        """
        tx_id = uuid.uuid4()
        reversed_entries: list[LedgerEntrySpec] = []

        for entry in original_tx.entries:
            reversed_entries.append(
                LedgerEntrySpec(
                    account_id=entry.account_id,
                    amount=entry.amount,
                    entry_type=entry.entry_type.opposite(),
                    currency=entry.currency,
                )
            )

        Ledger._validate_zero_sum(reversed_entries)

        return LedgerTransaction(
            transaction_id=tx_id,
            entries=reversed_entries,
        )

    @staticmethod
    def _validate_zero_sum(entries: list[LedgerEntrySpec]) -> None:
        debit_total = sum(e.amount for e in entries if e.entry_type == EntryType.DEBIT)
        credit_total = sum(
            e.amount for e in entries if e.entry_type == EntryType.CREDIT
        )

        if debit_total != credit_total:
            raise LedgerInvariantViolation(
                f"Zero-sum violation: debits={debit_total}, credits={credit_total}"
            )
