"""WebSocket terminal endpoint for interactive Claude sessions."""

import asyncio
import fcntl
import os
import pty
import shutil
import signal
import struct
import termios
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["terminal"])

# Project root path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

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

        # Execute claude with resume
        os.execve(CLAUDE_PATH, [CLAUDE_PATH, "--resume", session_id], env)
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

            try:
                await send_task
            except asyncio.CancelledError:
                pass

            # Cleanup
            os.close(master_fd)
            try:
                os.kill(pid, signal.SIGTERM)
                os.waitpid(pid, 0)
            except OSError:
                pass
