#!/usr/bin/env python3
"""
PreToolUse security hook that blocks dangerous operations.

Full mode (default) checks for:
- Dangerous rm commands
- Fork bombs
- Dangerous git commands (all git push, force operations)
- Disk write attacks (dd to /dev/)
- Sensitive file access (.env, .pem, .key, credentials, etc.)
- Path traversal attacks
- Project directory escape

Container mode (CLAUDE_CONTAINER_MODE=1) checks for:
- Dangerous git commands (all git push, force operations)
- Sensitive file access (.env, .pem, .key, credentials, etc.)

Environment variables:
- CLAUDE_HOOKS_DEBUG=1      Enable debug logging
- CLAUDE_CONTAINER_MODE=1   Use relaxed checks for sandboxed/container environments
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')

# Container mode - relaxes some security checks for sandboxed environments
# Keeps: sensitive file access, dangerous git commands
# Disables: rm -rf, fork bombs, disk writes, path escape
CONTAINER_MODE = os.environ.get('CLAUDE_CONTAINER_MODE', '').lower() in ('1', 'true')

# Pre-compiled regex patterns for performance
DANGEROUS_RM_PATTERNS = [
    re.compile(r'\brm\s+.*-[a-z]*r[a-z]*f'),  # rm -rf, rm -fr, rm -Rf, etc.
    re.compile(r'\brm\s+.*-[a-z]*f[a-z]*r'),  # rm -fr variations
    re.compile(r'\brm\s+--recursive\s+--force'),
    re.compile(r'\brm\s+--force\s+--recursive'),
    re.compile(r'\brm\s+-r\s+.*-f'),
    re.compile(r'\brm\s+-f\s+.*-r'),
]

DANGEROUS_RM_PATH_PATTERNS = [
    re.compile(r'\s/$'),          # Root directory
    re.compile(r'\s/\*'),         # Root with wildcard
    re.compile(r'\s~/?'),         # Home directory
    re.compile(r'\s\$HOME'),      # Home environment variable
    re.compile(r'\s\.\./?'),      # Parent directory references
    re.compile(r'\s\.$'),         # Current directory
]

RM_RECURSIVE_PATTERN = re.compile(r'\brm\s+.*-[a-z]*r')

FORK_BOMB_PATTERNS = [
    re.compile(r':\(\)\s*\{\s*:\|:&\s*\}\s*;:'),  # Classic bash fork bomb
    re.compile(r'\.\/\w+\s*&\s*\.\/\w+'),  # Self-replicating pattern
    re.compile(r'while\s+true.*fork', re.IGNORECASE),
    re.compile(r'fork\s*\(\s*\)\s*while', re.IGNORECASE),
]

DANGEROUS_GIT_PATTERNS = [
    # Block ALL git push commands — push manually
    re.compile(r'git\s+push\b'),
    # Other dangerous commands
    re.compile(r'git\s+reset\s+--hard\s+origin/'),
    re.compile(r'git\s+clean\s+-fd'),  # Force delete untracked files
]

DANGEROUS_DISK_PATTERNS = [
    re.compile(r'\bdd\s+.*of=/dev/'),  # dd to device
    re.compile(r'\bmkfs\.'),  # Format filesystem
    re.compile(r'>\s*/dev/sd'),  # Write to disk device
]

ENV_ACCESS_PATTERNS = [
    re.compile(r'\bcat\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\bless\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\bhead\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\btail\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'>\s*[^\s]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\bcp\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\bmv\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\bsource\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),
    re.compile(r'\.\s+[^\|]*\.env\b(?!\.sample|\.example|\.template)'),  # . .env (source shorthand)
]

SENSITIVE_FILE_PATTERNS = [
    (re.compile(r'\.pem$'), 'PEM certificate/key file'),
    (re.compile(r'\.key$'), 'Key file'),
    (re.compile(r'\.p12$'), 'PKCS12 certificate'),
    (re.compile(r'\.pfx$'), 'PFX certificate'),
    (re.compile(r'credentials\.(json|yaml|yml|xml|ini|conf)$'), 'Credentials file'),
    (re.compile(r'secrets?\.(json|yaml|yml|xml|ini|conf)$'), 'Secrets file'),
    (re.compile(r'\.kube/config'), 'Kubernetes config'),
    (re.compile(r'\.aws/credentials'), 'AWS credentials'),
    (re.compile(r'\.ssh/'), 'SSH directory'),
    (re.compile(r'\.gnupg/'), 'GPG directory'),
    (re.compile(r'\.netrc'), 'Netrc file'),
    (re.compile(r'\.npmrc'), 'NPM config with tokens'),
    (re.compile(r'\.pypirc'), 'PyPI config with tokens'),
]

# Exact filename matches for sensitive files
SENSITIVE_FILES = {
    '.env',
    '.env.local',
    '.env.production',
    '.env.development',
    'id_rsa',
    'id_ed25519',
    'id_ecdsa',
    'id_dsa',
}

# Allowed .env variants
ALLOWED_ENV_FILES = {'.env.sample', '.env.example', '.env.template'}


def debug_log(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)


def is_dangerous_rm_command(command: str) -> bool:
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    """
    normalized = ' '.join(command.lower().split())

    # Check standard rm -rf variations
    for pattern in DANGEROUS_RM_PATTERNS:
        if pattern.search(normalized):
            debug_log(f"Matched dangerous rm pattern: {pattern.pattern}")
            return True

    # Check for rm with recursive flag targeting dangerous paths
    if RM_RECURSIVE_PATTERN.search(normalized):
        for pattern in DANGEROUS_RM_PATH_PATTERNS:
            if pattern.search(normalized):
                debug_log(f"Matched dangerous rm path pattern: {pattern.pattern}")
                return True

    return False


