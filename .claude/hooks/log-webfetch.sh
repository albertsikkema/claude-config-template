#!/bin/bash
# Log WebFetch URLs with prompt and timestamp
# Output: thoughts/shared/web-activity.log

INPUT=$(cat)

URL=$(echo "$INPUT" | jq -r '.tool_input.url // empty')
PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' | cut -c1-8)

if [ -n "$URL" ]; then
  LOG_FILE="${CLAUDE_PROJECT_DIR}/thoughts/shared/web-activity.log"
  mkdir -p "$(dirname "$LOG_FILE")"

  {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [${SESSION_ID}] FETCH"
    echo "  URL: $URL"
    echo "  Prompt: $PROMPT"
    echo ""
  } >> "$LOG_FILE"
fi

exit 0
