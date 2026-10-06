#!/bin/sh
set -eu

# Apply database migrations before starting the server.
# With several replicas, set RUN_MIGRATIONS=0 and run `alembic upgrade head` as a one-off job.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    alembic upgrade head
fi

# exec so that uvicorn becomes PID 1 and receives SIGTERM directly (graceful shutdown).
exec "$@"
