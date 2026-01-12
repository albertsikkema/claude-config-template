"""Documentation management endpoints."""

import asyncio
import logging
import os
import shutil
import threading
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from kanban.utils import read_slash_command

# Find claude executable (same pattern as jobs.py)
CLAUDE_PATH = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")

router = APIRouter(prefix="/api", tags=["docs"])
logger = logging.getLogger(__name__)


class FetchDocsRequest(BaseModel):
    """Request to fetch technical documentation."""

    packages: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of package names to fetch documentation for",
    )
    repo_id: str = Field(..., description="Repository path")

    @field_validator("packages")
    @classmethod
    def validate_packages(cls, v: list[str]) -> list[str]:
        """Validate package names are non-empty and properly formatted."""
        if not v:
            raise ValueError("Packages list cannot be empty")

        cleaned = []
        for pkg in v:
            pkg_clean = pkg.strip()
            if not pkg_clean:
                raise ValueError("Package names cannot be empty or whitespace")

            # Allow alphanumeric, hyphens, underscores, @, and / (for scoped packages)
            if not all(c.isalnum() or c in "-_@/." for c in pkg_clean):
                raise ValueError(
                    f"Package name '{pkg_clean}' contains invalid characters. "
                    "Only alphanumeric, hyphens, underscores, @, /, and . are allowed."
                )

            # Prevent path traversal patterns (defense-in-depth)
            if ".." in pkg_clean or pkg_clean.startswith("/") or pkg_clean.endswith("/"):
                raise ValueError(
                    f"Package name '{pkg_clean}' contains suspicious path patterns. "
                    "Leading/trailing slashes and '..' are not allowed."
                )

            cleaned.append(pkg_clean)

        return cleaned


class FetchDocsResponse(BaseModel):
    """Response from documentation fetch request."""

    status: str = Field(..., description="Status of the request (e.g., 'started', 'error')")
    message: str = Field(..., description="Human-readable message describing the result")


async def _run_claude_fetch(packages: list[str], repo_path: Path) -> None:
    """Run Claude Code with /fetch_technical_docs command asynchronously.

    Args:
        packages: List of package names to fetch
        repo_path: Path to the repository
    """
    thread_id = threading.get_ident()

    # Read the slash command from the repo
    cmd_path = repo_path / ".claude" / "commands" / "fetch_technical_docs.md"
    if cmd_path.exists():
        content = cmd_path.read_text()
        # Strip YAML frontmatter if present
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                content = content[end_idx + 3:].lstrip()
        cmd_content = content
    else:
        logger.error(f"[Thread {thread_id}] Could not read fetch_technical_docs command from {cmd_path}")
        return

    # Build prompt with specific packages to fetch
    packages_list = "\n".join(f"- {pkg}" for pkg in packages)
    prompt = f"""{cmd_content}

## Packages to Fetch

The user has requested documentation for these specific packages:

{packages_list}

**Important**: Skip the discover step. Only search and fetch documentation for the packages listed above.
For each package:
1. Search Context7 for the package
2. Select the best result (prefer VIP, high trust score, high stars)
3. Fetch the documentation
4. Report success or failure

Begin fetching documentation now.
"""

    logger.info(f"[Thread {thread_id}] Starting Claude Code for {len(packages)} packages")

    try:
        # Ensure HOME env var is set for claude to find its config
        env = os.environ.copy()
        env["HOME"] = str(Path.home())

        # Build args for non-interactive execution (same pattern as jobs.py)
        args = [
            CLAUDE_PATH,
            "--dangerously-skip-permissions",
            "--verbose",
            "--model",
            "haiku",  # Use haiku for fast, simple task
            "-p",
            prompt,
            "--output-format",
            "stream-json",
        ]

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(repo_path),
            env=env,
        )

        # Wait for completion (fire-and-forget, but log output)
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"[Thread {thread_id}] Claude Code completed successfully")
        else:
            logger.warning(
                f"[Thread {thread_id}] Claude Code exited with code {process.returncode}"
            )
            if stderr:
                logger.warning(f"[Thread {thread_id}] stderr: {stderr.decode()[:500]}")

    except Exception as e:
        logger.error(f"[Thread {thread_id}] Error running Claude Code: {e}", exc_info=True)


def _run_fetch_in_thread(packages: list[str], repo_path: Path) -> None:
    """Run the async fetch in a new event loop within the thread.

    Args:
        packages: List of package names to fetch
        repo_path: Path to the repository
    """
    thread_id = threading.get_ident()
    logger.info(f"[Thread {thread_id}] Starting background fetch thread for {repo_path}")

    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_claude_fetch(packages, repo_path))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[Thread {thread_id}] Error in fetch thread: {e}", exc_info=True)


@router.post("/docs/fetch", response_model=FetchDocsResponse)
def fetch_technical_docs(request: FetchDocsRequest):
    """Fetch technical documentation from Context7 using Claude Code.

    This is a fire-and-forget endpoint. It spawns Claude Code in a background
    thread to intelligently fetch documentation and returns immediately.
    Users should check the thoughts/technical_docs/ directory for downloaded files.

    The endpoint uses the /fetch_technical_docs slash command which:
    - Searches Context7 for each package
    - Intelligently selects the best result (VIP, trust score, stars)
    - Fetches and saves documentation to thoughts/technical_docs/

    Args:
        request: FetchDocsRequest with list of package names and repo_id

    Returns:
        FetchDocsResponse with status 'started' and message

    Raises:
        HTTPException 422: Invalid request (caught by Pydantic validation)
    """
    repo_path = Path(request.repo_id)

    # Check that target directory exists
    docs_dir = repo_path / "thoughts" / "technical_docs"
    if not docs_dir.exists():
        logger.info(f"Creating documentation directory: {docs_dir}")
        docs_dir.mkdir(parents=True, exist_ok=True)

    package_count = len(request.packages)
    logger.info(f"Received fetch request for {package_count} package(s): {request.packages}")

    # Spawn daemon thread to run Claude Code
    thread = threading.Thread(target=_run_fetch_in_thread, args=(request.packages, repo_path), daemon=True)
    thread.start()

    return FetchDocsResponse(
        status="started",
        message=f"Fetching documentation for {package_count} package(s) using Claude Code. "
        f"Files will appear in thoughts/technical_docs/",
    )
