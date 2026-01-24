import json
from hashlib import sha256

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import IdempotencyKeyConflictError
from app.models.idempotency import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_payload(payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True).encode()
        return sha256(encoded).hexdigest()

    async def get_existing(
        self,
        *,
        key: str,
        scope: str,
    ) -> IdempotencyKey | None:
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.key == key,
            IdempotencyKey.scope == scope,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def store_new(
        self,
        *,
        key: str,
        scope: str,
        payload: dict,
        response_body: str | None = None,
    ) -> None:
        payload_hash = self._hash_payload(payload)

        # Fast-path: if a record already exists, validate payload and return it
        existing = await self.get_existing(key=key, scope=scope)
        if existing:
            if existing.request_hash != payload_hash:
                raise IdempotencyKeyConflictError(
                    "Idempotency key reused with different payload"
                )
            return existing, False

        # Try to insert; use INSERT ... RETURNING for a single roundtrip.
        try:
            stmt = (
                insert(IdempotencyKey)
                .values(
                    key=key,
                    scope=scope,
                    request_hash=payload_hash,
                    response_body=response_body,
                )
                .returning(IdempotencyKey)
            )

            await self.session.execute(stmt)
            # flush to ensure DB constraints are evaluated now
            await self.session.flush()

            # return the newly created record
            record = await self.get_existing(key=key, scope=scope)
            return record, True

        except IntegrityError:
            # race: another txn inserted the same key. Re-fetch and validate.
            existing = await self.get_existing(key=key, scope=scope)
            if not existing:
                # Something unexpected; surface conflict
                raise IdempotencyKeyConflictError()

            if existing.request_hash != payload_hash:
                raise IdempotencyKeyConflictError(
                    "Idempotency key reused with different payload"
                )

            return existing, False

    async def update_response(
        self,
        *,
        key: str,
        scope: str,
        response_body: str,
    ) -> None:
        stmt = (
            update(IdempotencyKey)
            .where(IdempotencyKey.key == key, IdempotencyKey.scope == scope)
            .values(response_body=response_body)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def validate_or_reuse(
        self,
        *,
        key: str,
        scope: str,
        payload: dict,
    ) -> IdempotencyKey | None:
        existing = await self.get_existing(key=key, scope=scope)

        if not existing:
            return None

        payload_hash = self._hash_payload(payload)

        if existing.request_hash != payload_hash:
            raise IdempotencyKeyConflictError(
                "Idempotency key reused with different payload"
            )
        return existing
