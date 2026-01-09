"""Pydantic models for the Kanban API."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Stage(str, Enum):
    """Workflow stages matching Claude Code commands."""

    BACKLOG = "backlog"
    RESEARCH = "research"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    CLEANUP = "cleanup"
    MERGE = "merge"
    DONE = "done"


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobStatus(str, Enum):
    """Background job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
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
    # Claude Code integration fields
    research_path: str | None = Field(default=None, max_length=500)
    plan_path: str | None = Field(default=None, max_length=500)
    review_path: str | None = Field(default=None, max_length=500)
    job_status: JobStatus | None = None
    job_output: str | None = None  # Real-time output buffer
    job_error: str | None = None  # Error message if failed
    job_started_at: datetime | None = None  # When job started
    job_completed_at: datetime | None = None  # When job finished
    session_id: str | None = None  # Claude session ID for resumption


class TaskCreate(TaskBase):
    """Properties for creating a new task."""

    pass


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
    # Claude Code integration fields
    research_path: str | None = Field(default=None, max_length=500)
    plan_path: str | None = Field(default=None, max_length=500)
    review_path: str | None = Field(default=None, max_length=500)
    job_status: JobStatus | None = None
    job_output: str | None = None
    job_error: str | None = None
    job_started_at: datetime | None = None
    job_completed_at: datetime | None = None
    session_id: str | None = None


class TaskMove(BaseModel):
    """Properties for moving a task to a different stage."""

    stage: Stage
    order: int = 0


class Task(TaskBase):
    """Full task model with system fields."""

    id: UUID = Field(default_factory=uuid4)
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
        id=Stage.MERGE,
        name="Merge",
        color="#EC4899",  # pink
        command=None,
        description="Creating PR and merging changes",
    ),
    StageInfo(
        id=Stage.DONE,
        name="Done",
        color="#22C55E",  # green
        command=None,
        description="Completed and shipped",
    ),
]


class StageAutoProgressionConfig(BaseModel):
    """Configuration for automatic stage progression.

    Defines which stage transitions should trigger automatic progression
    to the next stage upon job completion.

    All configured transitions are validated to ensure they move forward
    in the workflow (e.g., IMPLEMENTATION -> REVIEW is valid, but
    REVIEW -> IMPLEMENTATION would be rejected).
    """

    enabled: bool = Field(default=True, description="Global toggle for auto-progression feature")

    stage_transitions: dict[Stage, Stage] = Field(
        default={
            Stage.IMPLEMENTATION: Stage.REVIEW,
            # Potential future transitions (consider implications before enabling):
            # Stage.REVIEW: Stage.CLEANUP,  # Would skip manual review approval step
            # Stage.RESEARCH: Stage.PLANNING,  # Would eliminate research review checkpoint
        },
        description="Map of stage transitions that auto-progress (from_stage -> to_stage)",
    )

    default_order: int = Field(
        default=0, description="Default order/position in target column (0 = top)"
    )

    @field_validator("stage_transitions")
    @classmethod
    def validate_forward_progression(cls, v: dict[Stage, Stage]) -> dict[Stage, Stage]:
        """Ensure all configured transitions move forward in the workflow.

        Raises:
            ValueError: If any transition moves backward in the stage order
        """
        # Define canonical stage order (from kanban workflow)
        stage_order = [
            Stage.BACKLOG,
            Stage.RESEARCH,
            Stage.PLANNING,
            Stage.IMPLEMENTATION,
            Stage.REVIEW,
            Stage.CLEANUP,
            Stage.MERGE,
            Stage.DONE,
        ]
        stage_index = {stage: idx for idx, stage in enumerate(stage_order)}

        for from_stage, to_stage in v.items():
            from_idx = stage_index.get(from_stage)
            to_idx = stage_index.get(to_stage)

            if from_idx is None or to_idx is None:
                raise ValueError(f"Invalid stage in transition: {from_stage} -> {to_stage}")

            if to_idx <= from_idx:
                valid_order = " -> ".join(s.value for s in stage_order)
                raise ValueError(
                    f"Invalid stage transition: {from_stage.value} -> {to_stage.value}. "
                    f"Auto-progression must move forward in workflow. "
                    f"Valid progression order: {valid_order}"
                )

        return v


# Global configuration instance
AUTO_PROGRESSION_CONFIG = StageAutoProgressionConfig()
