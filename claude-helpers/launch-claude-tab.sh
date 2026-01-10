#!/bin/bash
# Launch a Claude session in iTerm with title and color
# Usage: launch-claude-tab.sh <task_id> <task_title> <stage> <project_dir> <model> [prompt] [resume_session_id]

set -e

# Ensure common paths are available (for non-login shells)
export PATH="$HOME/.local/bin:$HOME/bin:/usr/local/bin:$PATH"

TASK_ID="${1:-task}"
TASK_TITLE="${2:-Task}"
STAGE="${3:-default}"
PROJECT_DIR="${4:-$(pwd)}"
MODEL="${5:-sonnet}"
PROMPT="${6:-}"
RESUME_SESSION_ID="${7:-}"

# Sanitize tab name (remove special chars, keep alphanumeric, spaces, hyphens, dots)
TAB_NAME=$(echo "${TASK_ID:0:8} ${TASK_TITLE:0:50}" | tr -c '[:alnum:] .\-' ' ' | tr -s ' ')

# Get RGB color for stage
case "$STAGE" in
    research)       R=255; G=180; B=0 ;;    # Orange
    planning)       R=138; G=92;  B=246 ;;  # Purple
    implementation) R=59;  G=130; B=246 ;;  # Blue
    review)         R=249; G=115; B=22 ;;   # Orange-red
    cleanup)        R=6;   G=182; B=212 ;;  # Cyan
    *)              R=100; G=100; B=100 ;;  # Gray
esac

# Set terminal title
printf '\e]0;%s\a' "$TAB_NAME"

# Set iTerm2 tab color
printf '\e]6;1;bg;red;brightness;%d\a' "$R"
printf '\e]6;1;bg;green;brightness;%d\a' "$G"
printf '\e]6;1;bg;blue;brightness;%d\a' "$B"

# Change to project directory
cd "$PROJECT_DIR"

# Clear screen
clear

# Export task ID for hooks to use (hooks can't access our session_id)
export CLAUDE_FLOW_TASK_ID="$TASK_ID"

# Start Claude
if [ -n "$RESUME_SESSION_ID" ]; then
    # Resume existing session
    exec claude --dangerously-skip-permissions --resume "$RESUME_SESSION_ID"
elif [ -n "$PROMPT" ]; then
    # New session with prompt
    exec claude --dangerously-skip-permissions --model "$MODEL" "$PROMPT"
else
    # New session without prompt
    exec claude --dangerously-skip-permissions --model "$MODEL"
fi
