#!/usr/bin/env bash

SESSION="agv-dev"
ROOT_DIR="$(pwd)"
LAYOUT_FILE="$ROOT_DIR/.zellij-dev-layout.kdl"

# Check if we are already inside a Zellij session
if [ -n "$ZELLIJ" ]; then
  echo "You are already inside a Zellij session. Please detach first or run outside of Zellij."
  exit 1
fi

# Clean up dead (EXITED) sessions first to avoid attachment conflicts
if zellij list-sessions -n 2>/dev/null | grep -q "^$SESSION.*EXITED"; then
  echo "Cleaning up dead session..."
  zellij delete-session "$SESSION" 2>/dev/null
fi

# Check if an active session already exists
if zellij list-sessions -n 2>/dev/null | grep -q "^$SESSION"; then
  echo "Session $SESSION already exists. Attaching..."
  zellij attach "$SESSION"
  exit 0
fi

echo "Creating new Zellij session: $SESSION"

# Generate the KDL layout on the fly
cat <<EOF >"$LAYOUT_FILE"
layout {
    default_tab_template {
        pane size=1 borderless=true {
            plugin location="zellij:tab-bar"
        }
        children
        pane size=2 borderless=true {
            plugin location="zellij:status-bar"
        }
    }
    
    tab name="nvim" focus=true {
        pane command="nvim" cwd="$ROOT_DIR"
    }
    
    tab name="terminal" {
        pane cwd="$ROOT_DIR"
    }
    
    tab name="opencode" {
        pane command="bash" cwd="$ROOT_DIR" {
            args "-c" "opencode; exec \$SHELL"
        }
    }
    
    tab name="frontend" {
        pane command="bash" cwd="$ROOT_DIR/agv-gui" {
            args "-c" "pnpm install && pnpm dev; exec \$SHELL"
        }
    }
    
    tab name="backend" {
        pane command="bash" cwd="$ROOT_DIR/agv-system" {
            args "-c" "docker-compose up -d && docker-compose logs -f; exec \$SHELL"
        }
    }
}
EOF

# Start the session using the explicit new-session flag
zellij --session "$SESSION" --new-session-with-layout "$LAYOUT_FILE"

# Clean up the layout file after Zellij exits or detaches
rm -f "$LAYOUT_FILE"
