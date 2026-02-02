#!/bin/bash
# Log WebSearch results as JSONL
# Output: memories/logs/web-searches.jsonl

INPUT=$(cat)

QUERY=$(echo "$INPUT" | jq -r '.tool_input.query // empty')

if [ -n "$QUERY" ]; then
  LOG_FILE="${CLAUDE_PROJECT_DIR}/memories/logs/web-searches.jsonl"
  mkdir -p "$(dirname "$LOG_FILE")"

  # Keep it simple: timestamp, session_id, query, and full results array
  echo "$INPUT" | jq -c '{
    timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
    session_id: .session_id,
    query: .tool_input.query,
    results: .tool_response.results
  }' >> "$LOG_FILE"
fi

exit 0
