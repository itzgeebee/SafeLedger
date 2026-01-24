from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Transfer(BaseModel):
    source_account_id: UUID

    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)

    fee_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)

    reference: Optional[str] = Field(
        None, max_length=128, description="Client-provided reference"
    )

    @field_validator("amount", "fee_amount", mode="before")
    @classmethod
    def validate_decimals(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            v = Decimal(v)
        if isinstance(v, Decimal) and v.as_tuple().exponent < -2:
            raise ValueError("Amounts must have at most 2 decimal places")
        return v


class TransferRequest(Transfer):
    destination_account_id: UUID

    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)

    fee_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)


class TransferResponse(BaseModel):
    transaction_id: UUID

    source_account_id: UUID
    destination_account_id: UUID

    # Use Decimal to avoid float precision issues with money
    amount: Decimal
    fee_amount: Decimal
    currency: str

    status: str = Field(..., description="SUCCESS | REVERSED | FAILED")

    created_at: datetime

    model_config = {"json_encoders": {Decimal: str}}
