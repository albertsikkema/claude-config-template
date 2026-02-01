#!/usr/bin/env python3
"""
Shared audio utilities for Claude Code hooks.

Provides common functions for playing audio notifications.
Set CLAUDE_AUDIO_ENABLED=1 to enable audio notifications (disabled by default).
Set CLAUDE_HOOKS_DEBUG=1 to enable debug logging.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')


def debug_log(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] audio: {message}", file=sys.stderr)


def get_project_root() -> Path:
    """
    Find project root by looking for .env, .git directory, or CLAUDE_PROJECT_DIR.
    Falls back to current working directory.
    """
    # First check environment variable
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        debug_log(f"Using CLAUDE_PROJECT_DIR: {project_dir}")
        return Path(project_dir)

    # Search upward from this file's location
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Max 10 levels up
        if (current / ".env").exists():
            debug_log(f"Found .env at: {current}")
            return current
        if (current / ".git").exists():
            debug_log(f"Found .git at: {current}")
            return current
        if current.parent == current:
            break
        current = current.parent

    # Fallback to cwd
    debug_log(f"Falling back to cwd: {Path.cwd()}")
    return Path.cwd()


def load_env_file() -> None:
    """Load environment variables from .env file in project root."""
    env_path = get_project_root() / ".env"
    if env_path.exists():
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        if key not in os.environ:  # Don't override existing env vars
                            os.environ[key] = value
            debug_log(f"Loaded env file: {env_path}")
        except Exception as e:
            debug_log(f"Error loading env file: {e}")


def is_audio_enabled() -> bool:
    """Check if audio is enabled via environment variable or .env file. Disabled by default."""
    load_env_file()
    enabled = os.environ.get("CLAUDE_AUDIO_ENABLED", "").lower() in ("1", "true", "yes")
    debug_log(f"Audio enabled: {enabled}")
    return enabled


def get_random_audio_file(category: str = "notification") -> Path | None:
    """Get a random audio file from the specified category directory."""
    audio_dir = Path(__file__).parent / "audio" / category

    if not audio_dir.exists():
        debug_log(f"Audio directory not found: {audio_dir}")
        return None

    audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))

    if not audio_files:
        debug_log(f"No audio files in: {audio_dir}")
        return None

    selected = random.choice(audio_files)
    debug_log(f"Selected audio file: {selected}")
    return selected


def play_audio(category: str = "notification") -> None:
    """Play a random audio file from the specified category."""
    try:
        audio_file = get_random_audio_file(category)
        if not audio_file:
            return

        subprocess.run(
            ["afplay", str(audio_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        debug_log(f"Played audio: {audio_file}")
    except subprocess.TimeoutExpired:
        debug_log("Audio playback timed out")
    except Exception as e:
        debug_log(f"Error playing audio: {e}")
