import logging

from fastapi import HTTPException, status

from app.domain.exceptions import (
    AccountNotFoundError,
    DuplicateTransactionError,
    IdempotencyKeyConflictError,
    InsufficientFundsError,
    InvalidAccountError,
    SafeLedgerError,
    TransactionNotFoundError,
)
from app.services.auth_service import (
    AccountDisabledError,
    AuthError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    PasswordValidationError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


def map_auth_exception(exc: Exception) -> HTTPException:
    """Map auth exceptions to HTTP responses."""
    if isinstance(exc, InvalidCredentialsError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        )
    if isinstance(exc, EmailAlreadyExistsError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        )
    if isinstance(exc, InvalidResetTokenError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    if isinstance(exc, AccountDisabledError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        )
    if isinstance(exc, PasswordValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    if isinstance(exc, UserNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )
    if isinstance(exc, AuthError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    logger.exception("Unexpected auth error")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )


def map_account_exception(exc: Exception) -> HTTPException:
    """Map account exceptions to appropriate HTTP responses."""
    if isinstance(exc, AccountNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, InvalidAccountError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        )
    if isinstance(exc, SafeLedgerError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        )
    logger.exception("Unexpected error in accounts operation")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )


def map_transfer_exception(exc: Exception) -> HTTPException:
    """Map transfer exceptions to appropriate HTTP responses."""
    if isinstance(exc, (AccountNotFoundError, TransactionNotFoundError)):
        return HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, (DuplicateTransactionError, IdempotencyKeyConflictError)):
        return HTTPException(status_code=409, detail=exc.message)
    if isinstance(exc, InsufficientFundsError):
        return HTTPException(status_code=400, detail=exc.message)
    if isinstance(exc, SafeLedgerError):
        return HTTPException(status_code=400, detail=exc.message)
    logger.exception("Unexpected error during transfer operation")
    return HTTPException(status_code=500, detail="Internal server error")
