"""
Accounts API endpoints.

Follows Separation of Concerns:
- Router: HTTP concerns only (request/response, status codes)
- Service: Business logic
- Repository: Data access
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import map_account_exception
from app.db.db import get_db
from app.middleware.auth import CurrentUser, verify_jwt
from app.middleware.rate_limit import rate_limit
from app.schemas.account import (
    AccountListResponse,
    AccountResponse,
    BalanceResponse,
    CreateAccountRequest,
    account_to_response,
)
from app.services.accounts_service import AccountsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Accounts"])


# Endpoints


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def get_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Get account details by ID."""
    service = AccountsService(db)

    try:
        account = await service.get_account(account_id)
        return account_to_response(account)
    except Exception as e:
        raise map_account_exception(e)


@router.get(
    "/accounts/{account_id}/balance",
    response_model=BalanceResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def get_account_balance(
    account_id: UUID,
    currency: str = "NGN",
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Get account balance for a specific currency."""
    service = AccountsService(db)

    try:
        balance = await service.get_account_balance(account_id, currency)
        return BalanceResponse(
            account_id=account_id,
            currency=currency,
            balance=balance,
        )
    except Exception as e:
        raise map_account_exception(e)


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def create_account(
    payload: CreateAccountRequest,
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Create a new account."""
    service = AccountsService(db)

    try:
        account = await service.create_account(
            owner_id=payload.owner_id,
            currency=payload.currency,
            account_type=payload.account_type,
        )
        await db.commit()
        return account_to_response(account)
    except Exception as e:
        await db.rollback()
        raise map_account_exception(e)


@router.post(
    "/accounts/{account_id}/deactivate",
    response_model=AccountResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def deactivate_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an account. Deactivated accounts cannot be used in transfers."""
    service = AccountsService(db)

    try:
        account = await service.deactivate_account(account_id)
        await db.commit()
        return account_to_response(account)
    except Exception as e:
        await db.rollback()
        raise map_account_exception(e)


@router.post(
    "/accounts/{account_id}/activate",
    response_model=AccountResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def activate_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Activate a deactivated account."""
    service = AccountsService(db)

    try:
        account = await service.activate_account(account_id)
        await db.commit()
        return account_to_response(account)
    except Exception as e:
        await db.rollback()
        raise map_account_exception(e)


@router.get(
    "/users/{owner_id}/accounts",
    response_model=AccountListResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def get_user_accounts(
    owner_id: str,
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Get all accounts for a specific owner."""
    service = AccountsService(db)

    try:
        accounts = await service.get_accounts_by_owner(owner_id)
        return AccountListResponse(
            accounts=[account_to_response(acc) for acc in accounts]
        )
    except Exception as e:
        raise map_account_exception(e)
