#!/usr/bin/env bash

SESSION="agv-prod"
ROOT_DIR="$(pwd)"

# Check if we are already in a tmux session
if [ -n "$TMUX" ]; then
  echo "You are already inside a tmux session. Please detach first or run outside of tmux."
  exit 1
fi

# Check if session already exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Creating new tmux session: $SESSION"

  # Window 1: normal terminal in root directory
  tmux new-session -d -s "$SESSION" -n "terminal" -c "$ROOT_DIR"

  # Window 2: backend production startup
  tmux new-window -t "$SESSION:2" -n "backend" -c "$ROOT_DIR/agv-system"
  tmux send-keys -t "$SESSION:2" "echo 'Starting backend...' && docker-compose up -d --build && docker-compose logs -f" C-m

  # Window 3: frontend production startup
  tmux new-window -t "$SESSION:3" -n "frontend" -c "$ROOT_DIR/agv-gui"
  tmux send-keys -t "$SESSION:3" "echo 'Starting frontend...' && docker-compose up -d --build && docker-compose logs -f" C-m

  # Select the first window ("terminal")
  tmux select-window -t "$SESSION:1"
else
  echo "Session $SESSION already exists. Attaching..."
fi

# Attach to the session
tmux attach-session -t "$SESSION"