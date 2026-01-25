"""
Simulation webhooks for testing.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import map_transfer_exception
from app.db.db import get_db
from app.schemas.webhook import PayInSimulationRequest
from app.services.simulation_service import SimulationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])


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
    Delegates to SimulationService.
    """
    service = SimulationService(db)

    try:
        response = await service.simulate_pay_in(
            user_account_id=payload.user_account_id,
            amount=payload.amount,
            currency=payload.currency,
            external_reference=payload.external_reference,
        )
        await db.commit()
        return {
            "status": "success",
            "transaction_id": response.transaction_id,
            "message": f"Successfully credited {payload.amount} {payload.currency} to {payload.user_account_id}",
        }
    except Exception as e:
        await db.rollback()
        raise map_transfer_exception(e)