def is_fork_bomb(command: str) -> bool:
    """Detect fork bomb patterns."""
    for pattern in FORK_BOMB_PATTERNS:
        if pattern.search(command):
            debug_log(f"Matched fork bomb pattern: {pattern.pattern}")
            return True
    return False


def is_dangerous_git_command(command: str) -> bool:
    """Detect dangerous git commands."""
    normalized = ' '.join(command.lower().split())

    for pattern in DANGEROUS_GIT_PATTERNS:
        if pattern.search(normalized):
            debug_log(f"Matched dangerous git pattern: {pattern.pattern}")
            return True
    return False


def is_dangerous_disk_write(command: str) -> bool:
    """Detect dangerous disk write operations."""
    normalized = ' '.join(command.lower().split())

    for pattern in DANGEROUS_DISK_PATTERNS:
        if pattern.search(normalized):
            debug_log(f"Matched dangerous disk pattern: {pattern.pattern}")
            return True
    return False


def is_sensitive_file(file_path: str) -> tuple[bool, str | None]:
    """Check if file path points to sensitive files."""
    if not file_path:
        return False, None

    path_lower = file_path.lower()
    basename = os.path.basename(path_lower)

    # Allow .env.sample and .env.example
    if basename in ALLOWED_ENV_FILES:
        return False, None

    # Check exact filename matches
    if basename in SENSITIVE_FILES:
        debug_log(f"Matched sensitive file: {basename}")
        return True, f"Access to {basename} files is prohibited"

    # Check pattern matches
    for pattern, description in SENSITIVE_FILE_PATTERNS:
        if pattern.search(path_lower):
            debug_log(f"Matched sensitive file pattern: {pattern.pattern}")
            return True, f"Access to {description} is prohibited"

    return False, None


def is_path_escape(file_path: str, project_dir: str) -> tuple[bool, str | None]:
    """Check if path escapes the project directory."""
    if not file_path or not project_dir:
        return False, None

    try:
        # Resolve to absolute paths
        abs_path = Path(file_path).resolve()
        abs_project = Path(project_dir).resolve()

        # Check if path is within project (using proper prefix check)
        # CVE-2025-54794: Must check with trailing separator to prevent
        # /project matching /project_malicious
        project_str = str(abs_project)
        path_str = str(abs_path)

        if not (path_str == project_str or path_str.startswith(project_str + os.sep)):
            debug_log(f"Path escape detected: {path_str} not in {project_str}")
            return True, "Path is outside project directory"

        # Also check for .. in the original path (before resolution)
        if '..' in file_path:
            debug_log(f"Path traversal detected: {file_path}")
            return True, "Path traversal attempt detected"

    except (ValueError, OSError) as e:
        debug_log(f"Path resolution error: {e}")
        return True, "Invalid path"

    return False, None


