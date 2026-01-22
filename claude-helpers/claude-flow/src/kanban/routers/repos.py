"""Repository management endpoints."""

import contextlib
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from kanban.database import RepoDB, TaskDB, get_db
from kanban.models import RepoCreate
from kanban.utils import utc_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repos", tags=["repos"])


class RepoWithCount(BaseModel):
    """Repository with task count."""

    id: UUID
    repo_id: str
    name: str | None
    active: bool
    task_count: int
    created_at: datetime
    updated_at: datetime
    # Template tracking fields
    template_status: str
    template_version: str | None
    template_installed_at: datetime | None
    # Recent projects tracking
    last_accessed_at: datetime | None


def get_repo_name_from_path(repo_path: str) -> str | None:
    """Extract repository name from git remote or directory name.

    Args:
        repo_path: Absolute path to the repository

    Returns:
        Repository name or None if unable to determine
    """
    repo_name = None

    # Try to get repo name from git remote origin URL
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=repo_path,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract repo name from URL (handles both HTTPS and SSH)
            # e.g., https://github.com/user/repo.git -> repo
            # e.g., git@github.com:user/repo.git -> repo
            if url:
                repo_name = url.rstrip("/").rstrip(".git").split("/")[-1].split(":")[-1]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fall back to directory name if no git remote
    if not repo_name:
        with contextlib.suppress(Exception):
            repo_name = Path(repo_path).name

    return repo_name


@router.get("", response_model=list[RepoWithCount])
def list_repos(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """Get all registered repositories with task counts.

    Args:
        active_only: If True, only return active repos (default)
        db: Database session

    Returns:
        List of repos with their task counts
    """
    # Subquery to count tasks per repo
    task_counts = (
        db.query(TaskDB.repo_id, func.count(TaskDB.id).label("task_count"))
        .group_by(TaskDB.repo_id)
        .subquery()
    )

    # Main query joining repos with task counts
    query = db.query(
        RepoDB, func.coalesce(task_counts.c.task_count, 0).label("task_count")
    ).outerjoin(task_counts, RepoDB.repo_id == task_counts.c.repo_id)

    if active_only:
        query = query.filter(RepoDB.active == True)  # noqa: E712

    results = query.order_by(RepoDB.name, RepoDB.repo_id).all()

    return [
        RepoWithCount(
            id=UUID(repo.id),
            repo_id=repo.repo_id,
            name=repo.name,
            active=repo.active,
            task_count=task_count,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            template_status=repo.template_status or "not_installed",
            template_version=repo.template_version,
            template_installed_at=repo.template_installed_at,
            last_accessed_at=repo.last_accessed_at,
        )
        for repo, task_count in results
    ]


@router.post("", response_model=RepoWithCount, status_code=201)
def register_repo(
    repo: RepoCreate,
    auto_install: bool = Query(
        default=True,
        description="Automatically install template after registration",
    ),
    db: Session = Depends(get_db),
):
    """Register a new repository.

    Validates that the path exists and is a git repository.
    If the repo already exists but is inactive, reactivates it.
    Optionally triggers template installation (default: enabled).

    Args:
        repo: Repository to register
        auto_install: If True, trigger template installation (default: True)
        db: Database session

    Returns:
        The registered repository with task count
    """
    # Normalize the path
    repo_path = Path(repo.repo_id).resolve()

    # Validate path exists
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {repo_path}")

    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {repo_path}")

    # Check if it's a git repository
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a git repository (no .git directory): {repo_path}",
        )

    repo_id_str = str(repo_path)

    # Check if repo already exists
    existing = db.query(RepoDB).filter(RepoDB.repo_id == repo_id_str).first()
    if existing:
        if existing.active:
            raise HTTPException(status_code=409, detail="Repository already registered")
        # Reactivate inactive repo
        existing.active = True
        existing.updated_at = utc_now()
        if repo.name:
            existing.name = repo.name

        # Optionally reinstall template on reactivation if not already installed
        if auto_install and existing.template_status not in ("installed", "installing"):
            from kanban.routers.install import trigger_install

            trigger_install(repo_id_str)
            existing.template_status = "installing"

        db.commit()
        db.refresh(existing)

        # Count tasks
        task_count = db.query(TaskDB).filter(TaskDB.repo_id == repo_id_str).count()

        return RepoWithCount(
            id=UUID(existing.id),
            repo_id=existing.repo_id,
            name=existing.name,
            active=existing.active,
            task_count=task_count,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
            template_status=existing.template_status or "not_installed",
            template_version=existing.template_version,
            template_installed_at=existing.template_installed_at,
            last_accessed_at=existing.last_accessed_at,
        )

    # Extract name from git remote if not provided
    name = repo.name or get_repo_name_from_path(repo_id_str)

    # Create new repo
    db_repo = RepoDB(
        repo_id=repo_id_str,
        name=name,
        active=True,
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)

    logger.info(f"Registered repository: {repo_id_str} ({name})")

    # Auto-install template if enabled
    if auto_install:
        from kanban.routers.install import trigger_install

        trigger_install(repo_id_str)
        db_repo.template_status = "installing"
        db.commit()
        db.refresh(db_repo)

    return RepoWithCount(
        id=UUID(db_repo.id),
        repo_id=db_repo.repo_id,
        name=db_repo.name,
        active=db_repo.active,
        task_count=0,  # New repo has no tasks
        created_at=db_repo.created_at,
        updated_at=db_repo.updated_at,
        template_status=db_repo.template_status or "not_installed",
        template_version=db_repo.template_version,
        template_installed_at=db_repo.template_installed_at,
        last_accessed_at=db_repo.last_accessed_at,
    )


