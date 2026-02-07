#!/usr/bin/env bash
set -euo pipefail

# Collect metadata
DATETIME_TZ=$(date '+%Y-%m-%d %H:%M:%S %Z')
FILENAME_TS=$(date '+%Y-%m-%d_%H-%M-%S')
CURRENT_USER=$(whoami)
CURRENT_PWD=$(pwd)

# Generate UUID for this metadata instance
if command -v uuidgen >/dev/null 2>&1; then
  UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
else
  # Fallback: generate a pseudo-UUID using date and random
  UUID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || \
         printf '%08x-%04x-%04x-%04x-%012x' \
         $RANDOM$RANDOM $RANDOM $RANDOM $RANDOM $RANDOM$RANDOM$RANDOM)
fi

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_ROOT=$(git rev-parse --show-toplevel)
  REPO_NAME=$(basename "$REPO_ROOT")
  GIT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)
  GIT_COMMIT=$(git rev-parse HEAD)
else
  REPO_ROOT=""
  REPO_NAME=""
  GIT_BRANCH=""
  GIT_COMMIT=""
fi

# Find Claude session ID
# When running in Claude Code, find the most recently active session for current directory
CLAUDE_SESSION_ID=""
CURRENT_DIR=$(pwd)
PROJECTS_DIR="$HOME/.claude/projects"

if [ -d "$PROJECTS_DIR" ]; then
  # Find the most recently modified session file matching current directory
  # Note: This will be the active session since it's being written to
  MOST_RECENT=0
  shopt -s nullglob 2>/dev/null || true
  for project_dir in "$PROJECTS_DIR"/*; do
    if [ -d "$project_dir" ]; then
      for session_file in "$project_dir"/*.jsonl; do
        [ -f "$session_file" ] || continue

        # Check if session's cwd matches current directory
        session_cwd=$(head -n 20 "$session_file" 2>/dev/null | \
                      grep -m 1 '"cwd"' 2>/dev/null | \
                      sed -E 's/.*"cwd":"([^"]+)".*/\1/' 2>/dev/null || echo "")

        if [ "$session_cwd" = "$CURRENT_DIR" ]; then
          # Use modification time (most recently written = active session)
          mtime=$(stat -c "%Y" "$session_file" 2>/dev/null || stat -f "%m" "$session_file" 2>/dev/null || echo 0)
          if [ "$mtime" -gt "$MOST_RECENT" ]; then
            MOST_RECENT=$mtime
            CLAUDE_SESSION_ID=$(basename "$session_file" .jsonl)
          fi
        fi
      done
    fi
  done
  shopt -u nullglob 2>/dev/null || true
fi

# Optional: memories system status (may be long). Limit lines to avoid noise.
MEMORIES_STATUS=""
if command -v humanlayer >/dev/null 2>&1; then
  # Capture first 40 lines; adjust as needed.
  MEMORIES_STATUS=$(humanlayer memories status 2>/dev/null | head -n 40)
fi

# Print similar to the individual command outputs
echo "UUID: $UUID"
echo "Current Date/Time (TZ): $DATETIME_TZ"
echo "Current User: $CURRENT_USER"
echo "Current Working Directory: $CURRENT_PWD"
[ -n "$GIT_COMMIT" ] && echo "Current Git Commit Hash: $GIT_COMMIT"
[ -n "$GIT_BRANCH" ] && echo "Current Branch Name: $GIT_BRANCH"
[ -n "$REPO_NAME" ] && echo "Repository Name: $REPO_NAME"
[ -n "$CLAUDE_SESSION_ID" ] && echo "claude-sessionid: $CLAUDE_SESSION_ID"
echo "Timestamp For Filename: $FILENAME_TS"
if [ -n "$MEMORIES_STATUS" ]; then
  echo "$MEMORIES_STATUS"
fi
