from app.infrastructure.repositories.idempotency_repo import IdempotencyRepository
from app.observability import record_metric


class IdempotencyService:
    def __init__(self, repo: IdempotencyRepository):
        self.repo = repo

    async def check_or_fail(
        self,
        *,
        key: str,
        scope: str,
        payload: dict,
    ):
        """
        Validate idempotency key.
        Returns existing record if present and valid.
        """
        existing = await self.repo.validate_or_reuse(
            key=key,
            scope=scope,
            payload=payload,
        )
        return existing

    async def record(
        self,
        *,
        key: str,
        scope: str,
        payload: dict,
        response_body: str | None = None,
    ):
        # If response_body is None we are reserving the key before processing.
        if response_body is None:
            # reservation attempt
            record_metric("idempotency.reserve.attempt", 1, {"scope": scope})
            res = await self.repo.store_new(
                key=key,
                scope=scope,
                payload=payload,
                response_body=None,
            )
            record_metric("idempotency.reserve.result", 1, {"scope": scope})
            return res

        # Otherwise, update the existing idempotency record with the final response.
        existing = await self.repo.get_existing(key=key, scope=scope)
        if not existing:
            # No existing reservation found: try to insert with response_body
            res = await self.repo.store_new(
                key=key,
                scope=scope,
                payload=payload,
                response_body=response_body,
            )
            # repo.store_new may return (record, created) when inserting; normalize to record
            if isinstance(res, tuple):
                return res[0]
            return res

        # Update the response body on the reserved record
        await self.repo.update_response(
            key=key, scope=scope, response_body=response_body
        )
        record_metric("idempotency.update_response", 1, {"scope": scope})
        return existing
