#!/usr/bin/env bash
set -euo pipefail

# Start docker compose and wait for Postgres
docker compose up -d postgres

echo "Waiting for Postgres to be ready..."
# Use environment variables if present, fallback to defaults
DB_USER=${POSTGRES_USER:-safeledger}
DB_NAME=${POSTGRES_DB:-safeledger_test}

MAX_RETRIES=30
COUNT=0

until docker compose exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "Error: Postgres was not ready after $MAX_RETRIES seconds."
    echo "--- Postgres Logs ---"
    docker compose logs postgres
    echo "--- Container Status ---"
    docker compose ps
    docker compose down
    exit 1
  fi
  sleep 1
done

echo "Postgres is ready!"

echo "Running tests against Postgres..."
# Export DATABASE_URL for tests if not already set
export DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://$DB_USER:$DB_USER@127.0.0.1:5432/$DB_NAME}

pytest -v

EXIT_CODE=$?

docker compose down
exit $EXIT_CODE
