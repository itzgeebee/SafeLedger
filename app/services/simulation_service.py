import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.transfer import TransferRequest, TransferResponse
from app.services.transfer_service import TransferService

logger = logging.getLogger(__name__)


class SimulationService:
    """
    Service for simulating external events for testing and development.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.transfer_service = TransferService(session)

    async def simulate_pay_in(
        self,
        user_account_id: UUID,
        amount: float,
        currency: str,
        external_reference: str,
    ) -> TransferResponse:
        """
        Simulate an external pay-in by transferring from the SETTLEMENT account.
        """
        # Hardcoded settlement account ID from seed_accounts.sql
        settlement_account_id = UUID("00000000-0000-0000-0000-000000000001")

        payload_request = TransferRequest(
            source_account_id=settlement_account_id,
            destination_account_id=user_account_id,
            amount=amount,
            currency=currency,
            reference=f"Pay-in: {external_reference}",
        )

        response = await self.transfer_service.execute(
            payload=payload_request,
            idempotency_key=f"pay-in-{external_reference}",
            is_external=False,  # Settlement is an internal proxy for external world
        )

        logger.info(f"Simulated pay-in successful: {response.transaction_id}")
        return response
