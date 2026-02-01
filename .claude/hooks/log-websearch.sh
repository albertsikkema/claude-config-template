#!/bin/bash
# Log WebSearch queries with timestamp
# Output: thoughts/shared/web-activity.log

INPUT=$(cat)

QUERY=$(echo "$INPUT" | jq -r '.tool_input.query // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' | cut -c1-8)

if [ -n "$QUERY" ]; then
  LOG_FILE="${CLAUDE_PROJECT_DIR}/thoughts/shared/web-activity.log"
  mkdir -p "$(dirname "$LOG_FILE")"

  {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [${SESSION_ID}] SEARCH"
    echo "  Query: $QUERY"
    echo ""
  } >> "$LOG_FILE"
fi

exit 0
