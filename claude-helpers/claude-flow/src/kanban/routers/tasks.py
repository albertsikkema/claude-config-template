"""Task management endpoints."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kanban.database import TaskDB, get_db
from kanban.jobs import trigger_stage_command
from kanban.models import (
    STAGES,
    JobStatus,
    Stage,
    StageInfo,
    Task,
    TaskCreate,
    TaskMove,
    TaskUpdate,
)

# Project root for reading document files
# tasks.py -> routers -> kanban -> src -> claude-flow -> claude-helpers -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

router = APIRouter(prefix="/api", tags=["tasks"])


def task_db_to_model(db_task: TaskDB) -> Task:
    """Convert database model to Pydantic model."""
    return Task(
        id=UUID(db_task.id),
        title=db_task.title,
        description=db_task.description,
        stage=db_task.stage,
        priority=db_task.priority,
        tags=db_task.tags,
        ticket_id=db_task.ticket_id,
        order=db_task.order,
        model=db_task.model,
        complexity=db_task.complexity,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at,
        research_path=db_task.research_path,
        plan_path=db_task.plan_path,
        review_path=db_task.review_path,
        job_status=db_task.job_status,
        job_output=db_task.job_output,
        job_error=db_task.job_error,
        job_started_at=db_task.job_started_at,
        job_completed_at=db_task.job_completed_at,
        session_id=db_task.session_id,
    )


@router.get("/stages", response_model=list[StageInfo])
def get_stages():
    """Get all workflow stage definitions."""
    return STAGES


@router.get("/tasks", response_model=list[Task])
def get_tasks(db: Session = Depends(get_db)):
    """Get all tasks."""
    tasks = db.query(TaskDB).order_by(TaskDB.stage, TaskDB.order, TaskDB.created_at).all()
    return [task_db_to_model(t) for t in tasks]


@router.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    db_task = TaskDB(
        title=task.title,
        description=task.description,
        stage=task.stage,
        priority=task.priority,
        ticket_id=task.ticket_id,
        order=task.order,
        model=task.model,
        complexity=task.complexity,
    )
    db_task.tags = task.tags
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return task_db_to_model(db_task)


@router.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: UUID, db: Session = Depends(get_db)):
    """Get a single task by ID."""
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_db_to_model(db_task)


@router.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: UUID, task: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task."""
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task.model_dump(exclude_unset=True)
    if "tags" in update_data:
        db_task.tags = update_data.pop("tags")

    for field, value in update_data.items():
        setattr(db_task, field, value)

    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return task_db_to_model(db_task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    """Delete a task."""
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()


@router.patch("/tasks/{task_id}/move", response_model=Task)
def move_task(task_id: UUID, move: TaskMove, db: Session = Depends(get_db)):
    """Move a task to a different stage.

    If moving to a stage with an associated Claude Code command,
    the command will be triggered automatically in the background.
    """
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_stage = db_task.stage
    new_stage = move.stage

    db_task.stage = new_stage
    db_task.order = move.order
    db_task.updated_at = datetime.utcnow()
    db.commit()

    # Trigger background command if moving forward to a stage with a command
    if old_stage != new_stage:
        trigger_stage_command(str(task_id), old_stage, new_stage, db)

    db.refresh(db_task)
    return task_db_to_model(db_task)


class DocumentResponse(BaseModel):
    """Response for document content."""

    content: str
    path: str


@router.get("/tasks/{task_id}/document", response_model=DocumentResponse)
def get_task_document(task_id: UUID, db: Session = Depends(get_db)):
    """Get the research, plan, or review document content for a task."""
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Prefer review_path > plan_path > research_path (most recent workflow stage first)
    doc_path = db_task.review_path or db_task.plan_path or db_task.research_path
    if not doc_path:
        raise HTTPException(status_code=404, detail="No document available for this task")

    full_path = PROJECT_ROOT / doc_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")

    content = full_path.read_text(encoding="utf-8")
    return DocumentResponse(content=content, path=doc_path)


class OutputResponse(BaseModel):
    """Response for job output."""

    job_status: str | None
    job_output: str | None
    job_error: str | None


@router.get("/tasks/{task_id}/output", response_model=OutputResponse)
def get_task_output(task_id: UUID, db: Session = Depends(get_db)):
    """Get the current job output for a task (for real-time streaming)."""
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    return OutputResponse(
        job_status=db_task.job_status.value if db_task.job_status else None,
        job_output=db_task.job_output,
        job_error=db_task.job_error,
    )


@router.post("/tasks/{task_id}/restart", response_model=Task)
def restart_task(task_id: UUID, db: Session = Depends(get_db)):
    """Restart a failed or cancelled task's job.

    Resets job fields and re-triggers the stage command.
    """
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only allow restart if job failed or was cancelled
    if db_task.job_status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Can only restart failed or cancelled jobs. Current status: {db_task.job_status}",
        )

    # Reset job fields
    db_task.job_status = JobStatus.PENDING
    db_task.job_output = None
    db_task.job_error = None
    db_task.job_started_at = None
    db_task.job_completed_at = None
    db_task.updated_at = datetime.utcnow()

    # Capture stage before commit (to avoid SQLAlchemy expiry issues)
    current_stage = db_task.stage

    db.commit()

    # Re-trigger the stage command (from BACKLOG to current stage)
    trigger_stage_command(str(task_id), Stage.BACKLOG, current_stage, db)

    db.refresh(db_task)
    return task_db_to_model(db_task)


