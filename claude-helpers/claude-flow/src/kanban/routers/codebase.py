"""Codebase operations endpoints (indexing)."""

import asyncio
import logging
import os
import shutil
import threading
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Find claude executable (same pattern as docs.py)
CLAUDE_PATH = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")

router = APIRouter(prefix="/api/codebase", tags=["codebase"])
logger = logging.getLogger(__name__)


class IndexCodebaseRequest(BaseModel):
    """Request to index a codebase."""

    repo_id: str = Field(..., description="Repository path")


class IndexCodebaseResponse(BaseModel):
    """Response from codebase indexing request."""

    status: str = Field(..., description="Status of the request (e.g., 'started')")
    message: str = Field(..., description="Human-readable message describing the result")


async def _run_claude_index(repo_path: Path) -> None:
    """Run Claude Code with /index_codebase command asynchronously.

    Args:
        repo_path: Path to the repository to index
    """
    thread_id = threading.get_ident()

    # Read the slash command from the repo
    cmd_path = repo_path / ".claude" / "commands" / "index_codebase.md"
    if cmd_path.exists():
        content = cmd_path.read_text()
        # Strip YAML frontmatter if present
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                content = content[end_idx + 3 :].lstrip()
        cmd_content = content
    else:
        logger.error(f"[Thread {thread_id}] Could not read index_codebase command from {cmd_path}")
        return

    # Use command as-is (no context injection needed - command is self-contained)
    prompt = cmd_content

    logger.info(f"[Thread {thread_id}] Starting Claude Code for codebase indexing")

    try:
        # Ensure HOME env var is set for claude to find its config
        env = os.environ.copy()
        env["HOME"] = str(Path.home())

        # Build args for non-interactive execution (same pattern as docs.py)
        args = [
            CLAUDE_PATH,
            "--dangerously-skip-permissions",
            "--verbose",
            "--model",
            "haiku",  # Use haiku for fast indexing task
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


def _run_index_in_thread(repo_path: Path) -> None:
    """Run the async indexing in a new event loop within the thread.

    Args:
        repo_path: Path to the repository to index
    """
    thread_id = threading.get_ident()
    logger.info(f"[Thread {thread_id}] Starting background indexing thread for {repo_path}")

    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_claude_index(repo_path))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[Thread {thread_id}] Error in indexing thread: {e}", exc_info=True)


@router.post("/index", response_model=IndexCodebaseResponse)
def index_codebase(request: IndexCodebaseRequest):
    """Index the codebase using Claude Code.

    This is a fire-and-forget endpoint. It spawns Claude Code in a background
    thread to index the codebase and returns immediately.
    Users should check the thoughts/codebase/ directory for generated overview files.

    The endpoint uses the /index_codebase slash command which:
    - Auto-detects project type (Python, JavaScript/TypeScript, Go)
    - Calls appropriate indexer script (index_python.py, index_js_ts.py, index_go.py)
    - Generates overview files with complete file tree, classes, functions, and call relationships
    - Saves results to thoughts/codebase/codebase_overview_*.md

    Args:
        request: IndexCodebaseRequest with repo_id

    Returns:
        IndexCodebaseResponse with status 'started' and message

    Example:
        POST /api/codebase/index
        {
            "repo_id": "/Users/user/myrepo"
        }

        Response:
        {
            "status": "started",
            "message": "Codebase indexing started in background. Files will be generated in thoughts/codebase/"
        }
    """
    repo_path = Path(request.repo_id)

    # Check that target directory exists
    codebase_dir = repo_path / "thoughts" / "codebase"
    if not codebase_dir.exists():
        logger.info(f"Creating codebase directory: {codebase_dir}")
        codebase_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Received codebase indexing request for {repo_path}")

    # Spawn daemon thread to run Claude Code
    thread = threading.Thread(target=_run_index_in_thread, args=(repo_path,), daemon=True)
    thread.start()

    return IndexCodebaseResponse(
        status="started",
        message="Codebase indexing started in background. "
        "Files will be generated in thoughts/codebase/",
    )
