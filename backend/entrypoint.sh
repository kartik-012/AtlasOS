#!/usr/bin/env bash
# ==============================================================================
# AtlasOS Backend Entrypoint
# Runs database migrations before starting the application.
# ==============================================================================
set -e

echo "Starting AtlasOS Backend..."

# Wait for Postgres to be ready (optional, since docker-compose handles this,
# but good practice in case it's run standalone)
# We assume the DB is up if we reached here via docker-compose depends_on

echo "Running Alembic migrations..."
alembic upgrade head

echo "Migrations complete. Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
