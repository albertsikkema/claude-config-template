#!/bin/bash
# Log WebSearch queries and results with timestamp
# Output: thoughts/shared/web-activity.log

INPUT=$(cat)

QUERY=$(echo "$INPUT" | jq -r '.tool_input.query // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' | cut -c1-8)

# Extract URLs from tool_response (search results)
URLS=$(echo "$INPUT" | jq -r '.tool_response // empty | if type == "string" then . else empty end' | grep -oE 'https?://[^)>\s"]+' | head -10)

if [ -n "$QUERY" ]; then
  LOG_FILE="${CLAUDE_PROJECT_DIR}/thoughts/shared/web-activity.log"
  mkdir -p "$(dirname "$LOG_FILE")"

  {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [${SESSION_ID}] SEARCH"
    echo "  Query: $QUERY"
    if [ -n "$URLS" ]; then
      echo "  Results:"
      echo "$URLS" | while read -r url; do
        echo "    - $url"
      done
    fi
    echo ""
  } >> "$LOG_FILE"
fi

exit 0
