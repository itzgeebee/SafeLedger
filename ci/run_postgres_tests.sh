#!/usr/bin/env bash
set -euo pipefail

# Start docker compose and wait for Postgres
docker compose up -d postgres

echo "Waiting for Postgres to be ready..."
until docker compose exec -T postgres pg_isready -U safeledger -d safeledger_test >/dev/null 2>&1; do
  sleep 1
done

echo "Running tests against Postgres..."
# Export DATABASE_URL for tests
export DATABASE_URL=postgresql+asyncpg://safeledger:safeledger@127.0.0.1:5432/safeledger_test

pytest -q

EXIT_CODE=$?

docker compose down
exit $EXIT_CODE
