#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "colorama>=0.4.6",
# ]
# ///
"""
PR Review Orchestrator: Automated GitHub PR review workflow

Workflow:
    1. Validate clean git status
    2. Fetch PR details and comments
    3. Checkout PR branch
    4. Index codebase
    5. Fetch technical docs for changed packages
    6. Run interactive /review_pr

Usage:
    uv run .claude/helpers/pr_reviewer.py 123                    # PR by number
    uv run .claude/helpers/pr_reviewer.py https://github.com/.../pull/123  # PR by URL
    uv run .claude/helpers/pr_reviewer.py --skip-docs 123        # Skip documentation fetch
    uv run .claude/helpers/pr_reviewer.py --skip-index 123       # Skip codebase indexing
"""

from __future__ import annotations

import argparse
import json
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from colorama import Fore, Style, init

# Initialize colorama
init()

# Color mapping for stages
STAGE_COLORS = {
    'Validate': Fore.CYAN,
    'Fetch PR': Fore.YELLOW,
    'Checkout': Fore.MAGENTA,
    'Install': Fore.BLUE,
    'Tests': Fore.BLUE,
    'Indexing': Fore.CYAN,
    'Docs': Fore.CYAN,
    'Review': Fore.GREEN,
}


# --- Result dataclasses ---

@dataclass
class PRInfo:
    """Information about the PR being reviewed."""
    number: int
    title: str
    author: str
    base_branch: str
    head_branch: str
    url: str
    body: str
    changed_files: list[str]
    additions: int
    deletions: int


@dataclass
class PRComment:
    """A comment on the PR."""
    author: str
    body: str
    path: str | None  # File path for review comments
    line: int | None  # Line number for review comments


@dataclass
class PRReviewResult:
    """Result from the PR review process."""
    pr_number: int
    pr_title: str
    packages_fetched: list[str]
    review_complete: bool


# --- Utility functions ---

