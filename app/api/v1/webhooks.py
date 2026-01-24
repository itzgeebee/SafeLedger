"""
Simulation webhooks for testing.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import map_transfer_exception
from app.db.db import get_db
from app.services.transfer_service import TransferService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])


class PayInSimulationRequest(BaseModel):
    user_account_id: UUID
    amount: float
    currency: str = "NGN"
    external_reference: str


@router.post(
    "/webhooks/simulate-pay-in",
    status_code=status.HTTP_200_OK,
)
async def simulate_pay_in(
    payload: PayInSimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate a successful external deposit (Pay-In).
    Moves money from the SETTLEMENT account to the USER account.
    """
    from app.schemas.transfer import TransferRequest

    transfer_service = TransferService(db)

    # Hardcoded settlement account ID from seed_accounts.sql
    settlement_account_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        # Webhooks represent external events, so we use is_external=True
        # and move money FROM settlement TO user
        payload_request = TransferRequest(
            source_account_id=settlement_account_id,
            destination_account_id=payload.user_account_id,
            amount=payload.amount,
            currency=payload.currency,
            reference=f"Pay-in: {payload.external_reference}",
        )

        response = await transfer_service.execute(
            payload=payload_request,
            idempotency_key=f"pay-in-{payload.external_reference}",
            is_external=False,  # Settlement accounts are internal participants representing external world
        )
        return {
            "status": "success",
            "transaction_id": response.transaction_id,
            "message": f"Successfully credited {payload.amount} {payload.currency} to {payload.user_account_id}",
        }
    except Exception as e:
        await db.rollback()
        raise map_transfer_exception(e)
