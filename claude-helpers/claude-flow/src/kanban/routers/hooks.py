"""Endpoints for Claude Code hooks."""

import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kanban.database import RepoDB, SessionLocal, TaskDB
from kanban.models import ClaudeStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hooks", tags=["hooks"])


def ensure_repo_registered(db, repo_id: str) -> None:
    """Ensure a repo is registered when hooks are called.

    This auto-registers repos when they first interact with the API via hooks.
    """
    if not repo_id:
        return

    existing = db.query(RepoDB).filter(RepoDB.repo_id == repo_id).first()
    if not existing:
        # Auto-register the repo
        from kanban.routers.repos import get_repo_name_from_path

        name = get_repo_name_from_path(repo_id)
        db_repo = RepoDB(repo_id=repo_id, name=name, active=True)
        db.add(db_repo)
        db.commit()
        logger.info(f"Auto-registered repository from hook: {repo_id}")


class SessionEndRequest(BaseModel):
    """Request from Claude Stop hook."""

    session_id: str = Field(..., min_length=1, max_length=100)
    exit_code: int = Field(default=0)
    repo_id: str | None = Field(default=None, max_length=500)


class ArtifactCreatedRequest(BaseModel):
    """Request from Claude Write hook."""

    file_path: str = Field(..., min_length=1, max_length=500)
    task_id: str | None = Field(default=None, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    repo_id: str | None = Field(default=None, max_length=500)


class StopRequest(BaseModel):
    """Request from Claude Stop hook (end of turn)."""

    task_id: str | None = Field(default=None, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    repo_id: str | None = Field(default=None, max_length=500)


@router.post("/session-end")
async def handle_session_end(request: SessionEndRequest):
    """Handle Claude Stop hook - update task status.

    Called when a Claude session ends (user exits or Claude completes).
    Updates task status to ready_for_review (success) or failed (error).
    """
    db = SessionLocal()
    try:
        # Auto-register repo if provided
        if request.repo_id:
            ensure_repo_registered(db, request.repo_id)

        # Find task by session_id (optionally filtered by repo_id for extra safety)
        query = db.query(TaskDB).filter(TaskDB.session_id == request.session_id)
        if request.repo_id:
            query = query.filter(TaskDB.repo_id == request.repo_id)
        task = query.first()

        if not task:
            logger.warning(f"No task found for session_id: {request.session_id}")
            return {"status": "not_found", "session_id": request.session_id}

        # Update status based on exit code
        if request.exit_code == 0:
            task.claude_status = ClaudeStatus.READY_FOR_REVIEW
        else:
            task.claude_status = ClaudeStatus.FAILED

        task.claude_completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Session ended for task {task.id}: exit_code={request.exit_code}, "
            f"status={task.claude_status}"
        )

        return {
            "status": "updated",
            "task_id": task.id,
            "task_title": task.title,
            "claude_status": task.claude_status.value,
        }
    finally:
        db.close()


@router.post("/artifact-created")
async def handle_artifact_created(request: ArtifactCreatedRequest):
    """Handle artifact file creation.

    Called when Claude writes to thoughts/shared/ directories.
    Updates task with artifact path and sets status to ready_for_review.
    Accepts either task_id (preferred) or session_id for task lookup.
    """
    db = SessionLocal()
    try:
        # Auto-register repo if provided
        repo_id = request.repo_id if request.repo_id else None
        if repo_id:
            ensure_repo_registered(db, repo_id)

        # Normalize empty strings to None
        task_id = request.task_id if request.task_id else None
        session_id = request.session_id if request.session_id else None

        # Find task by task_id (preferred) or session_id
        task = None
        if task_id:
            query = db.query(TaskDB).filter(TaskDB.id == task_id)
            if repo_id:
                query = query.filter(TaskDB.repo_id == repo_id)
            task = query.first()
        if not task and session_id:
            query = db.query(TaskDB).filter(TaskDB.session_id == session_id)
            if repo_id:
                query = query.filter(TaskDB.repo_id == repo_id)
            task = query.first()

        if not task:
            logger.warning(
                f"artifact-created: no task found (task_id={request.task_id}, session_id={request.session_id})"
            )
            return {"status": "not_found"}

        # Determine artifact type from path
        path = request.file_path
        artifact_type = None
        if "research" in path:
            task.research_path = path
            artifact_type = "research"
        elif "plans" in path:
            task.plan_path = path
            artifact_type = "plan"
        elif "reviews" in path:
            task.review_path = path
            artifact_type = "review"

        # Set status to ready_for_review when artifact is written
        if artifact_type:
            task.claude_status = ClaudeStatus.READY_FOR_REVIEW
            task.claude_completed_at = datetime.utcnow()
            logger.info(f"Task {task.id} artifact created: {artifact_type} -> ready_for_review")

        db.commit()

        return {
            "status": "updated",
            "task_id": task.id,
            "path": path,
            "artifact_type": artifact_type,
        }
    finally:
        db.close()


@router.post("/stop")
async def handle_stop(request: StopRequest):
    """Handle Claude Stop hook (end of turn).

    Called at the end of each Claude turn. If the task is still marked as
    'running', this acts as a fallback to mark it ready_for_review.
    Accepts either task_id (preferred) or session_id for task lookup.
    """
    db = SessionLocal()
    try:
        # Auto-register repo if provided
        repo_id = request.repo_id if request.repo_id else None
        if repo_id:
            ensure_repo_registered(db, repo_id)

        # Normalize empty strings to None
        task_id = request.task_id if request.task_id else None
        session_id = request.session_id if request.session_id else None

        # Find task by task_id (preferred) or session_id
        task = None
        if task_id:
            query = db.query(TaskDB).filter(TaskDB.id == task_id)
            if repo_id:
                query = query.filter(TaskDB.repo_id == repo_id)
            task = query.first()
        if not task and session_id:
            query = db.query(TaskDB).filter(TaskDB.session_id == session_id)
            if repo_id:
                query = query.filter(TaskDB.repo_id == repo_id)
            task = query.first()

        if not task:
            return {"status": "not_found"}

        # Only update if still running (don't overwrite artifact-created status)
        if task.claude_status == ClaudeStatus.RUNNING:
            task.claude_status = ClaudeStatus.READY_FOR_REVIEW
            task.claude_completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Task {task.id} stop hook -> ready_for_review")
            return {"status": "updated", "task_id": task.id}

        return {
            "status": "no_change",
            "task_id": task.id,
            "current_status": task.claude_status.value,
        }
    finally:
        db.close()
