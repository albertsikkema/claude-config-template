#!/usr/bin/env python3
"""
Generate ~/.claude/settings.local.json for container interactive mode.

Writes permissive tool permissions to the user-home settings file so
interactive Claude sessions inside containers auto-allow all tools.
Non-interactive scripts should use --dangerously-skip-permissions instead.

Usage:
    python3 generate_settings.py              # Auto-detect from CLAUDE_CONTAINER_MODE
    python3 generate_settings.py --container  # Force container permissions
    python3 generate_settings.py --baseline   # Force baseline permissions
    python3 generate_settings.py --check      # Print mode, don't write
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CONTAINER_PERMISSIONS = {
    "permissions": {
        "allow": [
            "Bash(*)",
            "Read(*)",
            "Edit(*)",
            "MultiEdit(*)",
            "Write(*)",
            "Glob(*)",
            "Grep(*)",
            "WebSearch",
            "WebFetch(*)",
            "NotebookEdit(*)",
            "TodoRead",
            "TodoWrite",
            "Task(*)",
        ]
    }
}

BASELINE_PERMISSIONS = {
    "permissions": {
        "allow": [
            "Read",
            "Glob",
            "Grep",
            "WebSearch",
            "WebFetch(*)",
            "TodoRead",
            "Task(*)",
            "Bash(.claude/helpers/spec_metadata.sh)",
            "Bash(uuidgen:*)",
        ]
    }
}


def detect_mode() -> str:
    """Auto-detect mode from CLAUDE_CONTAINER_MODE environment variable."""
    val = os.environ.get("CLAUDE_CONTAINER_MODE", "").lower()
    return "container" if val in ("1", "true") else "baseline"


def settings_path() -> Path:
    """Return ~/.claude/settings.local.json path."""
    return Path.home() / ".claude" / "settings.local.json"


def write_settings(data: dict, path: Path) -> None:
    """Write settings JSON to path, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ~/.claude/settings.local.json"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--container", action="store_true", help="Force container permissions"
    )
    group.add_argument(
        "--baseline", action="store_true", help="Force baseline permissions"
    )
    group.add_argument(
        "--check", action="store_true", help="Print detected mode, don't write"
    )
    args = parser.parse_args()

    if args.container:
        mode = "container"
    elif args.baseline:
        mode = "baseline"
    else:
        mode = detect_mode()

    if args.check:
        print(f"Mode: {mode}")
        print(f"Target: {settings_path()}")
        return

    data = CONTAINER_PERMISSIONS if mode == "container" else BASELINE_PERMISSIONS
    target = settings_path()
    write_settings(data, target)
    print(f"Wrote {mode} permissions to {target}")


if __name__ == "__main__":
    main()
