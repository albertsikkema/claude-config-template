#!/usr/bin/env python3
"""Claude Flow Desktop Application.

Per-repo desktop application using PyWebView.
Starts FastAPI backend and opens desktop window.

Usage:
    python desktop_app.py         # Production mode
    python desktop_app.py --dev   # Development mode with auto-reload
"""

import os
import sys

# IMPORTANT: Disable pydantic plugins BEFORE any imports
# When running from PyInstaller bundle, logfire tries to inspect source code
# which doesn't exist, causing OSError. Set this early to prevent the issue.
if getattr(sys, "frozen", False):
    os.environ["LOGFIRE_IGNORE_NO_CONFIG"] = "1"
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"

import atexit
import contextlib
import logging
import signal
import socket
import subprocess
import threading
from pathlib import Path

import uvicorn
import webview
from webview import Window

# Parse --dev flag early
DEV_MODE = "--dev" in sys.argv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_bundle_dir() -> Path:
    """Get the directory where PyInstaller bundle is extracted.

    Returns:
        Path: Bundle directory for frozen app, or script directory otherwise
    """
    if getattr(sys, "frozen", False):
        # Running from PyInstaller bundle
        # sys._MEIPASS is the temp directory where PyInstaller extracts files
        return Path(sys._MEIPASS)
    else:
        # Running from Python script
        return Path(__file__).parent


def get_project_root() -> Path:
    """Get the project root directory (the repo where app was launched).

    Returns:
        Path: Current working directory (where user launched the app)
    """
    if getattr(sys, "frozen", False):
        # When running from bundle, use the directory where app was launched
        # This is the actual repository directory
        return Path.cwd()
    else:
        # When running from script, calculate from __file__
        return Path(__file__).parent.parent.parent


# Project root path - where the repository actually is
PROJECT_ROOT = get_project_root()

# Bundle directory - where PyInstaller extracted files (or script location)
BUNDLE_DIR = get_bundle_dir()

# Claude-flow directory for non-bundled mode
CLAUDE_FLOW_DIR = BUNDLE_DIR if getattr(sys, "frozen", False) else Path(__file__).parent

# Fixed port for global app - hooks always call localhost:9118
FIXED_PORT = 9118


