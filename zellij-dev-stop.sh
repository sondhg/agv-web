#!/usr/bin/env bash

SESSION="agv-dev"
ROOT_DIR="$(pwd)"

echo "🛑 Stopping backend containers..."
if [ -d "$ROOT_DIR/agv-system" ]; then
  cd "$ROOT_DIR/agv-system" && docker-compose down
else
  echo "Warning: agv-system directory not found, skipping docker-compose down."
fi

echo "🛑 Killing Zellij session '$SESSION'..."
# Check if the session exists before trying to kill it
if zellij list-sessions -n 2>/dev/null | grep -q "\b$SESSION\b"; then
  zellij kill-session "$SESSION"
  echo "✅ Zellij session killed successfully."
else
  echo "ℹ️ Zellij session '$SESSION' was not running."
fi

echo "✨ Everything stopped cleanly!"
