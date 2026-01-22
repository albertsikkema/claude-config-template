"""Template installation endpoints."""

import asyncio
import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kanban.database import RepoDB, SessionLocal, get_db
from kanban.utils import utc_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/install", tags=["install"])

# GitHub repository for template
TEMPLATE_REPO = "https://github.com/albertsikkema/claude-config-template"
TEMPLATE_BRANCH = "main"

# Installation timeout (10 minutes)
INSTALL_TIMEOUT_SECONDS = 600


class InstallResponse(BaseModel):
    """Response when starting an installation."""

    status: str
    message: str


class InstallStatusResponse(BaseModel):
    """Response for installation status check."""

    repo_id: str
    template_status: str
    template_version: str | None
    template_installed_at: datetime | None


class LatestVersionResponse(BaseModel):
    """Response containing latest available template version (git commit hash)."""

    version: str | None
    source: str  # "git" or "unavailable"


def _update_repo_status(
    repo_id: str,
    status: str,
    version: str | None = None,
) -> None:
    """Update repo template status in database.

    Args:
        repo_id: Repository path
        status: New status (installing, installed, failed)
        version: Template version if installed
    """
    db = SessionLocal()
    try:
        repo = db.query(RepoDB).filter(RepoDB.repo_id == repo_id).first()
        if repo:
            repo.template_status = status
            if version:
                repo.template_version = version
            if status == "installed":
                repo.template_installed_at = utc_now()
            repo.updated_at = utc_now()
            db.commit()
            logger.info(f"Updated repo {repo_id} template_status to {status}")
    finally:
        db.close()


def _read_installed_version(repo_path: str) -> str | None:
    """Read VERSION file from installed template.

    Args:
        repo_path: Repository path

    Returns:
        Version string or None if not found
    """
    version_file = Path(repo_path) / ".claude" / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return None


def _get_source_version() -> str | None:
    """Get git commit hash from the template source repository.

    Returns:
        Short git hash or None if unavailable
    """
    from kanban.main import CLAUDE_FLOW_DIR

    # Go from claude-helpers/claude-flow -> repo root
    repo_root = CLAUDE_FLOW_DIR.parent.parent

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _write_version_file(repo_path: str, version: str) -> None:
    """Write VERSION file to installed template.

    Args:
        repo_path: Repository path
        version: Version string to write
    """
    version_file = Path(repo_path) / ".claude" / "VERSION"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(version + "\n")


async def _run_install(repo_path: str, force_thoughts: bool = False) -> None:
    """Run template installation for a repo.

    Downloads from GitHub and installs:
    - .claude/ (always overwrite - agents, commands, settings, VERSION)
    - thoughts/ (rsync --ignore-existing, unless force_thoughts=True)
    - claude-helpers/ scripts (index_python.py, orchestrator.py, etc.)
    - Skips claude-helpers/claude-flow/ (app runs centrally)
    - Skips .env.claude (API keys in central DB)

    Args:
        repo_path: Absolute path to repository
        force_thoughts: If True, overwrite thoughts/ content
    """
    thread_id = threading.get_ident()
    logger.info(f"[Thread {thread_id}] Starting installation for {repo_path}")

    # Update status to installing
    _update_repo_status(repo_path, "installing")

    try:
        env = os.environ.copy()
        env["HOME"] = str(Path.home())

        # Build install URL
        install_url = f"{TEMPLATE_REPO}/raw/{TEMPLATE_BRANCH}/install.sh"

        # Build curl command with flags
        flags = "--global-app"
        if force_thoughts:
            flags += " --force"

        # Use curl to download and execute install.sh from GitHub
        cmd = f'curl -fsSL "{install_url}" | bash -s -- {flags} "{repo_path}"'
        logger.info(f"[Thread {thread_id}] Running: {cmd}")

        process = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=INSTALL_TIMEOUT_SECONDS,
            )

            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""

            if process.returncode == 0:
                # Get version from source repo and write to target
                # (install script can't get git hash when downloaded from GitHub)
                version = _get_source_version()
                if version:
                    _write_version_file(repo_path, version)
                    logger.info(f"[Thread {thread_id}] Wrote VERSION file: {version}")
                else:
                    # Fallback to reading whatever was installed
                    version = _read_installed_version(repo_path)
                _update_repo_status(repo_path, "installed", version)
                logger.info(f"[Thread {thread_id}] Installation completed for {repo_path}")
                if stdout_text:
                    logger.debug(f"[Thread {thread_id}] stdout: {stdout_text[:1000]}")
            else:
                _update_repo_status(repo_path, "failed")
                logger.error(
                    f"[Thread {thread_id}] Installation failed for {repo_path} "
                    f"(exit code {process.returncode})"
                )
                if stderr_text:
                    logger.error(f"[Thread {thread_id}] stderr: {stderr_text[:500]}")
                if stdout_text:
                    logger.error(f"[Thread {thread_id}] stdout: {stdout_text[:500]}")

        except TimeoutError:
            process.kill()
            await process.wait()
            _update_repo_status(repo_path, "failed")
            logger.error(
                f"[Thread {thread_id}] Installation timed out for {repo_path} "
                f"after {INSTALL_TIMEOUT_SECONDS // 60} minutes"
            )

    except Exception as e:
        _update_repo_status(repo_path, "failed")
        logger.error(f"[Thread {thread_id}] Error installing template: {e}", exc_info=True)


