"""iTerm2 tab management via AppleScript + shell script."""

import logging
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/iterm", tags=["iterm"])


def get_launch_script_path(repo_path: str) -> Path:
    """Get path to launch script in the given repository.

    Args:
        repo_path: Absolute path to the repository root

    Returns:
        Path to the launch-claude-tab.sh script
    """
    return Path(repo_path) / "claude-helpers" / "launch-claude-tab.sh"


class OpenTabRequest(BaseModel):
    """Request to open an iTerm tab for a task."""

    task_id: str = Field(..., min_length=1, max_length=100)
    task_title: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(default="", description="Prompt to pass to Claude")
    stage: str = Field(default="default", description="Stage for color coding")
    model: str = Field(default="sonnet", description="Claude model to use")
    session_id: str | None = Field(default=None, description="Session ID for new session")
    is_resume: bool = Field(default=False, description="True to resume existing session")
    repo_id: str = Field(..., min_length=1, max_length=500, description="Repository path")


class OpenTabResponse(BaseModel):
    """Response from opening an iTerm tab."""

    status: str
    tab_name: str
    session_id: str
    iterm_session_id: str | None = None  # iTerm's internal session unique ID


class CloseTabRequest(BaseModel):
    """Request to close an iTerm tab."""

    tab_name: str = Field(..., min_length=1, max_length=300)


