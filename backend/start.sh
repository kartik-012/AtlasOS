#!/bin/sh
# Railway injects PORT as an env variable — this script expands it properly
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
