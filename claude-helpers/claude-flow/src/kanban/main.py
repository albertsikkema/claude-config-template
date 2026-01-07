"""FastAPI application for Kanban workflow board."""

import contextlib
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root before other imports
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from kanban.database import init_db, seed_db  # noqa: E402
from kanban.routers import docs, tasks, terminal  # noqa: E402


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


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "claude-workflow-kanban"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/repo")
def get_repo_info():
    """Get repository information."""
    repo_name = None
    cwd = None

    # Get current working directory
    with contextlib.suppress(Exception):
        cwd = str(Path.cwd())

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

    # Fall back to current directory name if no git remote
    if not repo_name:
        with contextlib.suppress(Exception):
            repo_name = Path.cwd().name

    return {"name": repo_name, "cwd": cwd}
