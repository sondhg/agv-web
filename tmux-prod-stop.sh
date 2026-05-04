#!/usr/bin/env bash

SESSION="agv-prod"
ROOT_DIR="$(pwd)"

echo "🛑 Stopping backend containers..."
if [ -d "$ROOT_DIR/agv-system" ]; then
  cd "$ROOT_DIR/agv-system" && docker-compose down
else
  echo "Warning: agv-system directory not found, skipping backend stop."
fi

echo "🛑 Stopping frontend containers..."
if [ -d "$ROOT_DIR/agv-gui" ]; then
  cd "$ROOT_DIR/agv-gui" && docker-compose down
else
  echo "Warning: agv-gui directory not found, skipping frontend stop."
fi

echo "🛑 Killing tmux session '$SESSION'..."
if tmux kill-session -t "$SESSION" 2>/dev/null; then
  echo "✅ Tmux session killed successfully."
else
  echo "ℹ️ Tmux session '$SESSION' was not running."
fi

echo "✨ Everything stopped cleanly!"
