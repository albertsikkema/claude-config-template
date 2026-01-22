"""Shared utility functions for the kanban package."""

from datetime import UTC, datetime
from pathlib import Path


def utc_now() -> datetime:
    """Return the current UTC datetime as timezone-aware.

    This replaces datetime.utcnow() which is deprecated in Python 3.12+
    and produces timezone-naive datetimes that cause serialization issues.

    Returns:
        Timezone-aware UTC datetime that serializes with timezone info
        (e.g., "2026-01-22T10:30:00+00:00" instead of "2026-01-22T10:30:00")
    """
    return datetime.now(UTC)


# Project root path (utils.py -> kanban -> src -> claude-flow -> claude-helpers -> PROJECT_ROOT)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def read_slash_command(command_name: str) -> str | None:
    """Read a slash command file from .claude/commands/.

    Strips YAML frontmatter (---...---) from the content.
    Returns the command content or None if not found.

    Args:
        command_name: Name of the command (without .md extension)

    Returns:
        Command content with frontmatter stripped, or None if not found
    """
    cmd_path = PROJECT_ROOT / ".claude" / "commands" / f"{command_name}.md"
    if cmd_path.exists():
        content = cmd_path.read_text()
        # Strip YAML frontmatter if present
        if content.startswith("---"):
            # Find the closing ---
            end_idx = content.find("---", 3)
            if end_idx != -1:
                content = content[end_idx + 3 :].lstrip()
        return content
    return None
