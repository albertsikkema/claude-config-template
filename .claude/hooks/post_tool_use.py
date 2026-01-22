#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["requests"]
# ///

import json
import os
import sys
from pathlib import Path

# API base URL for claude-flow backend
CLAUDE_FLOW_API = os.environ.get("CLAUDE_FLOW_API", "http://localhost:9118")


def notify_artifact_created(task_id: str | None, session_id: str, file_path: str):
    """Notify claude-flow backend about artifact creation."""
    import requests

    try:
        resp = requests.post(
            f"{CLAUDE_FLOW_API}/api/hooks/artifact-created",
            json={"task_id": task_id, "session_id": session_id, "file_path": file_path},
            timeout=2
        )
        # Log to stderr for debugging (won't affect hook)
        print(f"artifact-created: {resp.status_code} (task={task_id})", file=sys.stderr)
    except Exception as e:
        print(f"artifact-created error: {e}", file=sys.stderr)


def update_task_session_id(task_id: str, claude_session_id: str):
    """Update task with Claude's real session ID for resume functionality."""
    import requests

    try:
        requests.put(
            f"{CLAUDE_FLOW_API}/api/tasks/{task_id}",
            json={"session_id": claude_session_id},
            timeout=2
        )
    except Exception:
        pass  # Silently ignore - not critical


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Extract session_id and task_id
        session_id = input_data.get('session_id', 'unknown')
        task_id = os.environ.get('CLAUDE_FLOW_TASK_ID')  # Set by launch script

        # Update task with Claude's real session_id (once per session)
        # Use a marker file to avoid repeated API calls
        if task_id and session_id and session_id != 'unknown':
            marker = Path(f"/tmp/.claude_flow_session_{task_id}")
            if not marker.exists():
                update_task_session_id(task_id, session_id)
                marker.touch()

        # Check for Write tool operations to thoughts/shared directories
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        if tool_name == 'Write' and isinstance(tool_input, dict):
            file_path = tool_input.get('file_path', '')
            # Check if it's a research, plan, or review file
            if 'thoughts/shared' in file_path:
                notify_artifact_created(task_id, session_id, file_path)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception as e:
        # Log error but exit cleanly
        print(f"post_tool_use error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()