@router.delete("/{repo_id:path}")
def deactivate_repo(repo_id: str, db: Session = Depends(get_db)):
    """Deactivate a repository (soft delete).

    Tasks are preserved in the database for history.
    The repo can be reactivated by registering it again.

    Args:
        repo_id: Repository path to deactivate
        db: Database session

    Returns:
        Status message
    """
    db_repo = db.query(RepoDB).filter(RepoDB.repo_id == repo_id).first()
    if not db_repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    db_repo.active = False
    db_repo.updated_at = utc_now()
    db.commit()

    logger.info(f"Deactivated repository: {repo_id}")

    return {"status": "deactivated", "repo_id": repo_id}


class CurrentRepoResponse(BaseModel):
    """Response for current repo endpoint."""

    repo_id: str | None
    name: str | None
    is_valid_git_repo: bool
    source: str  # "cwd", "last_used", or "none"


LAST_USED_REPO_KEY = "last_used_repo"


def _is_git_repo(path: str) -> bool:
    """Check if path is a git repository."""
    return (Path(path) / ".git").exists()


def _get_last_used_repo(db: Session) -> str | None:
    """Get last used repo from settings."""
    from kanban.database import SettingDB

    setting = db.query(SettingDB).filter(SettingDB.key == LAST_USED_REPO_KEY).first()
    return setting.value if setting else None


def _set_last_used_repo(db: Session, repo_id: str) -> None:
    """Save last used repo to settings."""
    from kanban.database import SettingDB

    setting = db.query(SettingDB).filter(SettingDB.key == LAST_USED_REPO_KEY).first()
    if setting:
        setting.value = repo_id
        setting.updated_at = utc_now()
    else:
        setting = SettingDB(key=LAST_USED_REPO_KEY, value=repo_id)
        db.add(setting)
    db.commit()


@router.get("/current", response_model=CurrentRepoResponse)
def get_current_repo(db: Session = Depends(get_db)):
    """Get information about the current repository context.

    Priority:
    1. If CWD is a valid git repo, use that
    2. Otherwise, fall back to last_used_repo from settings
    3. If neither, return empty response

    Returns:
        Current repo info with source indicator
    """
    from kanban.main import PROJECT_ROOT

    cwd_path = str(PROJECT_ROOT)

    # Check if CWD is a valid git repo
    if _is_git_repo(cwd_path):
        return CurrentRepoResponse(
            repo_id=cwd_path,
            name=get_repo_name_from_path(cwd_path),
            is_valid_git_repo=True,
            source="cwd",
        )

    # Fall back to last used repo
    last_used = _get_last_used_repo(db)
    if last_used and Path(last_used).exists() and _is_git_repo(last_used):
        return CurrentRepoResponse(
            repo_id=last_used,
            name=get_repo_name_from_path(last_used),
            is_valid_git_repo=True,
            source="last_used",
        )

    # No valid repo found
    return CurrentRepoResponse(
        repo_id=None,
        name=None,
        is_valid_git_repo=False,
        source="none",
    )


@router.post("/current")
def set_current_repo(
    repo_id: str = Query(..., description="Repository path to set as current"),
    db: Session = Depends(get_db),
):
    """Set the current repository context (persisted as last_used_repo).

    This is called when the user selects a repo from the UI.
    The selection is remembered for future sessions.

    Args:
        repo_id: Repository path to set as current

    Returns:
        Confirmation with repo info
    """
    # Validate the repo exists and is a git repo
    if not Path(repo_id).exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {repo_id}")

    if not _is_git_repo(repo_id):
        raise HTTPException(status_code=400, detail=f"Not a git repository: {repo_id}")

    # Save to settings
    _set_last_used_repo(db, repo_id)

    # Update last_accessed_at for this repo
    db_repo = db.query(RepoDB).filter(RepoDB.repo_id == repo_id).first()
    if db_repo:
        db_repo.last_accessed_at = utc_now()
        db.commit()

    logger.info(f"Set current repo to: {repo_id}")

    return {
        "status": "ok",
        "repo_id": repo_id,
        "name": get_repo_name_from_path(repo_id),
    }


class ValidateRepoResponse(BaseModel):
    """Response for repo validation."""

    is_valid: bool
    has_launch_script: bool
    launch_script_path: str | None
    error: str | None


@router.get("/{repo_id:path}/validate", response_model=ValidateRepoResponse)
def validate_repo(repo_id: str):
    """Validate if a repo has the required claude-helpers installed.

    Checks for the existence of the launch-claude-tab.sh script.

    Args:
        repo_id: Repository path to validate

    Returns:
        Validation status with details
    """
    from kanban.routers.iterm import get_launch_script_path

    repo_path = Path(repo_id)

    # Check if repo path exists
    if not repo_path.exists():
        return ValidateRepoResponse(
            is_valid=False,
            has_launch_script=False,
            launch_script_path=None,
            error=f"Repository path does not exist: {repo_id}",
        )

    # Check for launch script
    launch_script = get_launch_script_path(repo_id)
    has_script = launch_script.exists()

    if not has_script:
        return ValidateRepoResponse(
            is_valid=False,
            has_launch_script=False,
            launch_script_path=str(launch_script),
            error=f"Launch script not found at {launch_script}. Run installation to set up claude-helpers in this repository.",
        )

    return ValidateRepoResponse(
        is_valid=True,
        has_launch_script=True,
        launch_script_path=str(launch_script),
        error=None,
    )
