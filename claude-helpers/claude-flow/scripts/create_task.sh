#!/bin/bash
# Create a new task in the Kanban board
#
# Usage:
#   ./create_task.sh "Task title" "Task description"
#   ./create_task.sh "Task title" "Task description" --priority high
#   ./create_task.sh "Task title" "Task description" --tags "frontend,ui"
#   ./create_task.sh "Task title" "Task description" --model opus
#
# Options:
#   --priority  low|medium|high (default: medium)
#   --tags      Comma-separated tags (default: none)
#   --stage     backlog|research|planning|implementation|review|cleanup|done (default: backlog)
#   --model     sonnet|opus|haiku (default: sonnet)
#               - sonnet: Best balance of speed and capability. Good for most tasks.
#               - opus:   Most capable model. Best for complex research and planning.
#               - haiku:  Fastest and most affordable. Good for simple tasks.

API_URL="${KANBAN_API_URL:-http://localhost:8000/api/tasks}"

# Default values
PRIORITY="medium"
STAGE="backlog"
MODEL="sonnet"
TAGS="[]"

# Parse arguments
TITLE="$1"
DESCRIPTION="$2"
shift 2 2>/dev/null

while [[ $# -gt 0 ]]; do
    case $1 in
        --priority)
            PRIORITY="$2"
            shift 2
            ;;
        --stage)
            STAGE="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --tags)
            # Convert comma-separated to JSON array
            TAGS=$(echo "$2" | sed 's/,/","/g' | sed 's/^/["/' | sed 's/$/"]/')
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$TITLE" ]]; then
    echo "Usage: $0 \"Task title\" \"Task description\" [--priority low|medium|high|critical] [--tags \"tag1,tag2\"]"
    exit 1
fi

# Default description if not provided
DESCRIPTION="${DESCRIPTION:-}"

# Create JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
    "title": "$TITLE",
    "description": "$DESCRIPTION",
    "priority": "$PRIORITY",
    "stage": "$STAGE",
    "model": "$MODEL",
    "tags": $TAGS
}
EOF
)

# Make API request
RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD")

# Check if successful
if echo "$RESPONSE" | grep -q '"id"'; then
    TASK_ID=$(echo "$RESPONSE" | grep -o '"id": *"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✅ Task created: $TASK_ID"
    echo "   Title: $TITLE"
    echo "   Stage: $STAGE"
    echo "   Priority: $PRIORITY"
    echo "   Model: $MODEL"
else
    echo "❌ Failed to create task"
    echo "$RESPONSE"
    exit 1
fi
