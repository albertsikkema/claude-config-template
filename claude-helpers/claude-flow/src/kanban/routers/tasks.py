"""Task management endpoints."""

import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kanban.database import TaskDB, get_db
from kanban.models import (
    STAGES,
    ClaudeStatus,
    Stage,
    StageInfo,
    Task,
    TaskCreate,
    TaskMove,
    TaskUpdate,
)

logger = logging.getLogger(__name__)

# Project root is now dynamic - passed via repo_id
# This is used for reading document files relative to repo

router = APIRouter(prefix="/api", tags=["tasks"])


def task_db_to_model(db_task: TaskDB) -> Task:
    """Convert database model to Pydantic model."""
    return Task(
        id=UUID(db_task.id),
        repo_id=db_task.repo_id,
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
        claude_status=db_task.claude_status,
        started_at=db_task.started_at,
        claude_completed_at=db_task.claude_completed_at,
        approved_at=db_task.approved_at,
        session_id=db_task.session_id,
    )


@router.get("/stages", response_model=list[StageInfo])
def get_stages():
    """Get all workflow stage definitions."""
    return STAGES


@router.get("/tasks", response_model=list[Task])
def get_tasks(
    repo_id: str | None = Query(None, description="Filter tasks by repository path"),
    db: Session = Depends(get_db),
):
    """Get tasks, optionally filtered by repo_id."""
    query = db.query(TaskDB)
    if repo_id:
        query = query.filter(TaskDB.repo_id == repo_id)
    tasks = query.order_by(TaskDB.stage, TaskDB.order, TaskDB.created_at).all()
    return [task_db_to_model(t) for t in tasks]


@router.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    db_task = TaskDB(
        repo_id=task.repo_id,
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


class MoveTaskResponse(BaseModel):
    """Response for move task with session start indicator."""

    task: Task
    can_start_session: bool
    completed: bool = False
    cleaned_files: list[str] = []


@router.patch("/tasks/{task_id}/move", response_model=MoveTaskResponse)
def move_task(task_id: UUID, move: TaskMove, db: Session = Depends(get_db)):
    """Move a task to a different stage.

    Returns the task and whether this stage supports starting a Claude session.
    When moving to DONE, cleans up ephemeral files (plan, research).
    """
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_task.stage = move.stage
    db_task.order = move.order
    db_task.updated_at = datetime.utcnow()

    # If moving to next stage from ready_for_review, auto-approve
    if db_task.claude_status == ClaudeStatus.READY_FOR_REVIEW:
        db_task.claude_status = ClaudeStatus.APPROVED
        db_task.approved_at = datetime.utcnow()

    # Track cleanup for done stage
    cleaned_files: list[str] = []
    completed = False

    # If moving to DONE, clean up ephemeral files
    if move.stage == Stage.DONE:
        completed = True
        # Use the task's repo_id as the project root
        project_root = Path(db_task.repo_id)
        ephemeral_paths = [db_task.plan_path, db_task.research_path, db_task.review_path]
        for rel_path in ephemeral_paths:
            if rel_path:
                full_path = project_root / rel_path
                if full_path.exists():
                    try:
                        full_path.unlink()
                        cleaned_files.append(rel_path)
                    except OSError:
                        pass  # Ignore deletion errors
        # Clear all artifact paths and session from the task
        db_task.plan_path = None
        db_task.research_path = None
        db_task.review_path = None
        db_task.session_id = None
        db_task.claude_status = None

    db.commit()
    db.refresh(db_task)

    # Return indicator if this stage supports session start
    action_stages = {
        Stage.RESEARCH,
        Stage.PLANNING,
        Stage.IMPLEMENTATION,
        Stage.REVIEW,
        Stage.CLEANUP,
        Stage.COMMIT,
    }
    can_start_session = move.stage in action_stages

    return MoveTaskResponse(
        task=task_db_to_model(db_task),
        can_start_session=can_start_session,
        completed=completed,
        cleaned_files=cleaned_files,
    )


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

    # Use the task's repo_id as the project root
    project_root = Path(db_task.repo_id)
    full_path = project_root / doc_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")

    content = full_path.read_text(encoding="utf-8")
    return DocumentResponse(content=content, path=doc_path)


@router.post("/tasks/{task_id}/approve", response_model=Task)
def approve_task(task_id: UUID, db: Session = Depends(get_db)):
    """Approve a task that is ready for review.

    Transitions task from ready_for_review to approved.
    """
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.claude_status != ClaudeStatus.READY_FOR_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve task with status: {db_task.claude_status}",
        )

    db_task.claude_status = ClaudeStatus.APPROVED
    db_task.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)

    return task_db_to_model(db_task)


