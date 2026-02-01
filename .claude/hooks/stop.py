#!/usr/bin/env python3
"""
Stop hook that plays pre-generated audio when Claude completes a task.
Used for both Stop and SubagentStop hooks.

Set CLAUDE_AUDIO_ENABLED=1 to enable audio notifications (disabled by default).
Set CLAUDE_HOOKS_DEBUG=1 to enable debug logging.
"""

import argparse
import json
import os
import sys

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')

# Minimum number of tool uses to consider a response "substantial"
MIN_TOOL_USES_FOR_AUDIO = 2


def debug_log(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] stop: {message}", file=sys.stderr)


# Import after debug setup so we can catch import errors
try:
    from utils.audio import is_audio_enabled, play_audio
except ImportError as e:
    debug_log(f"Import error: {e}")
    is_audio_enabled = lambda: False
    play_audio = lambda x: None


def is_substantial_response(input_data: dict) -> bool:
    """Check if the response was substantial enough to warrant audio."""
    # Check for tool usage count
    num_tool_uses = input_data.get("num_tool_uses", 0)
    if num_tool_uses >= MIN_TOOL_USES_FOR_AUDIO:
        debug_log(f"Substantial response: {num_tool_uses} tool uses")
        return True

    # Check for total turns (API round-trips)
    num_turns = input_data.get("num_turns", 0)
    if num_turns >= MIN_TOOL_USES_FOR_AUDIO:
        debug_log(f"Substantial response: {num_turns} turns")
        return True

    debug_log(f"Simple response: {num_tool_uses} tools, {num_turns} turns")
    return False


def main() -> None:
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--filter-simple', action='store_true',
                          help='Skip audio for simple responses')
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Check if audio is enabled
        if not is_audio_enabled():
            debug_log("Audio disabled")
            sys.exit(0)

        # If filtering is enabled, only play for substantial responses
        if args.filter_simple:
            if not is_substantial_response(input_data):
                sys.exit(0)

        debug_log("Playing completion audio")
        play_audio("completion")
        sys.exit(0)

    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(0)
    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        sys.exit(0)


if __name__ == '__main__':
    main()