def sanitize_tab_name(name: str) -> str:
    """Sanitize tab name to only contain safe characters."""
    sanitized = re.sub(r"[^\w\s\-\.]", " ", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "Task"


def _escape_applescript(s: str) -> str:
    """Escape string for AppleScript."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _is_iterm_running() -> bool:
    """Check if iTerm is running using pgrep (fast, ~10ms)."""
    try:
        result = subprocess.run(["pgrep", "-x", "iTerm2"], capture_output=True, timeout=1)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


@router.post("/open-tab", response_model=OpenTabResponse)
async def open_claude_tab(request: OpenTabRequest) -> OpenTabResponse:
    """Open a new iTerm tab with Claude for a task.

    Creates a named tab, sets the color based on stage, and runs the specified command.
    Returns a session_id that can be used to correlate Claude hooks and resume sessions.

    The session_id is passed to Claude with --session-id flag so it uses our ID,
    making session resume work correctly.
    """
    tab_name = sanitize_tab_name(f"{request.task_id[:8]} {request.task_title[:50]}")
    # Use provided session_id or generate new one
    session_id = request.session_id or str(uuid4())

    # Build the shell command that calls our launch script
    # The script handles title, color, cd, clear, and exec
    # Use the task's repo_id to find the launch script
    launch_script = get_launch_script_path(request.repo_id)
    if not launch_script.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Launch script not found at {launch_script}. "
            "Ensure claude-helpers is installed in this repository.",
        )

    script_path = str(launch_script)
    project_dir = request.repo_id

    # Full command to run in the terminal (script handles quoting internally)
    # Pass session_id and is_resume flag
    is_resume_flag = "true" if request.is_resume else ""
    full_command = (
        f'"{script_path}" '
        f'"{request.task_id}" '
        f'"{request.task_title}" '
        f'"{request.stage}" '
        f'"{project_dir}" '
        f'"{request.model}" '
        f'"{request.prompt}" '
        f'"{session_id}" '
        f'"{is_resume_flag}"'
    )

    # Check if iTerm is running
    iterm_was_running = _is_iterm_running()

    # AppleScript to open tab and run the launch script
    # Returns the iTerm session's unique ID so we can close it later
    if not iterm_was_running:
        script = f'''
tell application "iTerm"
    activate
    delay 0.5
    tell current window
        tell current session
            write text "{_escape_applescript(full_command)}"
            return unique ID
        end tell
    end tell
end tell
'''
    else:
        script = f'''
tell application "iTerm"
    activate
    delay 0.3
    if (count of windows) = 0 then
        create window with default profile
        tell current window
            tell current session
                write text "{_escape_applescript(full_command)}"
                return unique ID
            end tell
        end tell
    else
        tell current window
            create tab with default profile
            tell current session
                write text "{_escape_applescript(full_command)}"
                return unique ID
            end tell
        end tell
    end if
end tell
'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script], check=True, capture_output=True, timeout=10, text=True
        )
        iterm_session_id = result.stdout.strip() if result.stdout else None
        logger.info(f"Opened iTerm tab: {tab_name}, iterm_session_id: {iterm_session_id}")
        return OpenTabResponse(
            status="opened",
            tab_name=tab_name,
            session_id=session_id,
            iterm_session_id=iterm_session_id,
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout opening iTerm tab") from e
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open tab: {e.stderr.decode()}")
        raise HTTPException(500, f"Failed to open tab: {e.stderr.decode()}") from e


class CloseTabByTaskRequest(BaseModel):
    """Request to close an iTerm tab by task ID prefix."""

    task_id: str = Field(..., min_length=1, max_length=100)


class CloseTabByItermIdRequest(BaseModel):
    """Request to close an iTerm tab by its unique session ID."""

    iterm_session_id: str = Field(..., min_length=1, max_length=100)


@router.post("/close-tab")
async def close_claude_tab(request: CloseTabRequest):
    """Close an iTerm tab by name (exact match - legacy)."""
    sanitized_name = sanitize_tab_name(request.tab_name)
    escaped_name = _escape_applescript(sanitized_name)

    script = f"""
    tell application "iTerm"
        repeat with w in windows
            repeat with t in tabs of w
                repeat with s in sessions of t
                    if name of s is "{escaped_name}" then
                        close t
                        return "closed"
                    end if
                end repeat
            end repeat
        end repeat
        return "not_found"
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        return {"status": status, "tab_name": request.tab_name}
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout closing iTerm tab") from e


@router.post("/close-tab-by-task")
async def close_tab_by_task(request: CloseTabByTaskRequest):
    """Close an iTerm tab by task ID prefix.

    More reliable than close-tab because it uses 'starts with' matching,
    which works even when Claude changes the terminal title during execution.
    """
    task_prefix = request.task_id[:8]

    script = f'''
tell application "iTerm"
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                if name of s starts with "{task_prefix}" then
                    close t
                    return "closed"
                end if
            end repeat
        end repeat
    end repeat
    return "not_found"
end tell
'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        return {"status": status, "task_id": request.task_id}
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout closing iTerm tab") from e


@router.post("/close-tab-by-iterm-id")
async def close_tab_by_iterm_id(request: CloseTabByItermIdRequest):
    """Close an iTerm tab by its unique session ID.

    This is the most reliable method because iTerm's unique ID never changes,
    even when Claude changes the terminal title.
    """
    escaped_id = _escape_applescript(request.iterm_session_id)

    script = f'''
tell application "iTerm"
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                if unique ID of s is "{escaped_id}" then
                    close t
                    return "closed"
                end if
            end repeat
        end repeat
    end repeat
    return "not_found"
end tell
'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        return {"status": status, "iterm_session_id": request.iterm_session_id}
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout closing iTerm tab") from e


class FocusTabRequest(BaseModel):
    """Request to focus an iTerm tab."""

    task_id: str = Field(..., min_length=1, max_length=100)


@router.post("/focus-tab")
async def focus_claude_tab(request: FocusTabRequest):
    """Focus an iTerm tab by task ID prefix.

    Searches for a tab whose name starts with the task ID and brings it to focus.
    """
    task_prefix = request.task_id[:8]

    script = f'''
tell application "iTerm"
    activate
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                if name of s starts with "{task_prefix}" then
                    select t
                    return "focused"
                end if
            end repeat
        end repeat
    end repeat
    return "not_found"
end tell
'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        return {"status": status, "task_id": request.task_id}
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout focusing iTerm tab") from e


@router.get("/list-tabs")
async def list_claude_tabs():
    """List all iTerm tabs with their names."""
    script = """
    tell application "iTerm"
        set tabNames to {}
        repeat with w in windows
            repeat with t in tabs of w
                repeat with s in sessions of t
                    set end of tabNames to name of s
                end repeat
            end repeat
        end repeat
        return tabNames
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        raw = result.stdout.strip()
        tabs = [t.strip() for t in raw.split(",")] if raw else []
        return {"tabs": tabs}
    except subprocess.TimeoutExpired:
        return {"tabs": [], "error": "timeout"}


class OpenAppRequest(BaseModel):
    """Request to open an application at a repo path."""

    repo_id: str = Field(..., min_length=1, max_length=500, description="Repository path")


@router.post("/open-vscode")
async def open_vscode(request: OpenAppRequest):
    """Open VS Code at the specified repository path."""
    repo_path = request.repo_id

    # Validate path exists
    if not Path(repo_path).exists():
        raise HTTPException(404, f"Path not found: {repo_path}")

    try:
        # Use 'code' command to open VS Code
        subprocess.run(["code", repo_path], check=True, capture_output=True, timeout=10)
        logger.info(f"Opened VS Code at: {repo_path}")
        return {"status": "opened", "path": repo_path}
    except FileNotFoundError as e:
        raise HTTPException(
            500,
            "VS Code 'code' command not found. "
            "Install it via VS Code: Cmd+Shift+P -> 'Shell Command: Install code command'",
        ) from e
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout opening VS Code") from e
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open VS Code: {e.stderr.decode()}")
        raise HTTPException(500, f"Failed to open VS Code: {e.stderr.decode()}") from e


@router.post("/open-terminal")
async def open_terminal(request: OpenAppRequest):
    """Open iTerm at the specified repository path."""
    repo_path = request.repo_id

    # Validate path exists
    if not Path(repo_path).exists():
        raise HTTPException(404, f"Path not found: {repo_path}")

    escaped_path = _escape_applescript(repo_path)
    iterm_was_running = _is_iterm_running()

    if not iterm_was_running:
        script = f'''
tell application "iTerm"
    activate
    delay 0.5
    tell current window
        tell current session
            write text "cd \\"{escaped_path}\\" && clear"
        end tell
    end tell
end tell
'''
    else:
        script = f'''
tell application "iTerm"
    activate
    delay 0.3
    if (count of windows) = 0 then
        create window with default profile
        tell current window
            tell current session
                write text "cd \\"{escaped_path}\\" && clear"
            end tell
        end tell
    else
        tell current window
            create tab with default profile
            tell current session
                write text "cd \\"{escaped_path}\\" && clear"
            end tell
        end tell
    end if
end tell
'''

    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
        logger.info(f"Opened iTerm at: {repo_path}")
        return {"status": "opened", "path": repo_path}
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout opening iTerm") from e
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open iTerm: {e.stderr.decode()}")
        raise HTTPException(500, f"Failed to open iTerm: {e.stderr.decode()}") from e


@router.post("/open-claude")
async def open_claude(request: OpenAppRequest):
    """Open Claude CLI in iTerm at the specified repository path."""
    repo_path = request.repo_id

    # Validate path exists
    if not Path(repo_path).exists():
        raise HTTPException(404, f"Path not found: {repo_path}")

    escaped_path = _escape_applescript(repo_path)
    iterm_was_running = _is_iterm_running()

    # Command to cd to path and start Claude CLI
    command = f'cd \\"{escaped_path}\\" && clear && claude'

    if not iterm_was_running:
        script = f'''
tell application "iTerm"
    activate
    delay 0.5
    tell current window
        tell current session
            write text "{command}"
        end tell
    end tell
end tell
'''
    else:
        script = f'''
tell application "iTerm"
    activate
    delay 0.3
    if (count of windows) = 0 then
        create window with default profile
        tell current window
            tell current session
                write text "{command}"
            end tell
        end tell
    else
        tell current window
            create tab with default profile
            tell current session
                write text "{command}"
            end tell
        end tell
    end if
end tell
'''

    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
        logger.info(f"Opened Claude CLI at: {repo_path}")
        return {"status": "opened", "path": repo_path}
    except subprocess.TimeoutExpired as e:
        raise HTTPException(500, "Timeout opening Claude CLI") from e
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open Claude CLI: {e.stderr.decode()}")
        raise HTTPException(500, f"Failed to open Claude CLI: {e.stderr.decode()}") from e
