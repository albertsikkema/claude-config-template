#!/usr/bin/env python3
"""
Notification hook that plays pre-generated audio when Claude needs user input.

Set CLAUDE_AUDIO_ENABLED=1 to enable audio notifications (disabled by default).
Set CLAUDE_HOOKS_DEBUG=1 to enable debug logging.
"""

import argparse
import os
import sys

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')


def debug_log(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] notification: {message}", file=sys.stderr)


# Import after debug setup so we can catch import errors
try:
    from utils.audio import is_audio_enabled, play_audio
except ImportError as e:
    debug_log(f"Import error: {e}")
    is_audio_enabled = lambda: False
    play_audio = lambda x: None


def main() -> None:
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--notify', action='store_true', help='Enable audio notifications')
        args = parser.parse_args()

        # Consume stdin (required by hook protocol)
        sys.stdin.read()

        if args.notify and is_audio_enabled():
            debug_log("Playing notification audio")
            play_audio("notification")

        sys.exit(0)

    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        sys.exit(0)


if __name__ == '__main__':
    main()
