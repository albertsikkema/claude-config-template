"""Load and convert settings.json deny patterns to regex for hook enforcement.

In --dangerously-skip-permissions mode, the built-in permission system is
bypassed, but the hook still enforces deny patterns loaded from settings.json.
This ensures a single source of truth for deny rules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def load_deny_patterns(project_dir: str) -> dict[str, list[re.Pattern]]:
    """
    Read settings.json deny list, return {tool_name: [compiled_regex]}.

    Converts glob patterns like Bash(curl * | sh) to regex.
    Falls back to empty dict if settings.json is missing or malformed.
    """
    patterns: dict[str, list[re.Pattern]] = {
        "Bash": [], "Read": [], "Edit": [], "Write": [],
        "Glob": [], "Grep": [], "MultiEdit": [],
    }

    settings_path = Path(project_dir) / ".claude" / "settings.json"
    if not settings_path.exists():
        return patterns

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return patterns

    deny_list = settings.get("permissions", {}).get("deny", [])

    for entry in deny_list:
        # Parse "ToolName(pattern)" format
        match = re.match(r'^(\w+)\((.+)\)$', entry)
        if not match:
            continue
        tool_name, glob_pattern = match.groups()
        if tool_name not in patterns:
            continue

        # Convert glob to regex:
        # 1. Escape special chars, then replace escaped \* with .*
        regex_str = re.escape(glob_pattern).replace(r'\*', '.*')
        # 2. Make trailing ' .*' optional so "cmd *" matches both "cmd" and "cmd arg"
        if regex_str.endswith(r'\ .*'):
            regex_str = regex_str[:-4] + r'(\ .*)?'
        # 3. Replace escaped spaces adjacent to .* with \s* for flexible matching
        #    This handles patterns like "* DROP TABLE *" where the content may be
        #    wrapped in quotes, parentheses, etc.
        regex_str = regex_str.replace(r'.*\ ', r'.*\s*')
        regex_str = regex_str.replace(r'\ .*', r'\s*.*')
        try:
            compiled = re.compile(regex_str, re.IGNORECASE)
            patterns[tool_name].append(compiled)
        except re.error:
            continue

    return patterns
