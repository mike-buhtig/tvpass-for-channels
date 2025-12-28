#!/usr/bin/env bash
set -euo pipefail

# First update immediately (don’t fail container if upstream is flaky)
echo "[entrypoint] initial update..."
/app/scripts/run_update.sh || echo "[entrypoint] initial update failed (will retry on schedule)"

INTERVAL_MINUTES="${UPDATE_INTERVAL_MINUTES:-30}"
SLEEP_SECONDS=$((INTERVAL_MINUTES * 60))

# Background loop
(
  while true; do
    sleep "$SLEEP_SECONDS"
    echo "[entrypoint] scheduled update..."
    /app/scripts/run_update.sh || echo "[entrypoint] scheduled update failed"
  done
) &

# Run the web server in foreground
exec python3 /app/server.py
