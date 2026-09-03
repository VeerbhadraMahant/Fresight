#!/bin/sh
# Container entrypoint.
# When DATABASE_URL is configured (Supabase / Postgres), bring the schema up to
# head and make sure the ports table is seeded before serving. With no
# DATABASE_URL the app runs entirely from the bundled CSV -- unchanged behaviour.
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "[start] DATABASE_URL present -> alembic upgrade head"
  alembic upgrade head
  echo "[start] seeding ports table"
  python scripts/load_ports.py || echo "[start] port seed failed (non-fatal, continuing)"
else
  echo "[start] no DATABASE_URL -> bundled-CSV mode"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
