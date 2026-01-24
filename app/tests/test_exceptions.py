"""
Unit tests for domain exceptions.
"""

from app.domain.exceptions import (
    AccountInactiveError,
    AccountNotFoundError,
    CurrencyMismatchError,
    DatabaseError,
    DuplicateTransactionError,
    IdempotencyKeyConflictError,
    InsufficientFundsError,
    InvalidAccountError,
    InvalidReversalError,
    InvalidTransferError,
    LedgerInvariantViolation,
    RateLimitExceededError,
    SafeLedgerError,
    TransactionNotFoundError,
    UnauthorizedActionError,
)


class TestSafeLedgerError:
    def test_default_message(self):
        """Should have default message."""
        error = SafeLedgerError()
        assert error.message == "An internal error occurred"
        assert error.code == "SAFELEDGER_ERROR"

    def test_custom_message(self):
        """Should accept custom message."""
        error = SafeLedgerError("Custom error message")
        assert error.message == "Custom error message"

    def test_str_representation(self):
        """String representation should be the message."""
        error = SafeLedgerError("Test message")
        assert str(error) == "Test message"


class TestAccountErrors:
    def test_account_not_found_error(self):
        error = AccountNotFoundError()
        assert error.code == "ACCOUNT_NOT_FOUND"
        assert "Account" in error.message or "exist" in error.message

    def test_account_inactive_error(self):
        error = AccountInactiveError()
        assert error.code == "ACCOUNT_INACTIVE"

    def test_currency_mismatch_error(self):
        error = CurrencyMismatchError("NGN != USD")
        assert error.code == "CURRENCY_MISMATCH"
        assert "NGN != USD" in error.message

    def test_insufficient_funds_error(self):
        error = InsufficientFundsError("Balance too low")
        assert error.code == "INSUFFICIENT_FUNDS"

    def test_invalid_account_error(self):
        error = InvalidAccountError()
        assert error.code == "INVALID_ACCOUNT"


class TestTransactionErrors:
    def test_invalid_transfer_error(self):
        error = InvalidTransferError()
        assert error.code == "INVALID_TRANSFER"

    def test_ledger_invariant_violation(self):
        error = LedgerInvariantViolation("Debits != Credits")
        assert error.code == "LEDGER_INVARIANT_VIOLATION"
        assert "Debits != Credits" in error.message

    def test_duplicate_transaction_error(self):
        error = DuplicateTransactionError()
        assert error.code == "DUPLICATE_TRANSACTION"

    def test_transaction_not_found_error(self):
        error = TransactionNotFoundError()
        assert error.code == "TRANSACTION_NOT_FOUND"

    def test_invalid_reversal_error(self):
        error = InvalidReversalError("Already reversed")
        assert error.code == "INVALID_REVERSAL"


class TestIdempotencyErrors:
    def test_idempotency_key_conflict_error(self):
        error = IdempotencyKeyConflictError()
        assert error.code == "IDEMPOTENCY_KEY_CONFLICT"


class TestAuthErrors:
    def test_unauthorized_action_error(self):
        error = UnauthorizedActionError()
        assert error.code == "UNAUTHORIZED_ACTION"

    def test_rate_limit_exceeded_error(self):
        error = RateLimitExceededError()
        assert error.code == "RATE_LIMIT_EXCEEDED"


class TestInfrastructureErrors:
    def test_database_error(self):
        error = DatabaseError("Connection failed")
        assert error.code == "DATABASE_ERROR"
        assert "Connection failed" in error.message
