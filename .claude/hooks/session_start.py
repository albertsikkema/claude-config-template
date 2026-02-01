#!/usr/bin/env python3
"""
Session start hook that loads development context into the session.

Set CLAUDE_HOOKS_DEBUG=1 to enable debug logging.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')


def debug_log(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] session_start: {message}", file=sys.stderr)


def get_git_status() -> tuple[str | None, int | None]:
    """Get current git status information."""
    try:
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Get uncommitted changes count
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if status_result.returncode == 0:
            changes = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
            uncommitted_count = len(changes)
        else:
            uncommitted_count = 0

        debug_log(f"Git status: branch={current_branch}, changes={uncommitted_count}")
        return current_branch, uncommitted_count
    except subprocess.TimeoutExpired:
        debug_log("Git command timed out")
        return None, None
    except Exception as e:
        debug_log(f"Git error: {e}")
        return None, None


def get_recent_issues() -> str | None:
    """Get recent GitHub issues if gh CLI is available."""
    try:
        # Check if gh is available using shutil.which (more Pythonic)
        if not shutil.which('gh'):
            debug_log("gh CLI not found")
            return None

        # Get recent open issues
        result = subprocess.run(
            ['gh', 'issue', 'list', '--limit', '5', '--state', 'open'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            debug_log(f"Found {len(result.stdout.strip().splitlines())} issues")
            return result.stdout.strip()
    except subprocess.TimeoutExpired:
        debug_log("gh command timed out")
    except Exception as e:
        debug_log(f"gh error: {e}")
    return None


def load_development_context(source: str) -> str:
    """Load relevant development context based on session source."""
    context_parts = []

    # Add timestamp
    context_parts.append(f"Session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_parts.append(f"Session source: {source}")

    # Add git information
    branch, changes = get_git_status()
    if branch:
        context_parts.append(f"Git branch: {branch}")
        if changes and changes > 0:
            context_parts.append(f"Uncommitted changes: {changes} files")

    # Load project-specific context files if they exist
    context_files = [
        ".claude/CONTEXT.md",
        ".claude/TODO.md",
        "TODO.md",
        ".github/ISSUE_TEMPLATE.md"
    ]

    for file_path in context_files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        context_parts.append(f"\n--- Content from {file_path} ---")
                        context_parts.append(content[:1000])  # Limit to first 1000 chars
                        debug_log(f"Loaded context from: {file_path}")
            except Exception as e:
                debug_log(f"Error loading {file_path}: {e}")

    # Add recent issues if available
    issues = get_recent_issues()
    if issues:
        context_parts.append("\n--- Recent GitHub Issues ---")
        context_parts.append(issues)

    return "\n".join(context_parts)


def main() -> None:
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--load-context', action='store_true',
                          help='Load development context at session start')
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract fields
        source = input_data.get('source', 'unknown')  # "startup", "resume", or "clear"
        debug_log(f"Session source: {source}")

        # Load development context if requested
        if args.load_context:
            context = load_development_context(source)
            if context:
                # Using JSON output to add context
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": context
                    }
                }
                print(json.dumps(output))
                sys.exit(0)

        # Success
        sys.exit(0)

    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(0)
    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        sys.exit(0)


if __name__ == '__main__':
    main()
