"""FastAPI application for Kanban workflow board."""

import logging
import sys
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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


def get_paths():
    """Get PROJECT_ROOT and CLAUDE_FLOW_DIR based on runtime environment.

    Returns:
        tuple: (PROJECT_ROOT, CLAUDE_FLOW_DIR)
    """
    if getattr(sys, "frozen", False):
        # Running from PyInstaller bundle
        # PROJECT_ROOT is where the app was launched (the actual repo)
        project_root = Path.cwd()
        # CLAUDE_FLOW_DIR is where PyInstaller extracted files
        claude_flow_dir = Path(sys._MEIPASS)
    else:
        # Running from Python script
        # main.py -> kanban -> src -> claude-flow -> claude-helpers -> PROJECT_ROOT
        project_root = Path(__file__).parent.parent.parent.parent.parent
        # main.py -> kanban -> src -> claude-flow
        claude_flow_dir = Path(__file__).parent.parent.parent

    return project_root, claude_flow_dir


# Get paths based on runtime environment
PROJECT_ROOT, CLAUDE_FLOW_DIR = get_paths()

# Global app directory for shared data
GLOBAL_APP_DIR = get_global_app_dir()

# Load .env file from global app directory (shared across all repos)
env_path = GLOBAL_APP_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fall back to claude-flow directory for backwards compatibility
    local_env = CLAUDE_FLOW_DIR / ".env"
    if local_env.exists():
        load_dotenv(local_env)
        logger.info(f"Loaded .env from {local_env} (consider moving to {env_path})")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from kanban.database import init_db, seed_db  # noqa: E402
from kanban.routers import (  # noqa: E402
    codebase,
    docs,
    hooks,
    install,
    iterm,
    repos,
    security,
    settings,
    tasks,
)


class VersionResponse(BaseModel):
    """Application version information."""

    version: str = Field(..., description="Application version (e.g., 0.1.0)")
    service: str = Field(..., description="Service name")


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

# CORS for local development
# Fixed port 9118 for global app, plus dev server ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9118",
        "http://127.0.0.1:9118",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://localhost:8119",  # Legacy dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(repos.router)
app.include_router(docs.router)
app.include_router(codebase.router)
app.include_router(security.router)
app.include_router(iterm.router)
app.include_router(hooks.router)
app.include_router(settings.router)
app.include_router(install.router)


@app.get("/api")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "claude-workflow-kanban"}


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/version")
def get_version() -> VersionResponse:
    """Get application version information.

    Returns:
        VersionResponse with version and service name
    """
    try:
        pyproject_path = CLAUDE_FLOW_DIR / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        version = data["project"]["version"]
    except (FileNotFoundError, KeyError, OSError, ValueError) as e:
        # Fallback to app.version if pyproject.toml cannot be read
        # (file not found, missing version key, read errors, or TOML parsing errors)
        logger.warning("Failed to read version from pyproject.toml: %s", e)
        version = app.version or "unknown"

    return VersionResponse(version=version, service="claude-workflow-kanban")


# Serve built frontend if available (for desktop app)
# This must be LAST so API routes take precedence
FRONTEND_DIST = CLAUDE_FLOW_DIR / "claude-flow-board" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
