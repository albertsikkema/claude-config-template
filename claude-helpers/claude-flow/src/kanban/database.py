"""Database configuration using SQLAlchemy with SQLite."""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from kanban.models import ClaudeModel, ClaudeStatus, Priority, Stage, WorkflowComplexity

# Database file location
DB_PATH = Path(__file__).parent.parent.parent / "data" / "kanban.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy uses connection pooling internally via the engine.
# For SQLite with check_same_thread=False, it uses StaticPool (single connection).
# SessionLocal creates lightweight session objects that share the underlying pool.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class TaskDB(Base):
    """SQLAlchemy model for tasks."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    stage = Column(Enum(Stage), default=Stage.BACKLOG, nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM, nullable=False)
    tags_json = Column(Text, default="[]")  # Store as JSON string
    ticket_id = Column(String(50), nullable=True)
    order = Column(Integer, default=0)
    model = Column(Enum(ClaudeModel), default=ClaudeModel.SONNET, nullable=False)
    complexity = Column(
        Enum(WorkflowComplexity), default=WorkflowComplexity.COMPLETE, nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Artifact paths
    research_path = Column(String(500), nullable=True)
    plan_path = Column(String(500), nullable=True)
    review_path = Column(String(500), nullable=True)
    # Claude session tracking (NEW)
    claude_status = Column(Enum(ClaudeStatus), nullable=True)
    started_at = Column(DateTime, nullable=True)
    claude_completed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    session_id = Column(String(100), nullable=True)

    @property
    def tags(self) -> list[str]:
        return json.loads(self.tags_json) if self.tags_json else []

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.tags_json = json.dumps(value)


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def seed_db():
    """Add initial sample tasks if database is empty."""
    db = SessionLocal()
    try:
        if db.query(TaskDB).count() == 0:
            sample_tasks = [
                TaskDB(
                    title="Add user authentication",
                    description="Implement OAuth2 login flow with JWT tokens",
                    stage=Stage.BACKLOG,
                    priority=Priority.HIGH,
                    tags_json=json.dumps(["feature", "auth"]),
                    order=0,
                ),
                TaskDB(
                    title="Refactor database layer",
                    description="Migrate from raw SQL to SQLAlchemy ORM",
                    stage=Stage.RESEARCH,
                    priority=Priority.MEDIUM,
                    tags_json=json.dumps(["refactor"]),
                    order=0,
                ),
                TaskDB(
                    title="Fix login timeout bug",
                    description="Users are logged out after 5 minutes instead of 30",
                    stage=Stage.PLANNING,
                    priority=Priority.HIGH,
                    tags_json=json.dumps(["bugfix"]),
                    ticket_id="BUG-456",
                    order=0,
                ),
            ]
            db.add_all(sample_tasks)
            db.commit()
    finally:
        db.close()
