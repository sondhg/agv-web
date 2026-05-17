#!/usr/bin/env bash

SESSION="agv-dev"
ROOT_DIR="$(pwd)"

# Check if we are already in a tmux session
if [ -n "$TMUX" ]; then
  echo "You are already inside a tmux session. Please detach first or run outside of tmux."
  exit 1
fi

# Check if session already exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Creating new tmux session: $SESSION"

  # Window 1: nvim in root directory
  tmux new-session -d -s "$SESSION" -n "nvim" -c "$ROOT_DIR"
  tmux send-keys -t "$SESSION:1" "nvim" C-m

  # Window 2: normal terminal in root directory
  tmux new-window -t "$SESSION:2" -n "terminal" -c "$ROOT_DIR"

  # Window 3: opencode in root directory
  tmux new-window -t "$SESSION:3" -n "opencode" -c "$ROOT_DIR"
  tmux send-keys -t "$SESSION:3" "opencode" C-m

  # Window 4: frontend (agv-gui)
  tmux new-window -t "$SESSION:4" -n "frontend" -c "$ROOT_DIR/agv-gui"
  tmux send-keys -t "$SESSION:4" "pnpm install && pnpm dev" C-m

  # Window 5: backend (agv-system)
  tmux new-window -t "$SESSION:5" -n "backend" -c "$ROOT_DIR/agv-system"
  tmux send-keys -t "$SESSION:5" "docker-compose up -d && docker-compose logs -f" C-m

  # Select the first window ("nvim")
  tmux select-window -t "$SESSION:1"
else
  echo "Session $SESSION already exists. Attaching..."
fi

# Attach to the session
tmux attach-session -t "$SESSION"
