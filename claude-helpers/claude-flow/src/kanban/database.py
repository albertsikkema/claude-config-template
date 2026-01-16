"""Database configuration using SQLAlchemy with SQLite."""

import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from kanban.models import ClaudeModel, ClaudeStatus, Priority, Stage, WorkflowComplexity


def get_global_app_dir() -> Path:
    """Get the global application data directory.

    Returns:
        Path: Global app support directory for claude-flow
    """
    if sys.platform == "darwin":
        app_support = Path.home() / "Library" / "Application Support" / "claude-flow"
    elif sys.platform == "win32":
        app_support = Path.home() / "AppData" / "Local" / "claude-flow"
    else:
        # Linux and others - use XDG standard
        xdg_data = Path.home() / ".local" / "share"
        app_support = xdg_data / "claude-flow"

    app_support.mkdir(parents=True, exist_ok=True)
    return app_support


def get_db_path() -> Path:
    """Get database path - always in global app directory.

    Returns:
        Path: Database file path in global location
    """
    app_dir = get_global_app_dir()
    db_path = app_dir / "kanban.db"
    return db_path


# Database file location (global for all repos)
DB_PATH = get_db_path()

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy uses connection pooling internally via the engine.
# For SQLite with check_same_thread=False, it uses StaticPool (single connection).
# SessionLocal creates lightweight session objects that share the underlying pool.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class SettingDB(Base):
    """SQLAlchemy model for application settings (key-value store)."""

    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RepoDB(Base):
    """SQLAlchemy model for registered repositories."""

    __tablename__ = "repos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # repo_id is the absolute path to the repository root
    repo_id = Column(String(500), nullable=False, unique=True, index=True)
    # Display name (extracted from git remote or directory name)
    name = Column(String(200), nullable=True)
    # Whether this repo is active (can be hidden but tasks preserved)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Template tracking fields
    template_status = Column(
        String(50), default="not_installed"
    )  # not_installed, installing, installed, failed
    template_version = Column(String(50), nullable=True)  # e.g., "1.0.0"
    template_installed_at = Column(DateTime, nullable=True)


class TaskDB(Base):
    """SQLAlchemy model for tasks."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Repository this task belongs to (absolute path)
    repo_id = Column(String(500), nullable=False, index=True)
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
    # Auto-advance: when enabled, task automatically advances without manual approval
    auto_advance = Column(Boolean, default=False, nullable=False)
    # Claude session tracking
    claude_status = Column(Enum(ClaudeStatus), nullable=True)
    started_at = Column(DateTime, nullable=True)
    claude_completed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    session_id = Column(String(100), nullable=True)
    # Notification tracking
    last_notification = Column(DateTime, nullable=True)

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
    # Run migrations for existing databases
    migrate_db()


def migrate_db():
    """Run database migrations for schema changes.

    Adds missing columns to existing tables. SQLite requires
    ALTER TABLE ADD COLUMN for each new column.
    """
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in repos table
    cursor.execute("PRAGMA table_info(repos)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add template tracking columns if missing
    migrations = [
        ("template_status", "VARCHAR(50) DEFAULT 'not_installed'"),
        ("template_version", "VARCHAR(50)"),
        ("template_installed_at", "DATETIME"),
    ]

    for column_name, column_def in migrations:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE repos ADD COLUMN {column_name} {column_def}")
                print(f"Added column {column_name} to repos table")
            except sqlite3.OperationalError as e:
                # Column might already exist
                print(f"Migration note: {e}")

    # Check existing columns in tasks table
    cursor.execute("PRAGMA table_info(tasks)")
    existing_task_columns = {row[1] for row in cursor.fetchall()}

    # Add notification tracking column if missing
    if "last_notification" not in existing_task_columns:
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN last_notification DATETIME")
            print("Added column last_notification to tasks table")

            # Backfill: Set last_notification = claude_completed_at for existing completed tasks
            cursor.execute("""
                UPDATE tasks
                SET last_notification = claude_completed_at
                WHERE claude_status IN ('ready_for_review', 'approved', 'failed')
                  AND claude_completed_at IS NOT NULL
            """)
            print("Backfilled last_notification for existing completed tasks")
        except sqlite3.OperationalError as e:
            print(f"Migration note: {e}")

    # Add auto_advance column if missing
    if "auto_advance" not in existing_task_columns:
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN auto_advance BOOLEAN DEFAULT 0 NOT NULL")
            print("Added column auto_advance to tasks table")
        except sqlite3.OperationalError as e:
            print(f"Migration note: {e}")

    conn.commit()
    conn.close()


def seed_db():
    """No longer seeds sample data - users create their own tasks."""
    # Removed sample task seeding as global app needs repo context
    pass
