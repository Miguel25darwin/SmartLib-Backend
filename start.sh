#!/bin/bash
set -e

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
