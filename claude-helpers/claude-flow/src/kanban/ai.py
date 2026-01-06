"""AI-powered task improvement using OpenAI via PydanticAI."""

import os
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent


class OpenAIKeyNotConfiguredError(Exception):
    """Raised when OPENAI_API_KEY is not set."""

    pass

# Project root for reading context files
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class ImprovedTask(BaseModel):
    """Structured response for improved task."""

    title: str
    description: str
    tags: list[str]


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
6. Generate 3-5 relevant tags based on the task content

Tags should categorize the task by:
- Type (feature, bugfix, refactor, docs, test, chore, security, performance)
- Technology/component (frontend, backend, api, database, ui, cli, etc.)
- Domain/area (authentication, deployment, monitoring, etc.)
- Priority indicators if applicable (urgent, breaking-change)

Use lowercase, hyphenated tags (e.g., "bug-fix", "api-endpoint", "user-auth").
""",
        output_type=ImprovedTask,
    )

    # Build the prompt
    prompt = f"""Improve this task:

Title: {title}
Description: {description or "(no description)"}

Return an improved version with:
1. Better clarity and proper technical terminology
2. 3-5 relevant tags that categorize the task appropriately"""

    result = await agent.run(prompt)
    return result.output
