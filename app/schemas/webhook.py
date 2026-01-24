from uuid import UUID

from pydantic import BaseModel, Field


class PayInSimulationRequest(BaseModel):
    user_account_id: UUID
    amount: float = Field(..., gt=0)
    currency: str = Field("NGN", min_length=3, max_length=3)
    external_reference: str = Field(..., min_length=1)
