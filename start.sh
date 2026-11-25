#!/bin/bash

echo "Starting NIRO Telegram Bot..."
python -u bot.py &
BOT_PID=$!

echo "Starting NIRO Mini App..."
python -m uvicorn webapp:app --host 0.0.0.0 --port "${PORT:-8080}" &
WEB_PID=$!

wait
