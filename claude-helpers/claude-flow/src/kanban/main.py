"""FastAPI application for Kanban workflow board."""

import contextlib
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv

# Project root path (main.py -> kanban -> src -> claude-flow -> claude-helpers -> PROJECT_ROOT)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Claude-flow directory (main.py -> kanban -> src -> claude-flow)
CLAUDE_FLOW_DIR = Path(__file__).parent.parent.parent

# Load .env file from claude-flow directory before other imports
env_path = CLAUDE_FLOW_DIR / ".env"
load_dotenv(env_path)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from kanban.database import init_db, seed_db  # noqa: E402
from kanban.routers import codebase, docs, security, tasks, terminal  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    seed_db()
    yield


app = FastAPI(
    title="Claude Workflow Kanban",
    description="Kanban board API for managing Claude Code workflow tasks",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local development (port range 8119-8129 for dynamic port allocation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *[f"http://localhost:{port}" for port in range(8119, 8130)],
        *[f"http://127.0.0.1:{port}" for port in range(8119, 8130)],
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(terminal.router)
app.include_router(docs.router)
app.include_router(codebase.router)
app.include_router(security.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "claude-workflow-kanban"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


class RepoInfo(TypedDict):
    """Repository information response structure."""

    name: str | None
    repo_root: str


@app.get("/api/repo")
def get_repo_info() -> RepoInfo:
    """Get repository information.

    Returns:
        RepoInfo with:
            - name: Repository name from git remote or directory name
            - repo_root: Repository root path (file-based, consistent)
            - cwd: Project root working directory for Claude commands
    """
    repo_name = None

    # Both paths use PROJECT_ROOT for consistency
    repo_root = str(PROJECT_ROOT)  # File-based, always consistent


    # Try to get repo name from git remote origin URL
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
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

    # Fall back to repo_root directory name if no git remote
    if not repo_name:
        with contextlib.suppress(Exception):
            repo_name = Path(repo_root).name

    return {"name": repo_name, "repo_root": repo_root}
