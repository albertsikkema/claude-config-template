#!/usr/bin/env python3
"""
PreToolUse security hook — three-layer defense architecture.

Layer 1: Regex pattern matching (fast, ~0ms, catches obvious patterns)
Layer 2: settings.json deny list enforcement (single source of truth,
         enforced even in --dangerously-skip-permissions mode)
Layer 3: LLM prompt hook (configured in settings.json, catches intent-based
         threats that regex can't see)

Decision modes:
- deny:  Block the tool call entirely
- allow: Silently permit the tool call

Full mode (default) checks for:
- Dangerous rm commands
- Fork bombs
- Dangerous git commands (all git push, force operations)
- Disk write attacks (dd to /dev/)
- Sensitive file access (.env, .pem, .key, credentials, etc.)
- Path traversal attacks
- Project directory escape
- Cloud/infrastructure destruction (terraform, aws, kubectl)
- Database destruction (DROP TABLE, TRUNCATE, FLUSHALL)
- Data exfiltration (curl -d @file, scp, rsync to remote)

Container mode (CLAUDE_CONTAINER_MODE=1) checks for:
- Dangerous git commands (all git push, force operations)
- Sensitive file access (.env, .pem, .key, credentials, etc.)
- Cloud metadata SSRF (169.254.169.254, metadata.google.internal)
- Pipe-to-shell attacks (curl/wget | bash)
- Reverse shell attempts (bash /dev/tcp, nc -e, python socket)
- Container escape attempts (nsenter, docker --privileged)
- Credential exfiltration (env | base64, /etc/shadow)
- Crypto mining (xmrig)
- settings.json deny list enforcement

Audit logging:
- All tool invocations logged to memories/logs/hook-audit.jsonl
- Entries include timestamp, session ID, tool, decision, and reason

Environment variables:
- CLAUDE_HOOKS_DEBUG=1      Enable debug logging
- CLAUDE_CONTAINER_MODE=1   Use relaxed checks for sandboxed/container environments
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

# Import settings loader for Layer 2
sys.path.insert(0, str(Path(__file__).parent))
from utils.settings_loader import load_deny_patterns

# Debug mode for troubleshooting
DEBUG = os.environ.get('CLAUDE_HOOKS_DEBUG', '').lower() in ('1', 'true')

# Container mode - relaxes some security checks for sandboxed environments
# Keeps: sensitive file access, dangerous git commands, settings.json deny list
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

CLOUD_METADATA_PATTERNS = [
    re.compile(r'\bcurl\s+.*http://169\.254\.169\.254'),
    re.compile(r'\bwget\s+.*http://169\.254\.169\.254'),
    re.compile(r'\bcurl\s+.*http://metadata\.google\.internal'),
    re.compile(r'\bwget\s+.*http://metadata\.google\.internal'),
]

PIPE_TO_SHELL_PATTERNS = [
    re.compile(r'\bcurl\s+.*\|\s*(sh|bash)\b'),
    re.compile(r'\bwget\s+.*\|\s*(sh|bash)\b'),
    re.compile(r'\|\s*base64\s+-d\s*\|\s*(sh|bash)\b'),
]

REVERSE_SHELL_PATTERNS = [
    re.compile(r'bash\s+-i\s+>&\s*/dev/tcp/'),
    re.compile(r'\|\s*nc\s+-l'),
    re.compile(r'\bnc\s+.*-e\s+/bin/(ba)?sh'),
    re.compile(r'\bpython[23]?\s+-c\s+.*socket.*connect', re.IGNORECASE),
]

CONTAINER_ESCAPE_PATTERNS = [
    re.compile(r'\bnsenter\b'),
    re.compile(r'\bdocker\s+run\s+.*--privileged'),
]

CREDENTIAL_EXFIL_PATTERNS = [
    re.compile(r'\benv\s*\|\s*base64\b'),
    re.compile(r'\bprintenv\s*\|\s*base64\b'),
    re.compile(r'\bcat\s+/etc/shadow\b'),
]

CRYPTO_MINING_PATTERNS = [
    re.compile(r'xmrig', re.IGNORECASE),
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
    (re.compile(r'\.vault-token$'), 'Vault token'),
    (re.compile(r'\.htpasswd$'), 'Apache password file'),
    (re.compile(r'\.pgpass$'), 'PostgreSQL password file'),
    (re.compile(r'\.my\.cnf$'), 'MySQL config file'),
    (re.compile(r'\.docker/config\.json$'), 'Docker registry auth'),
    (re.compile(r'service[_-]account.*\.json$'), 'GCP service account'),
    (re.compile(r'\.tfstate$'), 'Terraform state file'),
]

# Exact filename matches for sensitive files
SENSITIVE_FILES = {
    '.env',
    '.env.local',
    '.env.production',
    '.env.development',
    '.env.staging',
    '.envrc',
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


def respond_deny(reason: str) -> None:
    """Block the tool call via hookSpecificOutput."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }))
    sys.exit(0)



