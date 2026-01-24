from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AccountResponse(BaseModel):
    id: UUID
    owner_id: str | None
    currency: str
    account_type: str
    is_active: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    account_id: UUID
    currency: str
    balance: Decimal

    model_config = {"json_encoders": {Decimal: str}}


class CreateAccountRequest(BaseModel):
    owner_id: str | None = Field(None, description="Required for USER accounts")
    currency: str = Field(..., min_length=3, max_length=3)
    account_type: str = Field(..., description="USER | SYSTEM | SETTLEMENT")


class AccountListResponse(BaseModel):
    accounts: list[AccountResponse]


def account_to_response(account) -> AccountResponse:
    """Convert Account model to response schema."""
    return AccountResponse(
        id=account.id,
        owner_id=account.owner_id,
        currency=account.currency,
        account_type=(
            account.account_type.value
            if hasattr(account.account_type, "value")
            else account.account_type
        ),
        is_active=account.is_active,
        created_at=account.created_at if hasattr(account, "created_at") else None,
    )