def _run_install_in_thread(repo_path: str, force_thoughts: bool = False) -> None:
    """Run installation in background thread.

    Args:
        repo_path: Repository path
        force_thoughts: If True, overwrite thoughts/ content
    """
    thread_id = threading.get_ident()
    logger.info(f"[Thread {thread_id}] Starting background installation thread")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_install(repo_path, force_thoughts))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[Thread {thread_id}] Error in installation thread: {e}")


def trigger_install(repo_path: str, force_thoughts: bool = False) -> None:
    """Trigger template installation in background thread.

    This is the main entry point for triggering installations.

    Args:
        repo_path: Absolute path to repository
        force_thoughts: If True, overwrite thoughts/ content
    """
    thread = threading.Thread(
        target=_run_install_in_thread,
        args=(repo_path, force_thoughts),
        daemon=True,
    )
    thread.start()


# Static routes must come before path-parameter routes
@router.get("/latest-version", response_model=LatestVersionResponse)
def get_latest_version():
    """Get the latest available template version (git commit hash).

    Reads the git commit hash from the template source repository.

    Returns:
        LatestVersionResponse with version hash and source
    """
    version = _get_source_version()
    if version:
        return LatestVersionResponse(version=version, source="git")
    return LatestVersionResponse(version=None, source="unavailable")


@router.post("/{repo_path:path}", response_model=InstallResponse)
def install_template(
    repo_path: str,
    force_thoughts: bool = Query(
        default=False,
        description="If True, overwrite thoughts/ content (default: preserve)",
    ),
    db: Session = Depends(get_db),
):
    """Install or update template for a repository (fire-and-forget).

    Installs .claude/, thoughts/ structure, and claude-helpers/ scripts.
    Does NOT install claude-flow (runs centrally) or .env.claude (central DB).

    Args:
        repo_path: Absolute path to repository
        force_thoughts: If True, overwrite thoughts/ (default: preserve content)

    Returns:
        InstallResponse with status 'started'
    """
    path = Path(repo_path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid repository path: {repo_path}")

    # Check repo is registered
    repo = db.query(RepoDB).filter(RepoDB.repo_id == repo_path).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not registered")

    # Don't start if already installing
    if repo.template_status == "installing":
        return InstallResponse(
            status="already_running",
            message=f"Installation already in progress for {repo_path}",
        )

    trigger_install(repo_path, force_thoughts)

    return InstallResponse(
        status="started",
        message=f"Template installation started for {repo_path}",
    )


@router.get("/{repo_path:path}/status", response_model=InstallStatusResponse)
def get_install_status(repo_path: str, db: Session = Depends(get_db)):
    """Get template installation status for a repository.

    Args:
        repo_path: Absolute path to repository

    Returns:
        InstallStatusResponse with current status
    """
    repo = db.query(RepoDB).filter(RepoDB.repo_id == repo_path).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not registered")

    return InstallStatusResponse(
        repo_id=repo.repo_id,
        template_status=repo.template_status or "not_installed",
        template_version=repo.template_version,
        template_installed_at=repo.template_installed_at,
    )
