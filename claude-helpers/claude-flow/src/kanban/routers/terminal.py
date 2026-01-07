"""WebSocket terminal endpoint for interactive Claude sessions."""

import asyncio
import contextlib
import fcntl
import os
import platform
import pty
import shutil
import signal
import struct
import subprocess
import termios
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["terminal"])

# Project root path
# terminal.py -> routers -> kanban -> src -> claude-flow -> claude-helpers -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Find claude executable
CLAUDE_PATH = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")


@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for interactive terminal with Claude resume."""
    await websocket.accept()

    # Create pseudo-terminal
    master_fd, slave_fd = pty.openpty()

    # Set initial terminal size
    winsize = struct.pack("HHHH", 24, 80, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    # Fork process
    pid = os.fork()

    if pid == 0:
        # Child process
        os.close(master_fd)
        os.setsid()

        # Set up controlling terminal
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

        os.dup2(slave_fd, 0)  # stdin
        os.dup2(slave_fd, 1)  # stdout
        os.dup2(slave_fd, 2)  # stderr

        if slave_fd > 2:
            os.close(slave_fd)

        # Change to project directory
        os.chdir(str(PROJECT_ROOT))

        # Set environment
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["HOME"] = str(Path.home())
        env["COLORTERM"] = "truecolor"

        # Execute claude with resume in yolo mode
        os.execve(
            CLAUDE_PATH,
            [CLAUDE_PATH, "--resume", session_id, "--dangerously-skip-permissions"],
            env,
        )
    else:
        # Parent process
        os.close(slave_fd)

        loop = asyncio.get_event_loop()
        output_queue: asyncio.Queue[bytes] = asyncio.Queue()
        running = True

        def on_pty_read():
            """Callback when PTY has data to read."""
            try:
                data = os.read(master_fd, 4096)
                if data:
                    output_queue.put_nowait(data)
            except OSError:
                pass

        # Add reader for PTY
        loop.add_reader(master_fd, on_pty_read)

        async def send_output():
            """Send PTY output to WebSocket."""
            while running:
                try:
                    data = await asyncio.wait_for(output_queue.get(), timeout=0.1)
                    await websocket.send_bytes(data)
                except TimeoutError:
                    continue
                except Exception:
                    break

        # Start output sender
        send_task = asyncio.create_task(send_output())

        try:
            # Receive from WebSocket and write to PTY
            while True:
                try:
                    message = await websocket.receive()

                    if message["type"] == "websocket.disconnect":
                        break

                    if "bytes" in message:
                        data = message["bytes"]
                        os.write(master_fd, data)
                    elif "text" in message:
                        text = message["text"]
                        # Handle resize messages
                        if text.startswith("resize:"):
                            try:
                                _, cols, rows = text.split(":")
                                cols, rows = int(cols), int(rows)
                                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                            except (ValueError, OSError):
                                pass
                        else:
                            os.write(master_fd, text.encode())
                except WebSocketDisconnect:
                    break

        finally:
            running = False
            loop.remove_reader(master_fd)
            send_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await send_task

            # Cleanup
            os.close(master_fd)
            try:
                os.kill(pid, signal.SIGTERM)
                os.waitpid(pid, 0)
            except OSError:
                pass


@router.post("/api/terminal/{session_id}/open")
async def open_native_terminal(session_id: str):
    """Open a native system terminal with Claude resume session.

    Supports macOS, Linux, and Windows.
    """
    try:
        system = platform.system()

        if system == "Darwin":  # macOS
            # Use AppleScript to open Terminal.app and run the command
            script = f"""
            tell application "Terminal"
                activate
                do script "cd '{str(PROJECT_ROOT)}' && {CLAUDE_PATH} --resume {session_id} --dangerously-skip-permissions"
            end tell
            """
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
            )
            return {"status": "success", "message": "Terminal opened on macOS"}

        elif system == "Linux":
            # Try common Linux terminal emulators
            terminals = [
                [
                    "gnome-terminal",
                    "--",
                    "bash",
                    "-c",
                    f"cd '{PROJECT_ROOT}' && {CLAUDE_PATH} --resume {session_id} --dangerously-skip-permissions",
                ],
                [
                    "xterm",
                    "-e",
                    f"cd '{PROJECT_ROOT}' && {CLAUDE_PATH} --resume {session_id} --dangerously-skip-permissions",
                ],
                [
                    "xfce4-terminal",
                    "--execute",
                    f"cd '{PROJECT_ROOT}' && {CLAUDE_PATH} --resume {session_id} --dangerously-skip-permissions",
                ],
                [
                    "konsole",
                    "-e",
                    f"cd '{PROJECT_ROOT}' && {CLAUDE_PATH} --resume {session_id} --dangerously-skip-permissions",
                ],
            ]

            for terminal_cmd in terminals:
                try:
                    subprocess.Popen(terminal_cmd)
                    return {"status": "success", "message": "Terminal opened on Linux"}
                except FileNotFoundError:
                    continue

            raise HTTPException(
                status_code=400,
                detail="No supported terminal emulator found. Install gnome-terminal, xterm, xfce4-terminal, or konsole.",
            )

        elif system == "Windows":
            # Use Windows Terminal or Command Prompt
            cmd = f"cd /d {PROJECT_ROOT} && {CLAUDE_PATH} --resume {session_id} --dangerously-skip-permissions"
            try:
                # Try Windows Terminal first
                subprocess.Popen(["wt", "cmd", "/k", cmd])
            except FileNotFoundError:
                # Fallback to cmd.exe
                subprocess.Popen(["cmd", "/k", cmd])
            return {"status": "success", "message": "Terminal opened on Windows"}

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform: {system}",
            )

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open terminal: {e.stderr.decode() if e.stderr else str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error opening terminal: {str(e)}",
        ) from e