@router.post("/tasks/{task_id}/cancel", response_model=Task)
def cancel_task(task_id: UUID, db: Session = Depends(get_db)):
    """Cancel a running or pending task's job.

    Terminates the Claude Code process if running.
    """
    from kanban.jobs import cancel_running_job

    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only allow cancel if job is running or pending
    if db_task.job_status not in (JobStatus.RUNNING, JobStatus.PENDING):
        raise HTTPException(
            status_code=400,
            detail=f"Can only cancel running or pending jobs. Current status: {db_task.job_status}",
        )

    # Try to cancel the running job
    cancelled = cancel_running_job(str(task_id))

    if not cancelled:
        # Job may be pending (not yet started) - just update status
        db_task.job_status = JobStatus.CANCELLED
        db_task.job_error = "Job cancelled by user"
        db_task.job_completed_at = datetime.utcnow()
        db_task.updated_at = datetime.utcnow()
        db.commit()

    db.refresh(db_task)
    return task_db_to_model(db_task)


class ImproveRequest(BaseModel):
    """Request body for improving task content."""

    title: str
    description: str | None = None


class ImproveResponse(BaseModel):
    """Response with improved task content."""

    title: str
    description: str


@router.post("/tasks/improve", response_model=ImproveResponse)
async def improve_content_endpoint(request: ImproveRequest):
    """Improve task title and description using AI (without saving).

    Calls OpenAI to generate improved title and description based on
    project context. Use this for previewing improvements before creating a task.
    """
    from kanban.ai import OpenAIKeyNotConfiguredError, improve_task_content

    try:
        improved = await improve_task_content(request.title, request.description)
        return ImproveResponse(title=improved.title, description=improved.description)
    except OpenAIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "api_key_not_configured", "message": str(e)},
        )


@router.post("/tasks/{task_id}/improve", response_model=Task)
async def improve_task_endpoint(task_id: UUID, db: Session = Depends(get_db)):
    """Improve task title and description using AI.

    Calls OpenAI to generate improved title and description based on
    project context (CLAUDE.md and indexed codebase).
    """
    from kanban.ai import OpenAIKeyNotConfiguredError, improve_task_content

    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Call AI to improve
        improved = await improve_task_content(db_task.title, db_task.description)
    except OpenAIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "api_key_not_configured", "message": str(e)},
        )

    # Update task with improved values
    db_task.title = improved.title
    db_task.description = improved.description
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)

    return task_db_to_model(db_task)
