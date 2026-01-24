"""
Domain and application-level exceptions.

These exceptions are raised inside services and repositories.
They are translated to HTTP errors at the API boundary.
"""


class SafeLedgerError(Exception):
    """
    Base exception for all SafeLedger errors.
    """

    code = "SAFELEDGER_ERROR"
    message = "An internal error occurred"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


# ----------------------------
# Account & Balance Errors
# ----------------------------


class AccountNotFoundError(SafeLedgerError):
    code = "ACCOUNT_NOT_FOUND"
    message = "Account does not exist"


class AccountAlreadyExistsError(SafeLedgerError):
    code = "ACCOUNT_ALREADY_EXISTS"
    message = "An account with this owner and currency already exists"


class AccountInactiveError(SafeLedgerError):
    code = "ACCOUNT_INACTIVE"
    message = "Account is inactive"


class CurrencyMismatchError(SafeLedgerError):
    code = "CURRENCY_MISMATCH"
    message = "Account currency mismatch"


class InsufficientFundsError(SafeLedgerError):
    code = "INSUFFICIENT_FUNDS"
    message = "Insufficient funds"


class InvalidAccountError(SafeLedgerError):
    code = "INVALID_ACCOUNT"
    message = "The account provided is invalid"


# ----------------------------
# Ledger & Transaction Errors
# ----------------------------


class InvalidTransferError(SafeLedgerError):
    code = "INVALID_TRANSFER"
    message = "Transfer parameters are invalid"


class LedgerInvariantViolation(SafeLedgerError):
    """
    Raised when a double-entry invariant is violated.
    This should NEVER happen in a correct system.
    """

    code = "LEDGER_INVARIANT_VIOLATION"
    message = "Ledger invariant violated"


class DuplicateTransactionError(SafeLedgerError):
    code = "DUPLICATE_TRANSACTION"
    message = "Transaction already processed"


class TransactionNotFoundError(SafeLedgerError):
    code = "TRANSACTION_NOT_FOUND"
    message = "Transaction does not exist"


class InvalidReversalError(SafeLedgerError):
    code = "INVALID_REVERSAL"
    message = "Transaction cannot be reversed"


# ----------------------------
# Idempotency Errors
# ----------------------------


class IdempotencyKeyConflictError(SafeLedgerError):
    code = "IDEMPOTENCY_KEY_CONFLICT"
    message = "Idempotency key reuse with different payload"


# ----------------------------
# Authorization & Abuse Errors
# ----------------------------


class UnauthorizedActionError(SafeLedgerError):
    code = "UNAUTHORIZED_ACTION"
    message = "You are not allowed to perform this action"


class RateLimitExceededError(SafeLedgerError):
    code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests"


# ----------------------------
# Infrastructure Errors
# ----------------------------


class DatabaseError(SafeLedgerError):
    code = "DATABASE_ERROR"
    message = "Database operation failed"
