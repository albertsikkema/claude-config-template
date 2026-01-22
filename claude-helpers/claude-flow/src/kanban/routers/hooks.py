"""Endpoints for Claude Code hooks."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kanban.database import RepoDB, SessionLocal, TaskDB
from kanban.models import ClaudeStatus, Stage
from kanban.utils import utc_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hooks", tags=["hooks"])

# Auto-advance configuration: defines which stages can auto-advance and to where
# This is designed to be easily extensible for future transitions
AUTO_ADVANCE_TRANSITIONS: dict[Stage, Stage] = {
    Stage.RESEARCH: Stage.PLANNING,
    Stage.IMPLEMENTATION: Stage.REVIEW,
    # Future: add more transitions here as needed
}


def get_auto_advance_target(current_stage: Stage) -> tuple[Stage, Stage] | None:
    """Get the auto-advance transition for the current stage.

    Args:
        current_stage: The current workflow stage

    Returns:
        Tuple of (from_stage, to_stage) if auto-advance is configured for this stage,
        None otherwise
    """
    if current_stage in AUTO_ADVANCE_TRANSITIONS:
        return (current_stage, AUTO_ADVANCE_TRANSITIONS[current_stage])
    return None


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


async def auto_start_session(task_id: str, repo_id: str) -> None:
    """Automatically start a new Claude session for a task after auto-advance.

    This function runs in the background to start the next workflow stage session.
    It uses a small delay to ensure the database commit is complete before starting.

    Args:
        task_id: The task ID (as string) to start a session for
        repo_id: The repository ID for the task
    """
    # Small delay to ensure DB commit is complete
    await asyncio.sleep(0.5)

    try:
        # Import here to avoid circular imports
        from kanban.routers.tasks import _start_session_for_task_internal

        db = SessionLocal()
        try:
            await _start_session_for_task_internal(UUID(task_id), db)
            logger.info(f"Auto-started session for task {task_id} after auto-advance")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Auto-start session failed for task {task_id}: {e}")


def check_and_perform_auto_advance(task: TaskDB, db, now: datetime) -> tuple[bool, Stage | None]:
    """Check if auto-advance should occur and perform it if enabled.

    Auto-advance is controlled by the task's auto_advance field.
    When enabled, the task will automatically move to the next stage without manual approval.

    Args:
        task: The task database object
        db: Database session
        now: Current timestamp

    Returns:
        Tuple of (auto_advanced, new_stage) - whether auto-advance occurred and the new stage
    """
    logger.info(
        f"check_and_perform_auto_advance: task.id={task.id}, task.stage={task.stage}, "
        f"task.auto_advance={task.auto_advance}"
    )

    # Check if auto-advance is enabled for this specific task
    if not task.auto_advance:
        logger.info(f"Task {task.id} has auto_advance=False, skipping")
        return (False, None)

    auto_advance_info = get_auto_advance_target(task.stage)
    logger.info(f"auto_advance_info for stage {task.stage}: {auto_advance_info}")

    if not auto_advance_info:
        return (False, None)

    from_stage, next_stage = auto_advance_info

    # Auto-approve and move to next stage
    task.claude_status = ClaudeStatus.APPROVED
    task.approved_at = now
    task.stage = next_stage
    db.commit()

    logger.info(f"Task {task.id} auto-advanced from {from_stage.value} to {next_stage.value}")

    # Start new session in background
    asyncio.create_task(auto_start_session(str(task.id), task.repo_id))

    return (True, next_stage)


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
    If auto-advance is enabled for this stage, automatically moves to next stage.
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
        now = utc_now()
        auto_advanced = False
        new_stage = None

        if request.exit_code == 0:
            task.claude_status = ClaudeStatus.READY_FOR_REVIEW
            task.claude_completed_at = now
            task.last_notification = now
            db.commit()

            # Check for auto-advance (only on successful completion)
            auto_advanced, new_stage = check_and_perform_auto_advance(task, db, now)
        else:
            task.claude_status = ClaudeStatus.FAILED
            task.claude_completed_at = now
            task.last_notification = now
            db.commit()

        logger.info(
            f"Session ended for task {task.id}: exit_code={request.exit_code}, "
            f"status={task.claude_status}, auto_advanced={auto_advanced}"
        )

        response = {
            "status": "updated",
            "task_id": task.id,
            "task_title": task.title,
            "claude_status": task.claude_status.value,
            "auto_advanced": auto_advanced,
        }
        if new_stage:
            response["new_stage"] = new_stage.value

        return response
    finally:
        db.close()


@router.post("/artifact-created")
async def handle_artifact_created(request: ArtifactCreatedRequest):
    """Handle artifact file creation.

    Called when Claude writes to thoughts/shared/ directories.
    Updates task with artifact path and sets status to ready_for_review.
    If auto-advance is enabled for this stage, automatically moves to next stage.
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

        auto_advanced = False
        new_stage = None

        # Set status to ready_for_review when artifact is written
        if artifact_type:
            now = utc_now()
            task.claude_status = ClaudeStatus.READY_FOR_REVIEW
            task.claude_completed_at = now
            task.last_notification = now
            db.commit()

            logger.info(f"Task {task.id} artifact created: {artifact_type} -> ready_for_review")

            # Check for auto-advance (only for certain artifacts that complete a stage)
            # Research artifact completes research stage, plan artifact completes planning
            auto_advanced, new_stage = check_and_perform_auto_advance(task, db, now)
        else:
            db.commit()

        response = {
            "status": "updated",
            "task_id": task.id,
            "path": path,
            "artifact_type": artifact_type,
            "auto_advanced": auto_advanced,
        }
        if new_stage:
            response["new_stage"] = new_stage.value

        return response
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
        # NOTE: The stop hook fires on every turn, including when Claude asks a question.
        # Auto-advance here is aggressive - it will trigger even on questions.
        # Users who enable auto-advance accept this behavior.
        if task.claude_status == ClaudeStatus.RUNNING:
            now = utc_now()
            task.claude_status = ClaudeStatus.READY_FOR_REVIEW
            task.claude_completed_at = now
            task.last_notification = now
            db.commit()
            logger.info(f"Task {task.id} stop hook -> ready_for_review")

            # Check for auto-advance - only if setting is explicitly enabled
            # Note: This is aggressive and will trigger even on question turns
            auto_advanced, new_stage = check_and_perform_auto_advance(task, db, now)

            response = {
                "status": "updated",
                "task_id": task.id,
                "auto_advanced": auto_advanced,
            }
            if new_stage:
                response["new_stage"] = new_stage.value
            return response

        return {
            "status": "no_change",
            "task_id": task.id,
            "current_status": task.claude_status.value,
        }
    finally:
        db.close()
