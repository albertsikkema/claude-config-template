"""Security check management endpoints."""

import asyncio
import os
import shutil
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Find claude executable (same pattern as docs.py)
CLAUDE_PATH = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")

# Security report file naming constants
SECURITY_REPORT_PREFIX = "security-analysis-"
SECURITY_REPORT_SUFFIX = ".md"
SECURITY_REPORT_PATTERN = f"{SECURITY_REPORT_PREFIX}*{SECURITY_REPORT_SUFFIX}"

# Subprocess timeout (30 minutes max for comprehensive security analysis)
SECURITY_CHECK_TIMEOUT_SECONDS = 1800

router = APIRouter(prefix="/api/security", tags=["security"])


class SecurityCheckRequest(BaseModel):
    """Request to start a security check."""

    repo_id: str


class SecurityCheckResponse(BaseModel):
    """Response when starting a security check."""

    status: str
    message: str


class SecurityReport(BaseModel):
    """Metadata for a security report file."""

    filename: str
    path: str
    created_at: str  # ISO timestamp
    size_bytes: int


async def _run_claude_security(repo_path: Path) -> None:
    """Run the /security slash command using Claude Code.

    This is fire-and-forget - we just spawn the command and let it run.
    The report will be saved to thoughts/shared/reviews/security-analysis-*.md.

    Args:
        repo_path: Path to the repository to analyze
    """
    thread_id = threading.get_ident()

    # Read /security command from the target repo
    cmd_path = repo_path / ".claude" / "commands" / "security.md"
    if cmd_path.exists():
        content = cmd_path.read_text()
        # Strip YAML frontmatter if present
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                content = content[end_idx + 3 :].lstrip()
        cmd_content = content
    else:
        raise RuntimeError(f"Security command not found. Expected file: {cmd_path}")

    prompt = cmd_content  # Use command as-is

    try:
        # Ensure HOME env var is set for claude to find its config
        env = os.environ.copy()
        env["HOME"] = str(Path.home())

        # Build args for non-interactive execution
        args = [
            CLAUDE_PATH,
            "--dangerously-skip-permissions",
            "--verbose",
            "--model",
            "sonnet",  # Use sonnet for comprehensive security analysis
            "-p",
            prompt,
        ]

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(repo_path),
            env=env,
        )

        # Wait for completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=SECURITY_CHECK_TIMEOUT_SECONDS,
            )

            if process.returncode == 0:
                print(f"[Thread {thread_id}] Security analysis completed successfully")
            else:
                print(
                    f"[Thread {thread_id}] Security analysis exited with code {process.returncode}"
                )
                if stderr:
                    print(f"[Thread {thread_id}] stderr: {stderr.decode()[:500]}")

        except TimeoutError:
            process.kill()
            await process.wait()
            print(
                f"[Thread {thread_id}] Security analysis timed out after "
                f"{SECURITY_CHECK_TIMEOUT_SECONDS // 60} minutes"
            )

    except Exception as e:
        print(f"[Thread {thread_id}] Error running security analysis: {e}")


def _run_security_in_thread(repo_path: Path) -> None:
    """Run the async security check in a new event loop within the thread.

    Args:
        repo_path: Path to the repository to analyze
    """
    thread_id = threading.get_ident()
    print(f"[Thread {thread_id}] Starting background security analysis thread for {repo_path}")

    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_claude_security(repo_path))
        finally:
            loop.close()
    except Exception as e:
        print(f"[Thread {thread_id}] Error in security analysis thread: {e}")


@router.post("/check", response_model=SecurityCheckResponse)
def trigger_security_check(request: SecurityCheckRequest):
    """Start a new security analysis (fire-and-forget).

    This endpoint spawns Claude Code in a background thread to run the /security
    command and returns immediately. The security report will be saved to
    thoughts/shared/reviews/security-analysis-YYYY-MM-DD.md.

    Users should check the /api/security/checks endpoint to see completed reports.

    Args:
        request: SecurityCheckRequest with repo_id path

    Returns:
        SecurityCheckResponse with status 'started' and message
    """
    repo_path = Path(request.repo_id)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail=f"Repository path not found: {request.repo_id}")

    # Check that target directory exists
    reviews_dir = repo_path / "thoughts" / "shared" / "reviews"
    if not reviews_dir.exists():
        reviews_dir.mkdir(parents=True, exist_ok=True)

    # Spawn daemon thread to run Claude Code
    thread = threading.Thread(target=_run_security_in_thread, args=(repo_path,), daemon=True)
    thread.start()

    return SecurityCheckResponse(
        status="started",
        message="Security analysis started. Report will appear in thoughts/shared/reviews/",
    )


@router.get("/checks", response_model=list[SecurityReport])
def list_security_reports(repo_id: str = Query(..., description="Repository path")):
    """List all security analysis reports from the filesystem.

    Scans thoughts/shared/reviews/ for security-analysis-*.md files
    and returns metadata for each report (most recent first).

    Args:
        repo_id: Repository path to list reports for

    Returns:
        List of SecurityReport objects with file metadata
    """
    repo_path = Path(repo_id)
    reviews_dir = repo_path / "thoughts" / "shared" / "reviews"

    if not reviews_dir.exists():
        return []

    # Find all security-analysis-*.md files
    security_files = list(reviews_dir.glob(SECURITY_REPORT_PATTERN))

    # Sort by modified time (most recent first)
    security_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Build response
    reports = []
    for file_path in security_files:
        stat = file_path.stat()
        reports.append(
            SecurityReport(
                filename=file_path.name,
                path=str(file_path.relative_to(repo_path)),
                created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                size_bytes=stat.st_size,
            )
        )

    return reports


@router.get("/report/{filename}")
def get_security_report(filename: str, repo_id: str = Query(..., description="Repository path")):
    """Get the content of a specific security report.

    Args:
        filename: Name of the report file (e.g., security-analysis-2026-01-09.md)
        repo_id: Repository path

    Returns:
        dict with 'content' and 'path' keys

    Raises:
        HTTPException 404: Report file not found
        HTTPException 400: Invalid filename (path traversal attempt)
    """
    # Security: Validate filename to prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Security: Only allow security-analysis-*.md files
    if not filename.startswith(SECURITY_REPORT_PREFIX) or not filename.endswith(
        SECURITY_REPORT_SUFFIX
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename format. Expected {SECURITY_REPORT_PATTERN}",
        )

    repo_path = Path(repo_id)
    reviews_dir = repo_path / "thoughts" / "shared" / "reviews"
    report_path = reviews_dir / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    content = report_path.read_text()
    return {
        "content": content,
        "path": str(report_path.relative_to(repo_path)),
    }