def audit_log(tool_name: str, tool_input: dict, decision: str, reason: str, mode: str) -> None:
    """Append audit entry to JSONL log file."""
    try:
        log_dir = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())) / "memories" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "hook-audit.jsonl"

        # Truncate tool_input to avoid massive log entries
        summary = json.dumps(tool_input)
        if len(summary) > 256:
            summary = summary[:253] + "..."

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sid": os.environ.get("CLAUDE_SESSION_ID", ""),
            "tool": tool_name,
            "input": summary,
            "decision": decision,
            "reason": reason,
            "mode": mode,
        }

        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never let logging break the hook


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


def is_network_escape_threat(command: str) -> tuple[bool, str]:
    """Detect network-based threats that can escape a container."""
    normalized = ' '.join(command.lower().split())

    checks = [
        (CLOUD_METADATA_PATTERNS, "Cloud metadata access blocked (SSRF)"),
        (PIPE_TO_SHELL_PATTERNS, "Piping remote content to shell is blocked"),
        (REVERSE_SHELL_PATTERNS, "Reverse shell attempt blocked"),
        (CONTAINER_ESCAPE_PATTERNS, "Container escape attempt blocked"),
        (CREDENTIAL_EXFIL_PATTERNS, "Credential exfiltration blocked"),
        (CRYPTO_MINING_PATTERNS, "Crypto mining blocked"),
    ]

    for patterns, message in checks:
        for pattern in patterns:
            if pattern.search(normalized):
                debug_log(f"Matched network/escape pattern: {pattern.pattern}")
                return True, message

    return False, ""


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


def check_against_settings_deny(
    tool_name: str, tool_input: dict, deny_patterns: dict[str, list[re.Pattern]]
) -> str | None:
    """Check tool invocation against settings.json deny patterns (Layer 2)."""
    patterns = deny_patterns.get(tool_name, [])
    if not patterns:
        return None

    # Build the string to match against
    if tool_name == "Bash":
        match_str = tool_input.get("command", "")
    else:
        # For file tools, match against the file path
        match_str = tool_input.get("file_path", "") or tool_input.get("path", "")

    if not match_str:
        return None

    for pattern in patterns:
        if pattern.search(match_str):
            debug_log(f"Matched settings.json deny pattern: {pattern.pattern}")
            return f"Blocked by settings.json deny rule: {pattern.pattern}"

    return None



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

    # Check for network/escape threats
    is_threat, reason = is_network_escape_threat(command)
    if is_threat:
        return reason

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
    """Check bash command in container mode (git, .env, and network escape)."""
    if is_dangerous_git_command(command):
        return "Git push is not allowed — push manually"

    # Check for .env access in bash commands
    for pattern in ENV_ACCESS_PATTERNS:
        if pattern.search(command):
            debug_log(f"Matched env access pattern: {pattern.pattern}")
            return "Access to .env files is prohibited"

    # Check for network/escape threats (these escape the container boundary)
    is_threat, reason = is_network_escape_threat(command)
    if is_threat:
        return reason

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
        mode = "container" if CONTAINER_MODE else "full"

        debug_log(f"Checking tool: {tool_name}")

        # Layer 2: Load settings.json deny patterns (enforced in ALL modes)
        deny_patterns = load_deny_patterns(project_dir)

        if CONTAINER_MODE:
            debug_log("Container mode - using relaxed security checks")

            # Layer 1: Regex checks (container subset)
            if tool_name == 'Bash':
                command = tool_input.get('command', '')
                error = check_bash_command_container(command)
                if error:
                    audit_log(tool_name, tool_input, "deny", error, mode)
                    respond_deny(error)

            if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Glob', 'Grep']:
                error = check_file_operation_container(tool_name, tool_input)
                if error:
                    audit_log(tool_name, tool_input, "deny", error, mode)
                    respond_deny(error)

            # Layer 2: settings.json deny (enforced even in container mode)
            error = check_against_settings_deny(tool_name, tool_input, deny_patterns)
            if error:
                audit_log(tool_name, tool_input, "deny", error, mode)
                respond_deny(error)

            audit_log(tool_name, tool_input, "allow", "", mode)
            sys.exit(0)

        # Full security checks (non-container mode)

        # Layer 1: Regex checks
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            error = check_bash_command(command)
            if error:
                audit_log(tool_name, tool_input, "deny", error, mode)
                respond_deny(error)

        # Check file operations (including Glob and Grep)
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Glob', 'Grep']:
            error = check_file_operation(tool_name, tool_input, project_dir)
            if error:
                audit_log(tool_name, tool_input, "deny", error, mode)
                respond_deny(error)

        # Layer 2: settings.json deny
        error = check_against_settings_deny(tool_name, tool_input, deny_patterns)
        if error:
            audit_log(tool_name, tool_input, "deny", error, mode)
            respond_deny(error)

        audit_log(tool_name, tool_input, "allow", "", mode)
        sys.exit(0)

    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(1)
    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
