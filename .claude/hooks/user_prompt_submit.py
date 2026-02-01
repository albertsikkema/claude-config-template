#!/usr/bin/env python3
"""
User prompt validation hook that blocks prompts containing sensitive data.

Set CLAUDE_HOOKS_DEBUG=1 to enable debug logging.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')

# Security patterns to block in user prompts
BLOCKED_PATTERNS = [
    # API Keys and Secrets
    ('AKIA', 'AWS Access Key detected'),
    ('sk-', 'OpenAI/Anthropic API key detected'),
    ('ghp_', 'GitHub Personal Access Token detected'),
    ('gho_', 'GitHub OAuth Token detected'),
    ('github_pat_', 'GitHub PAT detected'),
    ('xoxb-', 'Slack Bot Token detected'),
    ('xoxp-', 'Slack User Token detected'),
    ('-----BEGIN RSA PRIVATE KEY-----', 'RSA Private Key detected'),
    ('-----BEGIN OPENSSH PRIVATE KEY-----', 'SSH Private Key detected'),
    ('-----BEGIN PGP PRIVATE KEY-----', 'PGP Private Key detected'),
]


def debug_log(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] user_prompt_submit: {message}", file=sys.stderr)


def validate_prompt(prompt: str) -> tuple[bool, str | None]:
    """
    Validate the user prompt for security or policy violations.
    Returns tuple (is_valid, reason).
    """
    prompt_lower = prompt.lower()

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.lower() in prompt_lower:
            debug_log(f"Blocked pattern found: {pattern}")
            return False, reason

    debug_log("Prompt validation passed")
    return True, None


def main() -> None:
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--validate', action='store_true',
                          help='Enable prompt validation')
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract prompt
        prompt = input_data.get('prompt', '')
        debug_log(f"Received prompt of length: {len(prompt)}")

        # Validate prompt if requested
        if args.validate:
            is_valid, reason = validate_prompt(prompt)
            if not is_valid:
                # Exit code 2 blocks the prompt with error message
                print(f"Prompt blocked: {reason}", file=sys.stderr)
                sys.exit(2)

        # Success - prompt will be processed
        sys.exit(0)

    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(0)
    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        sys.exit(0)


if __name__ == '__main__':
    main()