def print_phase_header(phase_name: str) -> None:
    """Print a prominent phase header with separators."""
    color = STAGE_COLORS.get(phase_name, Fore.WHITE)
    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}", file=sys.stderr, flush=True)
    print(f"\n{color}Phase: {phase_name}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)
    print(f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)


def stream_progress(stage: str, message: str) -> None:
    """Print progress update to stderr for real-time feedback."""
    color = STAGE_COLORS.get(stage, Fore.WHITE)
    if 'FAILED' in message or 'Error' in message:
        color = Fore.RED
    elif 'Complete' in message or 'OK' in message:
        color = Fore.GREEN
    elif 'Warning' in message or 'Skipped' in message:
        color = Fore.YELLOW
    print(f"{color}[{stage}]{Style.RESET_ALL} {message}", file=sys.stderr, flush=True)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def format_stream_event(line: str) -> str | None:
    """Parse a stream-json line and return a human-readable string, or None to skip."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return line.strip() if line.strip() else None

    event_type = event.get('type')

    # Skip init events (too verbose)
    if event_type == 'system' and event.get('subtype') == 'init':
        return None

    # Assistant messages - extract text and tool calls
    if event_type == 'assistant':
        message = event.get('message', {})
        content = message.get('content', [])
        parts = []
        for item in content:
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    parts.append(f"\n{Fore.WHITE}{text}{Style.RESET_ALL}\n")
            elif item.get('type') == 'tool_use':
                tool_name = item.get('name', 'unknown')
                tool_input = item.get('input', {})
                if isinstance(tool_input, dict):
                    input_parts = []
                    for k, v in list(tool_input.items())[:3]:
                        v_str = str(v)
                        max_len = 80 if k in ('file_path', 'path', 'pattern') else 50
                        if len(v_str) > max_len:
                            v_str = v_str[:max_len] + '...'
                        input_parts.append(f"{k}={v_str}")
                    input_summary = ', '.join(input_parts)
                else:
                    input_summary = str(tool_input)[:100]
                parts.append(f"  {Fore.CYAN}→ {tool_name}{Style.RESET_ALL}({input_summary})")
        return '\n'.join(parts) if parts else None

    # Tool results - show abbreviated
    if event_type == 'user':
        content = event.get('message', {}).get('content', [])
        for item in content:
            if item.get('type') == 'tool_result':
                result = str(item.get('content', ''))
                lines = result.split('\n')[:2]
                preview = ' | '.join(line.strip() for line in lines if line.strip())[:150]
                if preview:
                    suffix = '...' if len(result) > 150 else ''
                    return f"  {Fore.YELLOW}← {preview}{suffix}{Style.RESET_ALL}"
        return None

    # Result event (final output)
    if event_type == 'result':
        return f"\n{Fore.GREEN}✓ Done{Style.RESET_ALL}\n"

    return None


# --- Git and gh CLI functions ---

def check_git_status_clean(project_path: str) -> bool:
    """Check if git working directory is clean."""
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    return result.returncode == 0 and not result.stdout.strip()


def get_current_branch(project_path: str) -> str | None:
    """Get the current git branch name."""
    result = subprocess.run(
        ['git', 'branch', '--show-current'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def check_gh_cli() -> tuple[bool, str]:
    """Verify gh CLI is installed and authenticated.

    Returns:
        Tuple of (success, error_message)
    """
    # Check if gh is installed
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except FileNotFoundError:
        return False, "gh CLI is not installed. Install it from https://cli.github.com/"
    except subprocess.CalledProcessError:
        return False, "gh CLI check failed"

    # Check if authenticated
    result = subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True)
    if result.returncode != 0:
        return False, "gh CLI is not authenticated. Run 'gh auth login' to authenticate."

    return True, ""


def parse_pr_input(input_str: str) -> int:
    """Parse PR number from number or GitHub URL.

    Args:
        input_str: PR number (e.g., "123") or URL (e.g., "https://github.com/owner/repo/pull/123")

    Returns:
        PR number as integer

    Raises:
        ValueError: If input cannot be parsed as a PR reference
    """
    # Try direct number
    try:
        return int(input_str)
    except ValueError:
        pass

    # Try URL pattern
    match = re.search(r'/pull/(\d+)', input_str)
    if match:
        return int(match.group(1))

    raise ValueError(f"Cannot parse PR reference: {input_str}")


def fetch_pr_info(pr_number: int, project_path: str) -> PRInfo | None:
    """Fetch PR details using gh CLI."""
    result = subprocess.run(
        ['gh', 'pr', 'view', str(pr_number), '--json',
         'number,title,author,baseRefName,headRefName,url,body,files,additions,deletions'],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
        return PRInfo(
            number=data.get('number', pr_number),
            title=data.get('title', ''),
            author=data.get('author', {}).get('login', 'unknown'),
            base_branch=data.get('baseRefName', 'main'),
            head_branch=data.get('headRefName', ''),
            url=data.get('url', ''),
            body=data.get('body', ''),
            changed_files=[f.get('path', '') for f in data.get('files', [])],
            additions=data.get('additions', 0),
            deletions=data.get('deletions', 0)
        )
    except (json.JSONDecodeError, KeyError):
        return None


def fetch_pr_comments(pr_number: int, project_path: str) -> list[PRComment]:
    """Fetch PR comments using gh API."""
    comments = []

    # Get review comments (on specific lines)
    result = subprocess.run(
        ['gh', 'api', f'repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments'],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            for comment in data:
                comments.append(PRComment(
                    author=comment.get('user', {}).get('login', 'unknown'),
                    body=comment.get('body', ''),
                    path=comment.get('path'),
                    line=comment.get('line')
                ))
        except json.JSONDecodeError:
            pass

    # Get issue comments (general PR comments)
    result = subprocess.run(
        ['gh', 'api', f'repos/{{owner}}/{{repo}}/issues/{pr_number}/comments'],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            for comment in data:
                comments.append(PRComment(
                    author=comment.get('user', {}).get('login', 'unknown'),
                    body=comment.get('body', ''),
                    path=None,
                    line=None
                ))
        except json.JSONDecodeError:
            pass

    return comments


def checkout_pr_branch(pr_number: int, project_path: str) -> tuple[str | None, str | None]:
    """Checkout the PR branch.

    Returns:
        Tuple of (original_branch, pr_branch) or (None, None) on failure
    """
    original_branch = get_current_branch(project_path)

    result = subprocess.run(
        ['gh', 'pr', 'checkout', str(pr_number)],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None, None

    pr_branch = get_current_branch(project_path)
    return original_branch, pr_branch


def restore_branch(branch: str, project_path: str) -> bool:
    """Restore to a specific branch."""
    result = subprocess.run(
        ['git', 'checkout', branch],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    return result.returncode == 0


# --- Package detection ---

def load_project_packages(project_path: str) -> set[str]:
    """Load all project packages using fetch-docs.py discover."""
    fetch_docs_path = Path(project_path) / '.claude' / 'helpers' / 'fetch-docs.py'

    if not fetch_docs_path.exists():
        return set()

    result = subprocess.run(
        ['python3', str(fetch_docs_path), 'discover'],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return set()

    try:
        data = json.loads(result.stdout)
        return set(data.get('packages', {}).keys())
    except json.JSONDecodeError:
        return set()


def parse_python_imports(file_path: Path) -> set[str]:
    """Parse import statements from Python file."""
    imports = set()
    try:
        content = file_path.read_text(encoding='utf-8')
    except (IOError, UnicodeDecodeError):
        return imports

    # Match: import foo, from foo import bar, from foo.bar import baz
    import_re = re.compile(r'^(?:from\s+(\S+)|import\s+(\S+))', re.MULTILINE)
    for match in import_re.finditer(content):
        module = match.group(1) or match.group(2)
        if module:
            # Get top-level package name
            top_level = module.split('.')[0]
            imports.add(top_level)

    return imports


def parse_js_ts_imports(file_path: Path) -> set[str]:
    """Parse import/require statements from JS/TS file."""
    imports = set()
    try:
        content = file_path.read_text(encoding='utf-8')
    except (IOError, UnicodeDecodeError):
        return imports

    # Match: import ... from 'package', require('package')
    import_re = re.compile(r'''(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))''')
    for match in import_re.finditer(content):
        module = match.group(1) or match.group(2)
        if module and not module.startswith('.'):
            # Handle scoped packages (@scope/package)
            if module.startswith('@'):
                parts = module.split('/')
                if len(parts) >= 2:
                    imports.add(f"{parts[0]}/{parts[1]}")
            else:
                imports.add(module.split('/')[0])

    return imports


def parse_go_imports(file_path: Path) -> set[str]:
    """Parse import statements from Go file."""
    imports = set()
    try:
        content = file_path.read_text(encoding='utf-8')
    except (IOError, UnicodeDecodeError):
        return imports

    # Match import blocks and single imports
    import_re = re.compile(r'"([^"]+)"')
    for match in import_re.finditer(content):
        module = match.group(1)
        # Get last path component as package name (simplified)
        parts = module.split('/')
        if len(parts) > 0:
            imports.add(parts[-1])

    return imports


def detect_packages_in_changed_files(changed_files: list[str], project_path: str) -> list[str]:
    """Detect which packages are used in the changed files."""
    # Load project dependencies
    project_packages = load_project_packages(project_path)
    if not project_packages:
        return []

    # Parse imports from each changed file
    all_imports: set[str] = set()
    for file_path in changed_files:
        full_path = Path(project_path) / file_path
        if not full_path.exists():
            continue

        ext = full_path.suffix.lower()
        if ext == '.py':
            imports = parse_python_imports(full_path)
        elif ext in ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'):
            imports = parse_js_ts_imports(full_path)
        elif ext == '.go':
            imports = parse_go_imports(full_path)
        else:
            continue
        all_imports.update(imports)

    # Match imports to project packages
    matched_packages = []
    for pkg_name in project_packages:
        # Check if any import matches this package
        pkg_lower = pkg_name.lower()
        for imp in all_imports:
            if imp.lower() == pkg_lower or pkg_lower in imp.lower():
                matched_packages.append(pkg_name)
                break

    return matched_packages


# --- Dependency installation and test execution ---

def detect_install_command(project_path: str) -> tuple[str | None, str]:
    """Detect the appropriate dependency install command for the project.

    Returns:
        Tuple of (command, description) or (None, reason) if no install needed
    """
    project = Path(project_path)

    # Python: uv, poetry, or pip
    if (project / 'pyproject.toml').exists():
        # Check for uv.lock (uv project)
        if (project / 'uv.lock').exists():
            return 'uv sync', 'Python (uv)'
        # Check for poetry.lock
        if (project / 'poetry.lock').exists():
            return 'poetry install', 'Python (poetry)'
        # Fallback to pip
        return 'pip install -e .', 'Python (pip)'

    if (project / 'requirements.txt').exists():
        return 'pip install -r requirements.txt', 'Python (pip)'

    # JavaScript/TypeScript: npm, yarn, or pnpm
    package_json = project / 'package.json'
    if package_json.exists():
        if (project / 'pnpm-lock.yaml').exists():
            return 'pnpm install', 'JavaScript/TypeScript (pnpm)'
        if (project / 'yarn.lock').exists():
            return 'yarn install', 'JavaScript/TypeScript (yarn)'
        if (project / 'package-lock.json').exists() or (project / 'npm-shrinkwrap.json').exists():
            return 'npm ci', 'JavaScript/TypeScript (npm ci)'
        return 'npm install', 'JavaScript/TypeScript (npm)'

    # Go: go mod download
    if (project / 'go.mod').exists():
        return 'go mod download', 'Go'

    # Rust: cargo build (fetches deps)
    if (project / 'Cargo.toml').exists():
        return 'cargo build', 'Rust'

    return None, 'No dependency configuration detected'


def install_dependencies(project_path: str) -> tuple[bool, str, float]:
    """Install dependencies for the project.

    Returns:
        Tuple of (success, output_summary, elapsed_seconds)
    """
    install_cmd, description = detect_install_command(project_path)

    if not install_cmd:
        return True, f"Skipped: {description}", 0.0

    stream_progress('Install', f'Running {description}...')

    start_time = time.time()
    result = subprocess.run(
        install_cmd,
        shell=True,
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=600  # 10 minute timeout
    )
    elapsed = time.time() - start_time

    output = result.stdout + result.stderr

    if result.returncode != 0:
        # Get last 20 lines for error context
        lines = output.strip().split('\n')
        summary = '\n'.join(lines[-20:]) if len(lines) > 20 else output
        return False, summary, elapsed

    return True, f"Dependencies installed ({format_duration(elapsed)})", elapsed


def detect_test_command(project_path: str) -> tuple[str | None, str]:
    """Detect the appropriate test command for the project.

    Returns:
        Tuple of (command, description) or (None, reason) if no tests detected
    """
    project = Path(project_path)

    # Python: pytest or unittest
    if (project / 'pyproject.toml').exists() or (project / 'setup.py').exists():
        if (project / 'pytest.ini').exists() or (project / 'pyproject.toml').exists():
            return 'pytest', 'Python (pytest)'
        return 'python -m unittest discover', 'Python (unittest)'

    # JavaScript/TypeScript: check package.json for test script
    package_json = project / 'package.json'
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding='utf-8'))
            scripts = data.get('scripts', {})
            if 'test' in scripts:
                return 'npm test', 'JavaScript/TypeScript (npm test)'
        except (json.JSONDecodeError, IOError):
            pass

    # Go
    if (project / 'go.mod').exists():
        return 'go test ./...', 'Go'

    # Rust
    if (project / 'Cargo.toml').exists():
        return 'cargo test', 'Rust'

    return None, 'No test configuration detected'


def run_tests(project_path: str) -> tuple[bool, str, float]:
    """Run tests for the project.

    Returns:
        Tuple of (success, output_summary, elapsed_seconds)
    """
    test_cmd, description = detect_test_command(project_path)

    if not test_cmd:
        return True, f"Skipped: {description}", 0.0

    stream_progress('Tests', f'Running {description}...')

    start_time = time.time()
    result = subprocess.run(
        test_cmd,
        shell=True,
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=600  # 10 minute timeout
    )
    elapsed = time.time() - start_time

    # Combine stdout and stderr for output
    output = result.stdout + result.stderr

    # Get summary (last few lines usually have test results)
    lines = output.strip().split('\n')
    summary_lines = lines[-10:] if len(lines) > 10 else lines
    summary = '\n'.join(summary_lines)

    return result.returncode == 0, summary, elapsed


# --- Claude command execution ---

def run_claude_command(command: list[str], cwd: str, timeout: int = 600, phase: str = '') -> tuple[int, str, float]:
    """Run a Claude Code command with real-time output streaming.

    Returns:
        Tuple of (return_code, captured_output, elapsed_seconds)
    """
    command = command.copy()
    command.insert(1, '--verbose')
    command.insert(2, '--output-format')
    command.insert(3, 'stream-json')

    if phase:
        print_phase_header(phase)

    start_time = time.time()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output_lines = []
    try:
        if process.stdout:
            for line in process.stdout:
                output_lines.append(line)
                formatted = format_stream_event(line)
                if formatted:
                    print(formatted, file=sys.stderr, flush=True)

        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        elapsed = time.time() - start_time
        raise RuntimeError(f"Command timed out after {format_duration(elapsed)}")

    elapsed = time.time() - start_time
    returncode = process.returncode if process.returncode is not None else 1
    return returncode, ''.join(output_lines), elapsed


def run_claude_interactive(initial_message: str, cwd: str, phase: str = '') -> tuple[int, float]:
    """Run Claude interactively with an initial message.

    Returns:
        Tuple of (return_code, elapsed_seconds)
    """
    if phase:
        print_phase_header(phase)

    start_time = time.time()
    process = subprocess.run(
        ['claude', '--dangerously-skip-permissions', initial_message],
        cwd=cwd,
    )
    elapsed = time.time() - start_time
    return process.returncode, elapsed


# --- Main orchestration ---

def run_pr_review(pr_ref: str, project_path: str, skip_tests: bool = False, skip_index: bool = False, skip_docs: bool = False) -> PRReviewResult:
    """Run the full PR review workflow."""
    original_branch: str | None = None

    try:
        # Phase 1: Validate
        print_phase_header('Validate')

        # Check git status
        if not check_git_status_clean(project_path):
            stream_progress('Validate', 'Error: Git working directory is not clean')
            print(f"\n{Fore.RED}Please commit or stash your changes before reviewing a PR.{Style.RESET_ALL}", file=sys.stderr)
            print("Run 'git status' to see uncommitted changes.", file=sys.stderr)
            raise RuntimeError("Dirty git working directory")
        stream_progress('Validate', 'Git status: clean')

        # Check gh CLI
        gh_ok, gh_error = check_gh_cli()
        if not gh_ok:
            stream_progress('Validate', f'Error: {gh_error}')
            raise RuntimeError(gh_error)
        stream_progress('Validate', 'gh CLI: OK')

        # Parse PR reference
        try:
            pr_number = parse_pr_input(pr_ref)
        except ValueError as e:
            stream_progress('Validate', f'Error: {e}')
            raise RuntimeError(str(e))
        stream_progress('Validate', f'PR number: #{pr_number}')

        # Phase 2: Fetch PR
        print_phase_header('Fetch PR')

        pr_info = fetch_pr_info(pr_number, project_path)
        if not pr_info:
            stream_progress('Fetch PR', f'Error: PR #{pr_number} not found')
            raise RuntimeError(f"PR #{pr_number} not found. Check that the PR exists and you have access.")
        stream_progress('Fetch PR', f'Title: {pr_info.title}')
        stream_progress('Fetch PR', f'Author: {pr_info.author}')
        stream_progress('Fetch PR', f'Branch: {pr_info.head_branch} → {pr_info.base_branch}')
        stream_progress('Fetch PR', f'Changed files: {len(pr_info.changed_files)} (+{pr_info.additions}/-{pr_info.deletions})')

        comments = fetch_pr_comments(pr_number, project_path)
        stream_progress('Fetch PR', f'Comments: {len(comments)}')

        # Phase 3: Checkout
        print_phase_header('Checkout')

        original_branch, pr_branch = checkout_pr_branch(pr_number, project_path)
        if not original_branch or not pr_branch:
            stream_progress('Checkout', 'Error: Failed to checkout PR branch')
            raise RuntimeError("Failed to checkout PR branch")
        stream_progress('Checkout', f'Switched from {original_branch} to {pr_branch}')

        # Phase 4: Install dependencies
        if skip_tests:
            stream_progress('Install', 'Skipped (--skip-tests)')
        else:
            print_phase_header('Install')
            install_success, install_output, install_elapsed = install_dependencies(project_path)

            if install_success:
                stream_progress('Install', f'Complete ({format_duration(install_elapsed)})')
            else:
                stream_progress('Install', f'FAILED ({format_duration(install_elapsed)})')
                print(f"\n{Fore.RED}Install output:{Style.RESET_ALL}", file=sys.stderr)
                print(install_output, file=sys.stderr)
                print(f"\n{Fore.RED}Aborting PR review: dependency installation failed.{Style.RESET_ALL}", file=sys.stderr)
                raise RuntimeError("Dependency installation failed - aborting review")

        # Phase 5: Run tests
        test_results: str = ""
        if skip_tests:
            stream_progress('Tests', 'Skipped (--skip-tests)')
            test_results = "Tests were skipped (--skip-tests flag used)"
        else:
            print_phase_header('Tests')
            test_success, test_output, test_elapsed = run_tests(project_path)

            if test_success:
                stream_progress('Tests', f'Passed ({format_duration(test_elapsed)})')
                test_results = f"All tests passed ({format_duration(test_elapsed)})\n\n{test_output}"
            else:
                stream_progress('Tests', f'FAILED ({format_duration(test_elapsed)})')
                print(f"\n{Fore.RED}Test output:{Style.RESET_ALL}", file=sys.stderr)
                print(test_output, file=sys.stderr)
                print(f"\n{Fore.RED}Aborting PR review: tests must pass before review.{Style.RESET_ALL}", file=sys.stderr)
                print(f"{Fore.YELLOW}Use --skip-tests to bypass (not recommended).{Style.RESET_ALL}", file=sys.stderr)
                raise RuntimeError("Tests failed - aborting review")

        # Phase 6: Index codebase
        packages_fetched: list[str] = []
        if skip_index:
            stream_progress('Indexing', 'Skipped (--skip-index)')
        else:
            returncode, output, elapsed = run_claude_command(
                ['claude', '--dangerously-skip-permissions', '-p', '/index_codebase'],
                cwd=project_path,
                timeout=600,
                phase='Indexing'
            )
            if returncode != 0:
                stream_progress('Indexing', f'Warning: Indexing failed (code {returncode}), continuing...')
            else:
                stream_progress('Indexing', f'Complete ({format_duration(elapsed)})')

        # Phase 7: Fetch technical docs
        if skip_docs:
            stream_progress('Docs', 'Skipped (--skip-docs)')
        else:
            print_phase_header('Docs')
            packages = detect_packages_in_changed_files(pr_info.changed_files, project_path)
            if packages:
                stream_progress('Docs', f'Detected packages in changed files: {", ".join(packages)}')
                # Pass packages to fetch_technical_docs
                quoted_pkgs = [f"'{pkg}'" if ' ' in pkg else pkg for pkg in packages]
                docs_prompt = f"/fetch_technical_docs {' '.join(quoted_pkgs)}"
                returncode, output, elapsed = run_claude_command(
                    ['claude', '--dangerously-skip-permissions', '-p', docs_prompt],
                    cwd=project_path,
                    timeout=600
                )
                if returncode != 0:
                    stream_progress('Docs', f'Warning: Docs fetch failed (code {returncode}), continuing...')
                else:
                    packages_fetched = packages
                    stream_progress('Docs', f'Complete ({format_duration(elapsed)})')
            else:
                stream_progress('Docs', 'No packages detected in changed files, skipping')

        # Phase 8: Interactive review
        # Build context for the review
        context = build_review_context(pr_info, comments, test_results)

        review_prompt = f"""/review_pr

{context}"""

        returncode, elapsed = run_claude_interactive(
            review_prompt,
            cwd=project_path,
            phase='Review'
        )

        stream_progress('Review', f'Complete ({format_duration(elapsed)})')

        return PRReviewResult(
            pr_number=pr_info.number,
            pr_title=pr_info.title,
            packages_fetched=packages_fetched,
            review_complete=returncode == 0
        )

    finally:
        # Always restore original branch
        if original_branch:
            print(f"\n{Fore.CYAN}Restoring original branch: {original_branch}{Style.RESET_ALL}", file=sys.stderr)
            if restore_branch(original_branch, project_path):
                print(f"{Fore.GREEN}✓ Restored to {original_branch}{Style.RESET_ALL}", file=sys.stderr)
            else:
                print(f"{Fore.RED}Warning: Failed to restore branch {original_branch}{Style.RESET_ALL}", file=sys.stderr)


def build_review_context(pr_info: PRInfo, comments: list[PRComment], test_results: str) -> str:
    """Build context string for the review command."""
    lines = [
        "## PR Information",
        "",
        f"**PR Number**: #{pr_info.number}",
        f"**Title**: {pr_info.title}",
        f"**Author**: {pr_info.author}",
        f"**URL**: {pr_info.url}",
        f"**Branch**: {pr_info.head_branch} → {pr_info.base_branch}",
        f"**Changes**: +{pr_info.additions}/-{pr_info.deletions} in {len(pr_info.changed_files)} files",
        "",
    ]

    if pr_info.body:
        lines.extend([
            "### Description",
            "",
            pr_info.body,
            "",
        ])

    lines.extend([
        "### Changed Files",
        "",
    ])
    for f in pr_info.changed_files:
        lines.append(f"- `{f}`")
    lines.append("")

    lines.extend([
        "### Test Results",
        "",
        test_results,
        "",
    ])

    if comments:
        lines.extend([
            "### Existing Comments",
            "",
        ])
        for comment in comments[:10]:  # Limit to first 10 comments
            if comment.path:
                lines.append(f"**{comment.author}** on `{comment.path}:{comment.line}`:")
            else:
                lines.append(f"**{comment.author}**:")
            # Truncate long comments
            body = comment.body[:500] + '...' if len(comment.body) > 500 else comment.body
            lines.append(f"> {body}")
            lines.append("")

    return '\n'.join(lines)


# --- Main entry point ---

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='GitHub PR Review Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 123                              # Review PR #123
  %(prog)s https://github.com/.../pull/123  # Review by URL
  %(prog)s --skip-tests 123                 # Skip running tests
  %(prog)s --skip-docs 123                  # Skip documentation fetch
  %(prog)s --skip-index 123                 # Skip codebase indexing
        """
    )
    parser.add_argument('pr_ref', help='PR number or GitHub URL')
    parser.add_argument('--project', default='.', help='Project directory path')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running tests (not recommended)')
    parser.add_argument('--skip-docs', action='store_true', help='Skip fetching technical docs')
    parser.add_argument('--skip-index', action='store_true', help='Skip codebase indexing')

    args = parser.parse_args()

    # Handle signals for graceful shutdown
    def handle_signal(signum, frame):
        sig_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
        exit_code = 143 if signum == signal.SIGTERM else 130
        print(f"\n{sig_name} received, shutting down...", file=sys.stderr)
        sys.exit(exit_code)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        total_start = time.time()

        result = run_pr_review(
            args.pr_ref,
            args.project,
            skip_tests=args.skip_tests,
            skip_index=args.skip_index,
            skip_docs=args.skip_docs
        )

        total_elapsed = time.time() - total_start

        # Print summary
        print(f"\n{Fore.GREEN}{Style.BRIGHT}PR Review Complete:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}PR:{Style.RESET_ALL} #{result.pr_number} - {result.pr_title}")
        if result.packages_fetched:
            print(f"  {Fore.CYAN}Docs fetched:{Style.RESET_ALL} {', '.join(result.packages_fetched)}")
        print(f"\n{Fore.BLUE}Total time:{Style.RESET_ALL} {format_duration(total_elapsed)}")

        return 0 if result.review_complete else 1

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except RuntimeError as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
