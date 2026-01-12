"""Pydantic models for the Kanban API."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Stage(str, Enum):
    """Workflow stages matching Claude Code commands."""

    BACKLOG = "backlog"
    RESEARCH = "research"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    CLEANUP = "cleanup"
    COMMIT = "commit"
    DONE = "done"


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaudeStatus(str, Enum):
    """Claude session status for interactive terminals."""

    RUNNING = "running"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClaudeModel(str, Enum):
    """Available Claude models."""

    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"


class WorkflowComplexity(str, Enum):
    """Workflow complexity levels."""

    SIMPLE = "simple"
    COMPLETE = "complete"


class StageInfo(BaseModel):
    """Stage metadata."""

    id: Stage
    name: str
    color: str
    command: str | None = None
    description: str


class TaskBase(BaseModel):
    """Base task properties."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    stage: Stage = Stage.BACKLOG
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    ticket_id: str | None = Field(default=None, max_length=50)
    order: int = 0
    model: ClaudeModel = ClaudeModel.SONNET  # Default to sonnet
    complexity: WorkflowComplexity = WorkflowComplexity.COMPLETE  # Default to complete
    # Artifact paths
    research_path: str | None = Field(default=None, max_length=500)
    plan_path: str | None = Field(default=None, max_length=500)
    review_path: str | None = Field(default=None, max_length=500)
    # Claude session tracking (replaces job_* fields)
    claude_status: ClaudeStatus | None = None
    started_at: datetime | None = None
    claude_completed_at: datetime | None = None
    approved_at: datetime | None = None
    session_id: str | None = None


class TaskCreate(TaskBase):
    """Properties for creating a new task."""

    # repo_id is required when creating a task
    repo_id: str = Field(..., min_length=1, max_length=500)


class TaskUpdate(BaseModel):
    """Properties for updating a task (all optional)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    stage: Stage | None = None
    priority: Priority | None = None
    tags: list[str] | None = None
    ticket_id: str | None = Field(default=None, max_length=50)
    order: int | None = None
    model: ClaudeModel | None = None
    complexity: WorkflowComplexity | None = None
    # Artifact paths
    research_path: str | None = Field(default=None, max_length=500)
    plan_path: str | None = Field(default=None, max_length=500)
    review_path: str | None = Field(default=None, max_length=500)
    # Claude session tracking
    claude_status: ClaudeStatus | None = None
    started_at: datetime | None = None
    claude_completed_at: datetime | None = None
    approved_at: datetime | None = None
    session_id: str | None = None


class TaskMove(BaseModel):
    """Properties for moving a task to a different stage."""

    stage: Stage
    order: int = 0


class Task(TaskBase):
    """Full task model with system fields."""

    id: UUID = Field(default_factory=uuid4)
    repo_id: str = Field(..., min_length=1, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


class RepoBase(BaseModel):
    """Base repo properties."""

    repo_id: str = Field(..., min_length=1, max_length=500)
    name: str | None = Field(default=None, max_length=200)


class RepoCreate(RepoBase):
    """Properties for registering a new repo."""

    pass


class Repo(RepoBase):
    """Full repo model with system fields."""

    id: UUID = Field(default_factory=uuid4)
    active: bool = True
    task_count: int = 0  # Populated by query
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


# Stage definitions with metadata
STAGES: list[StageInfo] = [
    StageInfo(
        id=Stage.BACKLOG,
        name="Backlog",
        color="#6B7280",  # gray
        command=None,
        description="New ideas and tasks waiting to be started",
    ),
    StageInfo(
        id=Stage.RESEARCH,
        name="Research",
        color="#F59E0B",  # yellow
        command="/research_codebase",
        description="Investigating codebase and requirements",
    ),
    StageInfo(
        id=Stage.PLANNING,
        name="Planning",
        color="#8B5CF6",  # purple
        command="/create_plan",
        description="Creating detailed implementation plans",
    ),
    StageInfo(
        id=Stage.IMPLEMENTATION,
        name="Implementation",
        color="#3B82F6",  # blue
        command="/implement_plan",
        description="Writing code and implementing features",
    ),
    StageInfo(
        id=Stage.REVIEW,
        name="Review",
        color="#F97316",  # orange
        command="/code_reviewer",
        description="Code review and security analysis",
    ),
    StageInfo(
        id=Stage.CLEANUP,
        name="Cleanup",
        color="#06B6D4",  # cyan
        command="/cleanup",
        description="Documenting best practices and removing artifacts",
    ),
    StageInfo(
        id=Stage.COMMIT,
        name="Commit",
        color="#EC4899",  # pink
        command="/commit",
        description="Committing changes and creating PR",
    ),
    StageInfo(
        id=Stage.DONE,
        name="Done",
        color="#22C55E",  # green
        command=None,
        description="Completed and shipped",
    ),
]