def get_prompt_for_stage(stage: Stage, task: TaskDB) -> str:
    """Get the prompt for a stage.

    Returns a prompt with the appropriate slash command and artifact path.
    Task context is only included for stages that need it (research, review).
    """
    # Build task context
    context = f"Task: {task.title}"
    if task.description:
        context += f"\n\nDescription: {task.description}"

    if stage == Stage.RESEARCH:
        return f"/research_codebase {context}"
    elif stage == Stage.PLANNING:
        # Planning should use research document, not task context
        if task.research_path:
            return f"/create_plan {task.research_path}"
        # Fallback if no research doc
        return f"/create_plan {context}"
    elif stage == Stage.IMPLEMENTATION:
        if not task.plan_path:
            raise ValueError("Cannot start implementation without a plan")
        return f"/implement_plan {task.plan_path}"
    elif stage == Stage.REVIEW:
        if not task.plan_path:
            raise ValueError("Cannot start review without a plan")
        return f"/code_reviewer {task.plan_path}"
    elif stage == Stage.CLEANUP:
        if task.plan_path:
            # Include research and review paths if available
            paths = [task.plan_path]
            if task.research_path:
                paths.append(task.research_path)
            if task.review_path:
                paths.append(task.review_path)
            return f"/cleanup {' '.join(paths)}"
        return f"/cleanup\n\n{context}"
    elif stage == Stage.COMMIT:
        # Include plan path for commit context
        if task.plan_path:
            return f"/commit {task.plan_path}"
        return "/commit"
    else:
        return context


class StartSessionResponse(BaseModel):
    """Response from starting a Claude session."""

    status: str
    session_id: str


@router.post("/tasks/{task_id}/start-session", response_model=StartSessionResponse)
async def start_task_session(task_id: UUID, db: Session = Depends(get_db)):
    """Start a new Claude session for a task.

    Opens an iTerm tab and updates task status to running.
    """
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get appropriate prompt based on stage
    try:
        prompt = get_prompt_for_stage(db_task.stage, db_task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Determine model - some stages require sonnet regardless of task preference
    from kanban.models import ClaudeModel

    if db_task.stage in (Stage.REVIEW, Stage.CLEANUP, Stage.COMMIT):
        model = ClaudeModel.SONNET
    else:
        model = db_task.model

    # Open iTerm tab
    from kanban.routers.iterm import OpenTabRequest, open_claude_tab

    response = await open_claude_tab(
        OpenTabRequest(
            task_id=str(task_id),
            task_title=db_task.title,
            prompt=prompt,
            stage=db_task.stage.value,
            model=model.value,
            repo_id=db_task.repo_id,
        )
    )

    # Update task
    db_task.claude_status = ClaudeStatus.RUNNING
    db_task.started_at = datetime.utcnow()
    db_task.session_id = response.session_id
    db.commit()

    return StartSessionResponse(status="started", session_id=response.session_id)


@router.post("/tasks/{task_id}/resume", response_model=StartSessionResponse)
async def resume_task_session(task_id: UUID, db: Session = Depends(get_db)):
    """Resume an existing Claude session.

    Opens iTerm tab with `claude --resume <session_id>`.
    """
    db_task = db.query(TaskDB).filter(TaskDB.id == str(task_id)).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not db_task.session_id:
        raise HTTPException(status_code=400, detail="No session to resume")

    # Open iTerm tab with resume command
    from kanban.routers.iterm import OpenTabRequest, open_claude_tab

    await open_claude_tab(
        OpenTabRequest(
            task_id=str(task_id),
            task_title=db_task.title,
            stage=db_task.stage.value,
            model=db_task.model.value,
            resume_session_id=db_task.session_id,
            repo_id=db_task.repo_id,
        )
    )

    # Update status
    db_task.claude_status = ClaudeStatus.RUNNING
    db_task.started_at = datetime.utcnow()
    db.commit()

    return StartSessionResponse(status="resumed", session_id=db_task.session_id)


class ImproveRequest(BaseModel):
    """Request body for improving task content."""

    title: str
    description: str | None = None


class ImproveResponse(BaseModel):
    """Response with improved task content."""

    title: str
    description: str
    tags: list[str]


@router.post("/tasks/improve", response_model=ImproveResponse)
async def improve_content_endpoint(request: ImproveRequest):
    """Improve task title, description, and generate tags using AI (without saving).

    Calls OpenAI to generate improved title, description, and relevant tags based on
    project context. Use this for previewing improvements before creating a task.

    Returns max 4 tags, sanitized to lowercase hyphenated format.
    """
    from kanban.ai import AIServiceError, OpenAIKeyNotConfiguredError, improve_task_content

    try:
        improved = await improve_task_content(request.title, request.description)
        return ImproveResponse(
            title=improved.title, description=improved.description, tags=improved.tags
        )
    except OpenAIKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "api_key_not_configured", "message": str(e)},
        ) from e
    except AIServiceError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_service_unavailable", "message": str(e)},
        ) from e


@router.post("/tasks/{task_id}/improve", response_model=Task)
async def improve_task_endpoint(task_id: UUID, db: Session = Depends(get_db)):
    """Improve task title, description, and generate tags using AI.

    Calls OpenAI to generate improved title, description, and relevant tags based on
    project context (CLAUDE.md and indexed codebase).

    Note: This endpoint modifies and persists the task immediately. Use POST /tasks/improve
    for preview without saving. Returns max 4 tags, sanitized to lowercase hyphenated format.
    """
    from kanban.ai import AIServiceError, OpenAIKeyNotConfiguredError, improve_task_content

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
        ) from e
    except AIServiceError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_service_unavailable", "message": str(e)},
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in improve_task_endpoint")
        raise HTTPException(
            status_code=500,
            detail={"error": "unexpected_error", "message": str(e)},
        ) from e

    # Update task with improved values
    db_task.title = improved.title
    db_task.description = improved.description
    db_task.tags = improved.tags
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)

    return task_db_to_model(db_task)
