#!/bin/bash
# Log WebFetch results as JSONL
# Output: memories/logs/web-fetches.jsonl

INPUT=$(cat)

URL=$(echo "$INPUT" | jq -r '.tool_input.url // empty')

if [ -n "$URL" ]; then
  LOG_FILE="${CLAUDE_PROJECT_DIR}/memories/logs/web-fetches.jsonl"
  mkdir -p "$(dirname "$LOG_FILE")"

  # Keep: timestamp, session_id, url, prompt, status, and the AI result
  echo "$INPUT" | jq -c '{
    timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
    session_id: .session_id,
    url: .tool_input.url,
    prompt: .tool_input.prompt,
    status: .tool_response.code,
    result: .tool_response.result
  }' >> "$LOG_FILE"
fi

exit 0
