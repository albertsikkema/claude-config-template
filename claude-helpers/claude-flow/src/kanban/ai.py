"""AI-powered task improvement using OpenAI via PydanticAI.

Tag Taxonomy
------------
Tags are automatically generated to categorize tasks. The following categories are used:

**Type Tags** (what kind of work):
    - feature: New functionality
    - bugfix: Bug fixes
    - refactor: Code restructuring without behavior change
    - docs: Documentation changes
    - test: Test additions or modifications
    - chore: Maintenance tasks (dependencies, configs)
    - security: Security-related changes
    - performance: Performance improvements

**Component Tags** (where the work is):
    - frontend: UI/client-side code
    - backend: Server-side code
    - api: API endpoints or contracts
    - database: Database schemas or queries
    - ui: User interface components
    - cli: Command-line interface

**Domain Tags** (what area it affects):
    - authentication, deployment, monitoring, etc.

**Priority Tags** (urgency indicators):
    - urgent: High priority work
    - breaking-change: Requires careful rollout

All tags are lowercase and hyphenated (e.g., "bug-fix", "api-endpoint").
Maximum of 4 tags per task.
"""

import logging
import re
import os
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_ai import Agent

logger = logging.getLogger(__name__)

# Constants for tag validation
MAX_TAGS = 4
MAX_TAG_LENGTH = 50


class OpenAIKeyNotConfiguredError(Exception):
    """Raised when OPENAI_API_KEY is not set."""

    pass


class AIServiceError(Exception):
    """Raised when the AI service fails (rate limits, API errors, etc.)."""

    pass


# Project root for reading context files
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def sanitize_tags(tags: list[str]) -> list[str]:
    """Sanitize and validate tags from AI output.

    Ensures tags are:
    - Lowercase
    - Hyphenated (no spaces or special chars except hyphens)
    - Unique (no duplicates)
    - Limited to MAX_TAGS (4)
    - Each tag max MAX_TAG_LENGTH (50) characters

    Args:
        tags: Raw tags from AI

    Returns:
        Sanitized list of tags
    """
    sanitized = []
    seen: set[str] = set()

    for tag in tags[:MAX_TAGS + 2]:  # Allow some extra to filter from
        if len(sanitized) >= MAX_TAGS:
            break

        # Convert to lowercase and strip whitespace
        clean = tag.lower().strip()

        # Replace spaces with hyphens, remove special chars except hyphens
        clean = re.sub(r"\s+", "-", clean)
        clean = re.sub(r"[^a-z0-9\-]", "", clean)

        # Remove multiple consecutive hyphens
        clean = re.sub(r"-+", "-", clean)

        # Strip leading/trailing hyphens
        clean = clean.strip("-")

        if clean and clean not in seen and len(clean) <= MAX_TAG_LENGTH:
            sanitized.append(clean)
            seen.add(clean)

    return sanitized


class ImprovedTask(BaseModel):
    """Structured response for improved task.

    Attributes:
        title: Improved task title (max 100 chars, actionable)
        description: Improved task description (max 500 chars, informative)
        tags: List of categorization tags (max 4, lowercase, hyphenated)
    """

    title: str
    description: str
    tags: list[str]

    @field_validator("tags", mode="after")
    @classmethod
    def validate_and_sanitize_tags(cls, v: list[str]) -> list[str]:
        """Validate and sanitize tags after parsing."""
        return sanitize_tags(v)


def get_context() -> str:
    """Read CLAUDE.md and indexed codebase files for context.

    gpt-4o-mini has 128K token context (~500K chars), so we can be generous.
    We limit total context to ~100K chars to leave room for prompt/response.
    """
    context_parts = []
    total_chars = 0
    max_total_chars = 100_000  # Leave room for system prompt and response

    # Read CLAUDE.md (full content, typically ~20K chars)
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()
        total_chars += len(content)
        context_parts.append(f"# Project Context (CLAUDE.md)\n\n{content}")

    # Read indexed codebase files (up to 30K chars each, stop if total exceeds limit)
    codebase_dir = PROJECT_ROOT / "thoughts" / "codebase"
    if codebase_dir.exists():
        for file in sorted(codebase_dir.glob("*.md")):
            if file.name.startswith("."):
                continue
            if total_chars >= max_total_chars:
                break
            content = file.read_text()
            # Truncate individual file if very large
            if len(content) > 30_000:
                content = content[:30_000] + "\n... (truncated)"
            total_chars += len(content)
            context_parts.append(f"# Codebase Overview ({file.name})\n\n{content}")

    return "\n\n---\n\n".join(context_parts) if context_parts else "No context available."


async def improve_task_content(title: str, description: str | None) -> ImprovedTask:
    """Improve task title, description, and generate tags using OpenAI.

    Args:
        title: Current task title
        description: Current task description (may be None)

    Returns:
        ImprovedTask with improved title, description, and auto-generated tags

    Raises:
        OpenAIKeyNotConfiguredError: If OPENAI_API_KEY is not set
    """
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        raise OpenAIKeyNotConfiguredError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it to your .env file to use AI features."
        )

    # Get project context
    context = get_context()

    # Create agent with OpenAI
    agent = Agent(
        "openai:gpt-4o-mini",
        system_prompt=f"""You are helping improve task titles, descriptions, and generate relevant tags for a Kanban board.

Use the following project context to understand terminology and conventions:

{context}

When improving tasks:
1. Use correct technical terminology from the codebase
2. Make the title specific and actionable (under 100 characters)
3. Make the description informative with relevant details (under 500 characters)
4. Reference relevant files, modules, or patterns if applicable
5. Keep the original intent but make it clearer
6. Generate 2-4 relevant tags based on the task content (maximum 4 tags)

Tags should categorize the task by:
- Type (feature, bugfix, refactor, docs, test, chore, security, performance)
- Technology/component (frontend, backend, api, database, ui, cli, etc.)
- Domain/area (authentication, deployment, monitoring, etc.)
- Priority indicators if applicable (urgent, breaking-change)

Use lowercase, hyphenated tags (e.g., "bug-fix", "api-endpoint", "user-auth").
IMPORTANT: Return no more than 4 tags.
""",
        output_type=ImprovedTask,
    )

    # Build the prompt
    prompt = f"""Improve this task:

Title: {title}
Description: {description or "(no description)"}

Return an improved version with:
1. Better clarity and proper technical terminology
2. 2-4 relevant tags that categorize the task (maximum 4 tags)"""

    try:
        result = await agent.run(prompt)
        return result.output
    except Exception as e:
        # Log the error for debugging
        logger.error(f"AI service error during task improvement: {e}")
        raise AIServiceError(f"Failed to improve task: {e}") from e
