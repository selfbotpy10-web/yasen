#!/bin/bash
set -e

echo "Starting NIRO SELF..."

if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: BOT_TOKEN is missing!"
    exit 1
fi

python -u bot.py &
BOT_PID=$!

python -u -m uvicorn webapp:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" &
WEB_PID=$!

cleanup() {
    kill "$BOT_PID" "$WEB_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait -n "$BOT_PID" "$WEB_PID"
