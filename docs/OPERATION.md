# Operational Runbook — Idempotency & Reservations

This short runbook describes what to do if idempotency reservations become stuck or you observe unusual behavior in production.

1. Symptoms

   - Stalled transfers returning 409 / DuplicateTransactionError
   - Long-running transactions waiting on advisory locks
   - Idempotency records present without `response_body` for longer than expected

2. Immediate checks

   - Inspect DB: `SELECT * FROM idempotency_keys WHERE response_body IS NULL ORDER BY created_at DESC LIMIT 50;`
   - Check for long-running transactions: `SELECT * FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '30 seconds';`
   - Check advisory lock contention: query `pg_locks` and `pg_stat_activity` to find waiters.

3. Recovery steps

   - If a transaction is genuinely stuck, first identify if it's a worker or a request; restart the offending process only after confirming it is safe.
   - For idempotency records without response bodies older than a threshold (e.g., 15 minutes), investigate logs; only manually populate `response_body` if you can deterministically reconstruct the original response.
   - Never delete idempotency records as a shortcut — prefer safe reconciliation or reversal flows.

4. Preventive measures
   - Add observability for `idempotency.reserve.attempt`, `idempotency.reserve.result`, and `transfer.idempotency.duplicate_inflight` (already present in codebase's lightweight stubs).
   - Monitor advisory-lock wait durations and alert on high percentiles.
   - Add a reconciliation job to detect and surface long-running reservations.
