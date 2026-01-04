"""FastAPI application for Kanban workflow board."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root before other imports
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from kanban.database import init_db, seed_db  # noqa: E402
from kanban.routers import tasks, terminal  # noqa: E402


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8119",
        "http://127.0.0.1:8119",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(terminal.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "claude-workflow-kanban"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
