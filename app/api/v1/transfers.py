import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import map_transfer_exception
from app.api.v1.utils import get_client_ip, get_request_id
from app.db.db import get_db
from app.middleware.auth import CurrentUser, verify_jwt
from app.middleware.rate_limit import rate_limit
from app.schemas.transfer import Transfer, TransferRequest, TransferResponse
from app.services.audit_service import AuditService
from app.services.reversal_services import ReversalService
from app.services.transfer_service import TransferService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transfers"])


# Endpoints


@router.post(
    "/transfers",
    response_model=TransferResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def create_p2p_transfer(
    payload: TransferRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    service = TransferService(db)
    audit = AuditService(db)

    try:
        response = await service.execute(
            payload=payload,
            idempotency_key=idempotency_key,
        )

        # Audit log the successful transfer
        await audit.log_transfer(
            transaction_id=str(response.transaction_id),
            source_account_id=str(response.source_account_id),
            destination_account_id=str(response.destination_account_id),
            amount=str(response.amount),
            currency=response.currency,
            actor_id=current_user.user_id,
            ip_address=get_client_ip(request),
            request_id=get_request_id(request),
        )

        return response
    except Exception as e:
        await db.rollback()
        raise map_transfer_exception(e)


@router.post(
    "/transfers/external",
    response_model=TransferResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def create_external_transfer(
    payload: Transfer,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    service = TransferService(db)
    audit = AuditService(db)

    try:
        response = await service.execute(
            payload=payload,
            idempotency_key=idempotency_key,
            is_external=True,
        )

        # Audit log the successful transfer
        await audit.log_transfer(
            transaction_id=str(response.transaction_id),
            source_account_id=str(response.source_account_id),
            destination_account_id=str(response.destination_account_id),
            amount=str(response.amount),
            currency=response.currency,
            actor_id=current_user.user_id,
            ip_address=get_client_ip(request),
            request_id=get_request_id(request),
        )

        return response
    except Exception as e:
        await db.rollback()
        raise map_transfer_exception(e)


@router.post(
    "/transfers/{transaction_id}/reversal",
    response_model=TransferResponse,
    dependencies=[Depends(verify_jwt), Depends(rate_limit)],
)
async def reverse_transfer(
    transaction_id: UUID,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    service = ReversalService(db)
    audit = AuditService(db)

    try:
        response = await service.execute(
            original_transaction_id=transaction_id,
            idempotency_key=idempotency_key,
        )

        # Audit log the reversal
        await audit.log_reversal(
            reversal_transaction_id=str(response.transaction_id),
            original_transaction_id=str(transaction_id),
            actor_id=current_user.user_id,
            ip_address=get_client_ip(request),
            request_id=get_request_id(request),
        )

        return response
    except Exception as e:
        await db.rollback()
        raise map_transfer_exception(e)