def check_bash_command(command: str) -> str | None:
    """Check bash command for dangerous patterns."""
    if is_dangerous_rm_command(command):
        return "Dangerous rm command detected"

    if is_fork_bomb(command):
        return "Fork bomb detected"

    if is_dangerous_git_command(command):
        return "Git push is not allowed — push manually"

    if is_dangerous_disk_write(command):
        return "Dangerous disk write operation detected"

    # Check for .env access in bash commands
    for pattern in ENV_ACCESS_PATTERNS:
        if pattern.search(command):
            debug_log(f"Matched env access pattern: {pattern.pattern}")
            return "Access to .env files is prohibited"

    return None


def check_file_operation(tool_name: str, tool_input: dict, project_dir: str) -> str | None:
    """Check file operations for security issues."""
    file_path = tool_input.get('file_path', '')

    # For Grep, also check the path parameter
    if tool_name == 'Grep':
        file_path = tool_input.get('path', '') or file_path

    # For Glob, check the path parameter
    if tool_name == 'Glob':
        file_path = tool_input.get('path', '') or file_path

    if not file_path:
        return None

    # Check sensitive files
    is_sensitive, reason = is_sensitive_file(file_path)
    if is_sensitive:
        return reason

    # Check path escape (only for absolute paths or paths with ..)
    if os.path.isabs(file_path) or '..' in file_path:
        is_escape, reason = is_path_escape(file_path, project_dir)
        if is_escape:
            return reason

    return None


def check_bash_command_container(command: str) -> str | None:
    """Check bash command in container mode (only git and .env access)."""
    if is_dangerous_git_command(command):
        return "Git push is not allowed — push manually"

    # Check for .env access in bash commands
    for pattern in ENV_ACCESS_PATTERNS:
        if pattern.search(command):
            debug_log(f"Matched env access pattern: {pattern.pattern}")
            return "Access to .env files is prohibited"

    return None


def check_file_operation_container(tool_name: str, tool_input: dict) -> str | None:
    """Check file operations in container mode (only sensitive files, no path escape)."""
    file_path = tool_input.get('file_path', '')

    # For Grep, also check the path parameter
    if tool_name == 'Grep':
        file_path = tool_input.get('path', '') or file_path

    # For Glob, check the path parameter
    if tool_name == 'Glob':
        file_path = tool_input.get('path', '') or file_path

    if not file_path:
        return None

    # Check sensitive files only (no path escape check)
    is_sensitive, reason = is_sensitive_file(file_path)
    if is_sensitive:
        return reason

    return None


def main() -> None:
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        debug_log(f"Checking tool: {tool_name}")

        if CONTAINER_MODE:
            debug_log("Container mode - using relaxed security checks")

            # Container mode: only check git commands and sensitive file access
            if tool_name == 'Bash':
                command = tool_input.get('command', '')
                error = check_bash_command_container(command)
                if error:
                    print(f"BLOCKED: {error}", file=sys.stderr)
                    sys.exit(2)

            if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Glob', 'Grep']:
                error = check_file_operation_container(tool_name, tool_input)
                if error:
                    print(f"BLOCKED: {error}", file=sys.stderr)
                    sys.exit(2)

            sys.exit(0)

        # Full security checks (non-container mode)

        # Check bash commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            error = check_bash_command(command)
            if error:
                print(f"BLOCKED: {error}", file=sys.stderr)
                sys.exit(2)

        # Check file operations (including Glob and Grep)
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Glob', 'Grep']:
            error = check_file_operation(tool_name, tool_input, project_dir)
            if error:
                print(f"BLOCKED: {error}", file=sys.stderr)
                sys.exit(2)

        sys.exit(0)

    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(0)
    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        sys.exit(0)


if __name__ == '__main__':
    main()
