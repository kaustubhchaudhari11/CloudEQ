#!/usr/bin/env sh
# FORGE SPAN on macOS/Linux: install and start the dashboard (offline simulation mode).
set -e
cd "$(dirname "$0")/.."
uv sync
echo "Open http://127.0.0.1:8000 in your browser. Ctrl+C to stop."
uv run cloudeq-server