def is_port_available(port: int) -> bool:
    """Check if a port is available.

    Args:
        port: Port number to check

    Returns:
        bool: True if port is available
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def get_repo_name() -> str:
    """Get repository name from git remote or directory name.

    Returns:
        str: Repository name
    """
    repo_name = None

    # Try to get repo name from git remote origin URL
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(PROJECT_ROOT),
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

    # Fall back to directory name if no git remote
    if not repo_name:
        with contextlib.suppress(Exception):
            repo_name = PROJECT_ROOT.name

    return repo_name or "Unknown"


def start_backend(port: int) -> None:
    """Start FastAPI backend in background thread (production mode).

    Args:
        port: Port number to bind to
    """
    logger.info(f"Starting FastAPI backend on port {port}")

    # Import here to ensure logging is configured first
    from kanban.main import app

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,  # Reduce noise in desktop app
    )
    server = uvicorn.Server(config)
    server.run()


def start_backend_dev(port: int) -> subprocess.Popen:
    """Start FastAPI backend as subprocess with auto-reload (dev mode).

    Args:
        port: Port number to bind to

    Returns:
        subprocess.Popen: The backend process
    """
    logger.info(f"Starting FastAPI backend on port {port} with auto-reload")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "kanban.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--reload",
        "--reload-dir",
        "src",
    ]

    process = subprocess.Popen(
        cmd,
        cwd=str(CLAUDE_FLOW_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Log output in background thread
    def log_output():
        for line in iter(process.stdout.readline, b""):
            logger.info(f"[uvicorn] {line.decode().rstrip()}")

    threading.Thread(target=log_output, daemon=True).start()

    return process


def start_frontend_dev() -> subprocess.Popen:
    """Start Vite dev server for frontend HMR.

    Returns:
        subprocess.Popen: The Vite process
    """
    logger.info("Starting Vite dev server on port 8119")

    frontend_dir = CLAUDE_FLOW_DIR / "claude-flow-board"

    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Log output in background thread
    def log_output():
        for line in iter(process.stdout.readline, b""):
            logger.info(f"[vite] {line.decode().rstrip()}")

    threading.Thread(target=log_output, daemon=True).start()

    return process


class Api:
    """JavaScript API exposed to the webview frontend.

    Methods on this class can be called from JavaScript via:
    window.pywebview.api.method_name()
    """

    def __init__(self, window: Window | None = None):
        self._window = window

    def set_window(self, window: Window) -> None:
        """Set the window reference after creation."""
        self._window = window

    def select_folder(self) -> str | None:
        """Open native folder selection dialog.

        Returns:
            Selected folder path or None if cancelled
        """
        if not self._window:
            logger.error("Window not set for folder selection")
            return None

        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=str(Path.home()),
        )

        if result and len(result) > 0:
            selected_path = result[0]
            logger.info(f"Folder selected: {selected_path}")
            return selected_path

        return None

    def is_git_repo(self, path: str) -> bool:
        """Check if a path is a git repository.

        Args:
            path: Path to check

        Returns:
            True if path contains a .git directory
        """
        git_dir = Path(path) / ".git"
        return git_dir.exists()


def main() -> None:
    """Launch desktop application."""
    # Check if frontend is built (in bundle or in dev)
    frontend_dist = BUNDLE_DIR / "claude-flow-board" / "dist"
    if not frontend_dist.exists():
        logger.error(
            f"Frontend not found at {frontend_dist}\n"
            f"If running from source, build frontend:\n"
            f"  cd claude-flow-board && npm run build"
        )
        sys.exit(1)

    mode = "development" if DEV_MODE else "production"
    logger.info(f"Mode: {mode}")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Bundle dir: {BUNDLE_DIR}")
    logger.info(f"Frontend: {frontend_dist}")

    # Check if Claude Flow is already running on the fixed port
    if not is_port_available(FIXED_PORT):
        logger.info(f"Claude Flow already running on port {FIXED_PORT}")
        logger.info("Opening browser to existing instance...")
        # Open browser to existing instance instead of starting a new one
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{FIXED_PORT}")
        return

    # Get repo name for window title (global app, shows current repo)
    repo_name = get_repo_name()
    window_title = "Claude Flow"
    if DEV_MODE:
        window_title += " [DEV]"
    logger.info(f"Current repository: {repo_name}")

    # Use fixed port for global app
    port = FIXED_PORT
    url = f"http://127.0.0.1:{port}"
    logger.info(f"Backend URL: {url}")

    backend_process = None
    frontend_process = None

    if DEV_MODE:
        # Start backend with auto-reload
        backend_process = start_backend_dev(port)

        # Start Vite dev server for frontend HMR
        frontend_process = start_frontend_dev()

        # Webview loads from Vite dev server
        url = "http://127.0.0.1:8119"

        # Register cleanup for subprocesses
        def cleanup():
            for name, proc in [("backend", backend_process), ("frontend", frontend_process)]:
                if proc and proc.poll() is None:
                    logger.info(f"Terminating {name} process...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()

        atexit.register(cleanup)
        signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
        signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

        # Give both servers time to start
        import time
        time.sleep(4)
    else:
        # Production mode: run uvicorn in thread
        backend_thread = threading.Thread(target=start_backend, args=(port,), daemon=True)
        backend_thread.start()

        # Give backend time to start
        import time
        time.sleep(2)

    # Create API instance for JavaScript interop
    api = Api()

    # Create and start PyWebView window
    logger.info(f"Opening desktop window: {window_title}")

    try:
        window = webview.create_window(
            window_title,
            url,
            width=1400,
            height=900,
            resizable=True,
            js_api=api,
        )

        # Set window reference in API for folder dialogs
        api.set_window(window)

        # Start the window (this blocks until window is closed)
        logger.info("Starting webview...")
        webview.start()
        logger.info("Application closed")
    except Exception as e:
        logger.error(f"Failed to start webview: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure processes are cleaned up
        for proc in [backend_process, frontend_process]:
            if proc and proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    main()
