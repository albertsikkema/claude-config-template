#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "colorama>=0.4.6",
# ]
# ///
"""
Multi-phase Claude Code orchestrator: Plan → Implement → Cleanup

Plan Phase Flow:
    1. Index codebase
    2. Interactive query refinement (analyzes codebase, improves query, identifies docs)
    3. Fetch technical documentation
    4. Research codebase with refined query
    5. Create implementation plan

Implement Phase Flow (/implement_plan → review → fix → handoff):
    1. Validate plan, detect tooling, auto-discover research
    2. Index codebase, ensure feature branch
    3. Run /implement_plan (single invocation, includes plan-validator)
    4. Review → fix cycles (max 3: automated review with verdict, fix if needed)
    5. Archive review, clean up transient artifacts
    6. Interactive handoff session (summary of done/fixed/open)

Usage:
    uv run .claude/helpers/orchestrator.py "Add user authentication"              # Run all phases
    uv run .claude/helpers/orchestrator.py --phase plan "Add user authentication" # Plan phase only
    uv run .claude/helpers/orchestrator.py --phase implement path/to/plan.md      # Implement phase
    uv run .claude/helpers/orchestrator.py --phase cleanup path/to/plan.md        # Cleanup phase
    uv run .claude/helpers/orchestrator.py --no-refine "Quick fix"                # Skip query refinement

Aliases: Add to ~/.zshrc or ~/.bashrc:

    # Orchestrator aliases
    alias orch='uv run .claude/helpers/orchestrator.py'
    alias orch-plan='uv run .claude/helpers/orchestrator.py --phase plan'
    alias orch-impl='uv run .claude/helpers/orchestrator.py --phase implement'
    alias orch-clean='uv run .claude/helpers/orchestrator.py --phase cleanup'

Then use:
    orch "Add user authentication"           # All phases (with interactive refinement)
    orch --no-refine "Quick bugfix"          # Skip refinement for simple tasks
    orch-plan "Add user authentication"      # Plan only
    orch-impl memories/shared/plans/xxx.md   # Implement only
    orch-clean memories/shared/plans/xxx.md  # Cleanup only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from colorama import Fore, Style, init

# Initialize colorama
init()

# Color mapping for stages
STAGE_COLORS = {
    'Indexing': Fore.CYAN,
    'Docs': Fore.CYAN,
    'Research': Fore.YELLOW,
    'Planning': Fore.MAGENTA,
    'Implement': Fore.GREEN,
    'Build': Fore.GREEN,
    'Review': Fore.BLUE,
    'Fix': Fore.YELLOW,
    'Cleanup': Fore.YELLOW,
    'Handoff': Fore.CYAN,
    'Commit': Fore.GREEN,
}

# Map index file suffixes to indexer scripts
INDEXER_MAP = {
    '_py.md': 'index_python.py',
    '_js_ts.md': 'index_js_ts.py',
    '_go.md': 'index_go.py',
    '_cpp.md': 'index_cpp.py',
    '_api_tools.md': 'index_api_tools.py',
}


# --- Result dataclasses ---

@dataclass
class PlanPhaseResult:
    """Result from the plan phase."""
    research_path: str
    plan_path: str
    summary: str


@dataclass
class BuildResult:
    """Result from a build/fix loop."""
    success: bool
    iterations: int
    pre_commit: str


@dataclass
class ImplementConfig:
    """Configuration for the implement phase (/implement_plan → review → fix loop)."""
    max_turns: int = 40
    max_fix_iterations: int = 5
    max_review_cycles: int = 3
    plan_path: str = ''
    research_path: str = ''
    test_cmd: str = ''
    lint_cmd: str = ''
    codebase_index: str = ''


@dataclass
class ImplementPhaseResult:
    """Result from the implement phase."""
    plan_path: str
    review_path: str
    status: str  # 'PASS', 'NEEDS_REVIEW'
    build_iterations: int
    review_cycles: int
    commits_made: int
    pre_commit: str


@dataclass
class CleanupPhaseResult:
    """Result from the cleanup phase."""
    committed: bool
    commit_hash: str | None
    pr_url: str | None


@dataclass
class QueryRefinementResult:
    """Result from interactive query refinement."""
    refined_query: str
    technical_docs: list[str]
    context_notes: str


# --- Utility functions ---

def print_phase_header(phase_name: str) -> None:
    """Print a prominent phase header with separators."""
    color = STAGE_COLORS.get(phase_name, Fore.WHITE)
    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}", file=sys.stderr, flush=True)
    print(f"\n{color}Starting Phase: {phase_name}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)
    print(f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)


def stream_progress(stage: str, message: str) -> None:
    """Print progress update to stderr for real-time feedback."""
    color = STAGE_COLORS.get(stage, Fore.WHITE)
    if 'FAILED' in message:
        color = Fore.RED
    elif 'Complete' in message:
        color = Fore.GREEN
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
                # Show brief input summary
                if isinstance(tool_input, dict):
                    input_parts = []
                    for k, v in list(tool_input.items())[:3]:
                        v_str = str(v)
                        # Longer limit for file paths, shorter for other values
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
                # Show first 2 lines, truncated
                lines = result.split('\n')[:2]
                preview = ' | '.join(line.strip() for line in lines if line.strip())[:150]
                if preview:
                    suffix = '...' if len(result) > 150 else ''
                    return f"  {Fore.YELLOW}← {preview}{suffix}{Style.RESET_ALL}"
        return None

    # Result event (final output)
    if event_type == 'result':
        result_text = event.get('result', '')
        if result_text:
            # Show first 3 lines max
            lines = result_text.strip().split('\n')[:3]
            preview = '\n'.join(lines)
            suffix = '\n...' if len(result_text.split('\n')) > 3 else ''
            return f"\n{Fore.GREEN}✓ Done{Style.RESET_ALL}\n"
        return None

    return None


def run_claude_command(command: list[str], cwd: str, timeout: int = 600, phase: str = '') -> tuple[int, str, float]:
    """Run a Claude Code command with real-time output streaming.

    Returns:
        Tuple of (return_code, captured_output, elapsed_seconds)
    """
    # Use stream-json with verbose for real-time output in -p mode
    command = command.copy()
    command.insert(1, '--verbose')
    command.insert(2, '--output-format')
    command.insert(3, 'stream-json')

    # Print phase header if provided
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
        process.wait()  # Reap the process to avoid zombies
        elapsed = time.time() - start_time
        raise RuntimeError(f"Command timed out after {format_duration(elapsed)}")

    elapsed = time.time() - start_time
    # Fallback to 1 if returncode is None (shouldn't happen after wait())
    returncode = process.returncode if process.returncode is not None else 1
    return returncode, ''.join(output_lines), elapsed


def run_claude_interactive(prompt: str, cwd: str) -> int:
    """Run Claude interactively (not in container) for user interaction."""
    print(f"{Fore.BLUE}Starting interactive Claude session...{Style.RESET_ALL}", file=sys.stderr)
    process = subprocess.run(
        ['claude', prompt],
        cwd=cwd,
    )
    return process.returncode


def run_claude_interactive_command(initial_message: str, cwd: str, phase: str = '') -> tuple[int, float]:
    """Run Claude interactively with an initial message (no output capture).

    This is for interactive sessions where the user needs to interact with Claude.
    Output goes directly to the terminal.

    Returns:
        Tuple of (return_code, elapsed_seconds)
    """
    if phase:
        print_phase_header(phase)

    start_time = time.time()
    process = subprocess.run(
        ['claude-safe', '--no-firewall', '--', initial_message],
        cwd=cwd,
    )
    elapsed = time.time() - start_time
    return process.returncode, elapsed


def extract_file_path(output: str, path_type: str = 'research') -> str | None:
    """Extract file path from Claude Code output.

    Args:
        output: The command output to search
        path_type: One of 'research', 'plans', or 'reviews'

    Returns:
        The file path if found, None otherwise
    """
    # Look for markdown file paths in the output
    pattern = rf'memories/shared/{path_type}/[\w\-]+\.md'
    matches = re.findall(pattern, output)
    if matches:
        return matches[-1]  # Return last match (most likely the created file)
    return None


def find_codebase_index(project_path: str) -> str | None:
    """Find the most recent codebase index file."""
    codebase_dir = Path(project_path) / 'memories' / 'codebase'
    if not codebase_dir.exists():
        return None

    # Find all overview files
    index_files = list(codebase_dir.glob('codebase_overview_*.md'))
    if not index_files:
        return None

    # Return the most recently modified one
    return str(max(index_files, key=lambda f: f.stat().st_mtime))


def git_rev_parse_head(project_path: str) -> str:
    """Get current HEAD commit hash."""
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=project_path, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Failed to get HEAD commit hash")
    return result.stdout.strip()


def git_current_branch(project_path: str) -> str:
    """Get current branch name."""
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=project_path, capture_output=True, text=True,
    )
    return result.stdout.strip()


def read_plan_frontmatter(plan_path: Path) -> dict[str, str]:
    """Read YAML frontmatter from a plan file as a flat dict."""
    try:
        content = plan_path.read_text(encoding='utf-8')
    except OSError:
        return {}
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end < 0:
        return {}
    metadata = {}
    for line in content[3:end].strip().splitlines():
        if ':' in line:
            key, _, value = line.partition(':')
            metadata[key.strip()] = value.strip()
    return metadata


def update_plan_frontmatter(plan_path: Path, key: str, value: str) -> None:
    """Add or update a key in the plan's YAML frontmatter."""
    try:
        content = plan_path.read_text(encoding='utf-8')
    except OSError:
        return

    if not content.startswith('---'):
        # No frontmatter — add one
        content = f'---\n{key}: {value}\n---\n\n' + content
        plan_path.write_text(content, encoding='utf-8')
        return

    end = content.find('---', 3)
    if end < 0:
        return

    frontmatter = content[3:end]
    body = content[end:]

    pattern = rf'^{re.escape(key)}:\s*.*$'
    if re.search(pattern, frontmatter, re.MULTILINE):
        frontmatter = re.sub(pattern, f'{key}: {value}', frontmatter, flags=re.MULTILINE)
    else:
        frontmatter = frontmatter.rstrip() + f'\n{key}: {value}\n'

    plan_path.write_text('---' + frontmatter + body, encoding='utf-8')


def _interactive_select(options: list[str], header: str) -> int:
    """Arrow-key interactive selector. Returns the chosen index.

    Uses raw terminal input for arrow navigation and Enter to confirm.
    Falls back to numbered input if terminal is not interactive.
    """
    import tty
    import termios

    if not sys.stdin.isatty():
        # Non-interactive fallback
        print(header, file=sys.stderr, flush=True)
        for i, opt in enumerate(options):
            print(f"  {i + 1}. {opt}", file=sys.stderr, flush=True)
        choice = input("  > ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        return 0

    selected = 0

    def render():
        # Move cursor up to overwrite previous render (except first time)
        for i, opt in enumerate(options):
            if i == selected:
                line = f"  {Fore.GREEN}❯ {opt}{Style.RESET_ALL}"
            else:
                line = f"    {opt}"
            print(line, file=sys.stderr, flush=True)

    print(header, file=sys.stderr, flush=True)
    render()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == '\r' or ch == '\n':
                break
            if ch == '\x1b':
                seq = sys.stdin.read(2)
                if seq == '[A':  # Up arrow
                    selected = (selected - 1) % len(options)
                elif seq == '[B':  # Down arrow
                    selected = (selected + 1) % len(options)
                # Redraw: move cursor up N lines, then re-render
                print(f'\x1b[{len(options)}A', end='', file=sys.stderr, flush=True)
                # Clear the lines
                for _ in options:
                    print('\x1b[2K', file=sys.stderr, flush=True)
                print(f'\x1b[{len(options)}A', end='', file=sys.stderr, flush=True)
                render()
            elif ch == '\x03':  # Ctrl-C
                raise KeyboardInterrupt
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print(file=sys.stderr, flush=True)  # Newline after selection
    return selected


def _suggest_branch_name(plan_path: str) -> str:
    """Derive a branch name from the plan filename."""
    plan_stem = Path(plan_path).stem
    # Strip date prefix: 2026-02-14-add-feature -> add-feature
    name_part = re.sub(r'^\d{4}-\d{2}-\d{2}-?', '', plan_stem)
    return f'feat/{name_part}' if name_part else 'feat/implementation'


def ensure_feature_branch(plan_path: str, project_path: str) -> str:
    """Ensure we're on a feature branch, not main/master. Returns branch name.

    Shows an interactive branch selector. If on main/master, warns and puts
    "Create new" first. If on a feature branch, puts the current branch first.
    Updates the plan frontmatter with the chosen branch.
    """
    full_plan_path = Path(project_path) / plan_path
    current = git_current_branch(project_path)
    suggested = _suggest_branch_name(plan_path)

    # Get existing feature branches
    result = subprocess.run(
        ['git', 'branch', '--format=%(refname:short)'],
        cwd=project_path, capture_output=True, text=True,
    )
    all_branches = [b.strip() for b in result.stdout.strip().splitlines()
                    if b.strip() and b.strip() not in ('main', 'master')]

    on_main = current in ('main', 'master')

    # Build option list
    options = []
    # Maps index -> (action, branch_name)
    actions: list[tuple[str, str]] = []

    if on_main:
        header = f"\n{Fore.YELLOW}⚠ On {current} — select a feature branch:{Style.RESET_ALL}\n"
        # First option: create new
        options.append(f"Create: {Fore.CYAN}{suggested}{Style.RESET_ALL}")
        actions.append(('create', suggested))
        # Then existing branches
        for b in all_branches:
            options.append(b)
            actions.append(('switch', b))
    else:
        header = f"\n  Select branch:\n"
        # First option: stay on current
        options.append(f"{current} {Fore.GREEN}(current){Style.RESET_ALL}")
        actions.append(('stay', current))
        # Second option: create new
        options.append(f"Create: {Fore.CYAN}{suggested}{Style.RESET_ALL}")
        actions.append(('create', suggested))
        # Then other existing branches
        for b in all_branches:
            if b != current:
                options.append(b)
                actions.append(('switch', b))

    selected = _interactive_select(options, header)
    action, target_branch = actions[selected]

    if action == 'create':
        subprocess.run(['git', 'checkout', '-b', target_branch],
                       cwd=project_path, check=True)
        stream_progress('Branch', f'Created: {target_branch}')
    elif action == 'switch':
        subprocess.run(['git', 'checkout', target_branch],
                       cwd=project_path, check=True)
        stream_progress('Branch', f'Switched to: {target_branch}')
    else:
        stream_progress('Branch', f'Staying on: {target_branch}')

    update_plan_frontmatter(full_plan_path, 'branch', target_branch)
    return target_branch


# --- Tooling detection ---

def detect_tooling(project_path: str) -> tuple[str, str, str]:
    """Detect test command, lint command, and format command for the project.

    Returns:
        Tuple of (test_cmd, lint_cmd, format_cmd)
    """
    project = Path(project_path)

    # Python with uv
    if (project / 'pyproject.toml').exists() and (project / 'uv.lock').exists():
        return 'uv run pytest -v', 'uv run ruff check .', 'uv run ruff format --check .'

    # Python without uv
    if (project / 'pyproject.toml').exists() or (project / 'setup.py').exists():
        test_cmd = 'pytest -v'
        lint_cmd = 'ruff check .' if (project / 'pyproject.toml').exists() else 'flake8 .'
        format_cmd = 'ruff format --check .' if (project / 'pyproject.toml').exists() else 'black --check .'
        return test_cmd, lint_cmd, format_cmd

    # JavaScript/TypeScript
    package_json = project / 'package.json'
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding='utf-8'))
            scripts = data.get('scripts', {})
            test_cmd = 'npm test' if 'test' in scripts else 'echo "no test script"'
            lint_cmd = 'npm run lint' if 'lint' in scripts else 'echo "no lint script"'
            format_cmd = 'npm run format' if 'format' in scripts else 'echo "no format script"'
            return test_cmd, lint_cmd, format_cmd
        except (json.JSONDecodeError, IOError):
            return 'npm test', 'npm run lint', 'echo "no format script"'

    # Go
    if (project / 'go.mod').exists():
        return 'go test ./...', 'golangci-lint run', 'gofmt -l .'

    return 'echo "no test command"', 'echo "no lint command"', 'echo "no format command"'


# --- Plan section extraction ---

def extract_plan_sections(content: str) -> dict[str, str]:
    """Extract key sections from a plan file.

    Returns dict with keys: title, overview, phases, criteria, files, testing
    """
    sections: dict[str, str] = {}

    # Strip YAML frontmatter
    body = content
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            body = content[end + 3:].strip()

    # Extract title (first # heading)
    title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
    sections['title'] = title_match.group(1).strip() if title_match else 'Implementation'

    # Extract overview/context — everything before first ## heading
    first_h2 = re.search(r'^##\s+', body, re.MULTILINE)
    if first_h2:
        overview = body[:first_h2.start()].strip()
        # Remove the title line itself
        overview = re.sub(r'^#\s+.+\n*', '', overview).strip()
        sections['overview'] = overview
    else:
        sections['overview'] = ''

    # Extract phases (## Phase N or ## Implementation Step N or ## N. heading)
    phase_pattern = r'^##\s+(?:Phase\s+\d+|Implementation\s+(?:Step\s+)?\d+|\d+\.\s+).+$'
    phase_matches = list(re.finditer(phase_pattern, body, re.MULTILINE))
    if phase_matches:
        phases_text = []
        for i, match in enumerate(phase_matches):
            start = match.start()
            end = phase_matches[i + 1].start() if i + 1 < len(phase_matches) else len(body)
            phases_text.append(body[start:end].strip())
        sections['phases'] = '\n\n'.join(phases_text)
    else:
        # Fallback: extract all ## sections as potential task sections
        h2_pattern = r'^##\s+.+$'
        h2_matches = list(re.finditer(h2_pattern, body, re.MULTILINE))
        if h2_matches:
            all_sections = []
            for i, match in enumerate(h2_matches):
                start = match.start()
                end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(body)
                section_text = body[start:end].strip()
                # Skip non-task sections
                heading = match.group(0).lower()
                if any(skip in heading for skip in ['context', 'overview', 'background',
                                                     'success criteria', 'verification',
                                                     'critical reference', 'key design',
                                                     'implementation order']):
                    continue
                all_sections.append(section_text)
            sections['phases'] = '\n\n'.join(all_sections) if all_sections else body
        else:
            sections['phases'] = body

    # Extract success criteria (checkbox lines)
    criteria_lines = re.findall(r'^[-*]\s+\[[ x]\]\s+.+$', body, re.MULTILINE)
    sections['criteria'] = '\n'.join(criteria_lines) if criteria_lines else ''

    # Extract file paths (bold file patterns)
    file_paths = re.findall(r'\*\*(?:File|Path)\*\*:\s*`([^`]+)`', body)
    # Also find backtick paths that look like file paths (must contain / or start with a word char)
    file_paths += re.findall(r'`((?:[a-zA-Z0-9_./-]+/)[a-zA-Z0-9_.-]+\.[a-z]{1,4})`', body)
    sections['files'] = '\n'.join(f'- `{p}`' for p in sorted(set(file_paths))) if file_paths else ''

    return sections


# --- Codebase index refresh ---

def refresh_codebase_indexes(project_path: str) -> None:
    """Re-run indexers for all existing codebase index files.

    Parses index filenames to determine which indexer and source directory to use,
    then re-runs each indexer directly (no Claude call).
    """
    codebase_dir = Path(project_path) / 'memories' / 'codebase'
    if not codebase_dir.exists():
        return

    helpers_dir = Path(project_path) / '.claude' / 'helpers'
    index_files = list(codebase_dir.glob('codebase_overview_*.md'))

    for index_file in index_files:
        filename = index_file.name  # e.g., codebase_overview_backend_py.md

        # Find which indexer to use based on suffix
        indexer_script = None
        for suffix, script in INDEXER_MAP.items():
            if filename.endswith(suffix):
                indexer_script = helpers_dir / script
                # Extract dirname: remove prefix 'codebase_overview_' and the suffix
                prefix = 'codebase_overview_'
                dirname = filename[len(prefix):-len(suffix)]
                break

        if not indexer_script or not indexer_script.exists():
            continue

        # Map dirname to source directory
        if dirname == 'root':
            source_dir = './'
        else:
            source_dir = f'./{dirname}/'

        # Verify source directory exists
        full_source = Path(project_path) / source_dir
        if not full_source.exists():
            continue

        # Re-run indexer
        try:
            subprocess.run(
                [sys.executable, str(indexer_script), source_dir,
                 '-o', str(index_file)],
                cwd=project_path,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            stream_progress('Indexing', f'Warning: Failed to refresh {index_file.name}: {e}')


# --- Review / Fix loops ---

def run_review(project_path: str, build_result: BuildResult,
               config: ImplementConfig, review_cycle: int) -> str:
    """Run a code review on changes since pre_impl_commit.

    Returns 'REVIEW_PASS', 'REVIEW_NEEDS_FIXES', or 'REVIEW_UNKNOWN'.
    """
    stream_progress('Review', f'Review cycle {review_cycle}/{config.max_review_cycles}')

    # Generate diff into impl-logs/ to avoid accidental commits from git add -A
    log_dir = Path(project_path) / 'memories' / 'shared' / 'impl-logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    diff_file = log_dir / 'review-diff.patch'
    with diff_file.open('w') as f:
        subprocess.run(
            ['git', 'diff', build_result.pre_commit, 'HEAD'],
            cwd=project_path,
            stdout=f,
        )

    diff_lines = len(diff_file.read_text().splitlines())
    diff_rel = os.path.relpath(diff_file, project_path)
    stream_progress('Review', f'Diff: {diff_lines} lines saved to {diff_rel}')

    # Refresh indexes before review
    refresh_codebase_indexes(project_path)

    # Build context file references
    context_files = []
    if config.plan_path:
        context_files.append(f'- Plan: `{config.plan_path}`')
    if config.research_path:
        context_files.append(f'- Research: `{config.research_path}`')
    context_files.append(f'- Diff: `{diff_rel}`')
    context_section = '\n'.join(context_files)

    # REVIEW.md also goes in impl-logs/ to avoid accidental commits
    review_md_path = log_dir / 'REVIEW.md'
    review_md_rel = os.path.relpath(review_md_path, project_path)

    # Build review prompt — closely mirrors /code_reviewer command
    review_prompt = f"""You are a senior software engineer conducting a thorough code review.
You are reviewing ONLY the changes introduced since commit {build_result.pre_commit}.

## Critical First Step
Read relevant docs in `/memories/technical_docs` before starting.

## Context Files
{context_section}

## Before You Review
1. Read the plan, research, and specs files listed above.
2. Read `{diff_rel}` to see all changes.
3. Run `git log {build_result.pre_commit}..HEAD --oneline` to see commit history.
4. Run `{config.test_cmd}` to verify tests pass.
5. Run `{config.lint_cmd}` to verify linting passes.

## Review Priorities

### 1. Correctness
- Does the code do what it's supposed to do?
- Are there logical errors or edge cases not handled?

### 2. Security
- Look for vulnerabilities like SQL injection, XSS, exposed credentials
- Check for unsafe operations or improper input validation

### 3. Performance
- Identify inefficient algorithms or unnecessary computations
- Look for memory leaks or operations that could be optimized

### 4. Code Quality
- Is the code readable and self-documenting?
- Are naming conventions clear and consistent?
- Is there appropriate separation of concerns?

### 5. Best Practices
- Does the code follow established patterns and conventions for the language/framework?

### 6. Error Handling
- Are errors properly caught, logged, and handled?
- Are there appropriate fallbacks?

### 7. Testing
- Is the code testable?
- Are there suggestions for test cases that should be written?

### 8. Simplicity
- Can the implementation be simplified?
- Are there easier alternatives that achieve the same result?
- Is any code over-engineered for the requirements?

## Output
Write your review to `{review_md_rel}` using this format:

## SUMMARY
[Brief description and overall assessment]

## CRITICAL ISSUES
1. [Issue with file:line reference and specific fix suggestion]

## IMPROVEMENTS
1. [Improvement with rationale and code example]

## MINOR NOTES
- [Style or convention suggestions]

## WELL DONE
- [Positive aspects of the code]

## QUESTIONS
- [Any clarifications needed]

Include a verdict line at the VERY END of `{review_md_rel}`:
REVIEW_PASS  (no critical issues or improvements needed)
REVIEW_NEEDS_FIXES  (has critical issues or improvements that should be fixed)

## Rules
- Do NOT modify any code. Read-only review.
- Every issue MUST include file:line reference and specific fix suggestion.
"""

    run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', review_prompt],
        cwd=project_path, timeout=600, phase='Review'
    )

    # Read verdict from REVIEW.md — check last 20 lines where verdict should be
    if not review_md_path.exists():
        stream_progress('Review', f'Warning: {review_md_rel} not created')
        return 'REVIEW_UNKNOWN'

    review_content = review_md_path.read_text(encoding='utf-8')
    tail = '\n'.join(review_content.splitlines()[-20:])

    if 'REVIEW_NEEDS_FIXES' in tail:
        stream_progress('Review', 'Verdict: REVIEW_NEEDS_FIXES')
        return 'REVIEW_NEEDS_FIXES'
    elif 'REVIEW_PASS' in tail:
        stream_progress('Review', 'Verdict: REVIEW_PASS')
        return 'REVIEW_PASS'
    else:
        stream_progress('Review', f'Warning: No clear verdict in {review_md_rel}')
        return 'REVIEW_UNKNOWN'


def run_fix(project_path: str, config: ImplementConfig,
            pre_commit: str) -> BuildResult:
    """Run a single fix pass to address review findings.

    Creates a fix prompt from REVIEW.md and runs Claude once.
    pre_commit is the original baseline, preserved across review-fix cycles.
    """
    review_md_rel = os.path.relpath(
        Path(project_path) / 'memories' / 'shared' / 'impl-logs' / 'REVIEW.md', project_path
    )

    # Build reference documents section
    ref_docs = []
    step = 3
    if config.plan_path:
        ref_docs.append(f'{step}. Read the plan at `{config.plan_path}`.')
        step += 1
    if config.research_path:
        ref_docs.append(f'{step}. Read the research at `{config.research_path}`.')
        step += 1
    ref_section = '\n'.join(ref_docs)

    fix_prompt = f"""You are fixing issues identified in a code review.

## Before You Start
1. Read `{review_md_rel}` for the review findings.
2. Read the codebase index at `{config.codebase_index}`.
{ref_section}
{step}. Run tests: `{config.test_cmd}`
{step + 1}. Run linter: `{config.lint_cmd}`

## Fix Priority
1. Critical Issues — MUST fix
2. Improvements — SHOULD fix
3. Minor Notes — SKIP

## Rules
- Run tests after every change: `{config.test_cmd}`
- Run linter after every change: `{config.lint_cmd}`
- Fix failures before moving on
- Commit each fix: `git add -A && git commit -m "fix[optional scope]: <lowercase imperative description>"`

## When Done
When all Critical Issues and Improvements are fixed, tests pass, and linter passes,
output exactly: IMPL_DONE
"""

    stream_progress('Fix', 'Running fix pass...')

    # Refresh indexes before fix
    refresh_codebase_indexes(project_path)

    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', fix_prompt,
         '--max-turns', str(config.max_turns)],
        cwd=project_path,
        timeout=900,
        phase='Fix'
    )

    success = 'IMPL_DONE' in output
    stream_progress('Fix', f'Complete ({format_duration(elapsed)}, '
                    f'{"IMPL_DONE" if success else "no IMPL_DONE"})')

    return BuildResult(success=success, iterations=1, pre_commit=pre_commit)


def save_review_with_frontmatter(project_path: str, review_cycle: int) -> str | None:
    """Save REVIEW.md with proper frontmatter to memories/shared/reviews/.

    Returns path to saved review, or None on failure.
    """
    review_file = Path(project_path) / 'memories' / 'shared' / 'impl-logs' / 'REVIEW.md'
    if not review_file.exists():
        return None

    review_content = review_file.read_text(encoding='utf-8')

    # Run spec_metadata.sh for frontmatter values
    metadata_script = Path(project_path) / '.claude' / 'helpers' / 'spec_metadata.sh'
    metadata = {}
    if metadata_script.exists():
        try:
            result = subprocess.run(
                ['bash', str(metadata_script)],
                cwd=project_path,
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    if ':' in line:
                        key, _, value = line.partition(':')
                        metadata[key.strip()] = value.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Build frontmatter
    date = metadata.get('Current Date/Time (TZ)', time.strftime('%Y-%m-%d %H:%M:%S %Z'))
    uuid = metadata.get('UUID', '')
    session_id = metadata.get('claude-sessionid', '')
    git_commit = metadata.get('Current Git Commit Hash', '')
    branch = metadata.get('Current Branch Name', '')
    repo_name = metadata.get('Repository Name', '')

    date_str = time.strftime('%Y-%m-%d')
    filename = f'code-review-{date_str}-iter{review_cycle}.md'

    frontmatter = f"""---
date: {date}
file-id: {uuid}
claude-sessionid: {session_id}
reviewer: orchestrator
git_commit: {git_commit}
branch: {branch}
repository: {repo_name}
review_type: automated_review
review_iteration: {review_cycle}
tags: [code-review, automated]
status: complete
last_updated: {time.strftime('%Y-%m-%d %H:%M')}
last_updated_by: orchestrator
---

"""

    # Save to memories/shared/reviews/
    reviews_dir = Path(project_path) / 'memories' / 'shared' / 'reviews'
    reviews_dir.mkdir(parents=True, exist_ok=True)

    output_path = reviews_dir / filename
    output_path.write_text(frontmatter + review_content, encoding='utf-8')

    return os.path.relpath(output_path, project_path)


def _cleanup_impl_artifacts(project_path: str) -> None:
    """Remove transient artifacts from impl-logs/ after archiving."""
    log_dir = Path(project_path) / 'memories' / 'shared' / 'impl-logs'
    for name in ('review-diff.patch', 'REVIEW.md', 'fix-prompt.md'):
        artifact = log_dir / name
        if artifact.exists():
            artifact.unlink()


# --- Research auto-discovery ---

def auto_discover_research(plan_path: str, project_path: str) -> str:
    """Try to find a matching research file by date prefix from the plan filename.

    E.g., plan '2026-02-08-feature.md' → search 'memories/shared/research/2026-02-08*.md'

    Returns relative path to research file, or empty string if not found.
    """
    plan_stem = Path(plan_path).stem
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', plan_stem)
    if not date_match:
        return ''

    date_prefix = date_match.group(1)
    research_dir = Path(project_path) / 'memories' / 'shared' / 'research'
    if not research_dir.exists():
        return ''

    matches = sorted(research_dir.glob(f'{date_prefix}*.md'),
                     key=lambda f: f.stat().st_mtime, reverse=True)
    if matches:
        return str(matches[0].relative_to(project_path))

    return ''


# --- Query refinement ---

def run_query_refinement(query: str, project_path: str) -> QueryRefinementResult:
    """Interactive session to refine the query based on codebase context.

    Returns refined query, list of technical docs needed, and context notes.
    """
    # Find codebase index
    index_path = find_codebase_index(project_path)
    index_context = ""
    if index_path:
        rel_path = os.path.relpath(index_path, project_path)
        index_context = f"The codebase has been indexed. Read the index at: {rel_path}"
    else:
        index_context = "No codebase index found."

    # Create output file in memories/shared/refinement/ with timestamp
    refinement_dir = Path(project_path) / 'memories' / 'shared' / 'refinement'
    refinement_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime('%Y-%m-%d-%H%M%S')
    output_file = refinement_dir / f'{timestamp}-query-refinement.json'

    prompt = f'''Quickly refine a development task query. This is NOT research - just improve the query text.

## USER'S ORIGINAL QUERY:
{query}

## Context (skim briefly)
{index_context}
- CLAUDE.md, README.md, memories/shared/project/ (if they exist)

## RULES
- **DO NOT list files to change** - that's for the research phase
- **DO NOT do detailed analysis** - just refine the query
- Keep the refined query to **4-5 sentences max**
- Preserve all user requirements from the original
- You may ask **up to 2 clarifying questions** if something is unclear or ambiguous

## Output a refined query like this:
"[Clear action verb] [what to change] from [old tech] to [new tech]. [Key requirements from original]. Use [recommended libraries]."

Example: "Replace MongoDB/Beanie with PostgreSQL/SQLAlchemy 2.0 async in the FastAPI backend. Clean implementation - no data migration, no MongoDB patterns to preserve. Use asyncpg driver and Alembic for migrations. Follow repository pattern for data access."

## Then list technical docs needed (just package names)

Ask user to confirm (or ask up to 2 clarifying questions first), then write to: memories/shared/refinement/{timestamp}-query-refinement.json

```json
{{
  "refined_query": "4-5 sentence improved query",
  "technical_docs": ["package1", "package2"],
  "context_notes": "One line summary"
}}
```'''

    print_phase_header("Query Refinement")
    print(f"{Fore.WHITE}Starting interactive query refinement session...{Style.RESET_ALL}", file=sys.stderr)
    print(f"{Fore.YELLOW}Original query:{Style.RESET_ALL} {query}\n", file=sys.stderr)
    print(f"{Fore.CYAN}You can interact with Claude to refine the query. Type 'exit' or press Ctrl+C when done.{Style.RESET_ALL}\n", file=sys.stderr)

    # Run truly interactive Claude session (no -p flag, but skip permissions for speed)
    # --system-prompt sets context, initial message starts the conversation
    process = subprocess.run(
        ['claude-safe', '--no-firewall', '--', '--system-prompt', prompt,
         'Read the context files (codebase index, CLAUDE.md, README.md, memories/shared/project/) and propose a refined query. Keep it brief.'],
        cwd=project_path,
    )

    if process.returncode != 0:
        stream_progress("Query Refinement", "Session ended with non-zero exit")

    # Read the output file
    if output_file.exists():
        try:
            result = json.loads(output_file.read_text())
            rel_output = os.path.relpath(output_file, project_path)
            stream_progress("Query Refinement", f"Complete: {rel_output}")
            return QueryRefinementResult(
                refined_query=result.get('refined_query', query),
                technical_docs=result.get('technical_docs', []),
                context_notes=result.get('context_notes', '')
            )
        except json.JSONDecodeError:
            stream_progress("Query Refinement", "Warning: Could not parse output, using original query")

    # Fallback to original query if something went wrong
    stream_progress("Query Refinement", "Using original query (no refinement output)")
    return QueryRefinementResult(
        refined_query=query,
        technical_docs=[],
        context_notes=''
    )


# --- Phase implementations ---

def run_phase_plan(query: str, project_path: str, skip_refinement: bool = False,
                   non_interactive: bool = False) -> PlanPhaseResult:
    """Phase 1: Index → Refine Query → Docs → Research → Plan"""

    # Step 1: Index codebase
    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', '/index_codebase'],
        cwd=project_path,
        timeout=600,
        phase='Indexing'
    )
    if returncode != 0:
        raise RuntimeError(f"Indexing failed with code {returncode}")
    stream_progress("Indexing", f"Complete ({format_duration(elapsed)})")

    # Step 2: Interactive query refinement
    if skip_refinement:
        refined = QueryRefinementResult(refined_query=query, technical_docs=[], context_notes='')
        stream_progress("Query Refinement", "Skipped (--no-refine)")
    elif non_interactive:
        # Skip refinement in non-interactive mode, use query as-is
        refined = QueryRefinementResult(refined_query=query, technical_docs=[], context_notes='')
        stream_progress("Query Refinement", "Skipped (non-interactive mode)")
    else:
        refined = run_query_refinement(query, project_path)

    working_query = refined.refined_query
    print(f"\n{Fore.GREEN}Using query:{Style.RESET_ALL} {working_query}\n", file=sys.stderr)

    # Step 3: Fetch docs using /fetch_technical_docs
    # Pass suggested packages from refinement as arguments (quote packages with spaces)
    if refined.technical_docs:
        quoted_pkgs = [f"'{pkg}'" if ' ' in pkg else pkg for pkg in refined.technical_docs]
        docs_prompt = f"/fetch_technical_docs {' '.join(quoted_pkgs)}"
    else:
        docs_prompt = '/fetch_technical_docs'

    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', docs_prompt],
        cwd=project_path,
        timeout=600,
        phase='Docs'
    )
    stream_progress("Docs", f"Complete ({format_duration(elapsed)})")

    # Step 4: Research with refined query
    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', f'/research_codebase {working_query}'],
        cwd=project_path,
        timeout=600,
        phase='Research'
    )
    if returncode != 0:
        raise RuntimeError(f"Research failed with code {returncode}")

    research_path = extract_file_path(output, 'research')
    if not research_path:
        raise RuntimeError("Could not extract research file path from output")
    stream_progress("Research", f"Complete: {research_path} ({format_duration(elapsed)})")

    # Step 5: Create plan interactively
    context_section = f"Context: {working_query}"
    if refined.context_notes:
        context_section += f"\n\nAdditional context from codebase analysis:\n{refined.context_notes}"

    prompt = f"""/create_plan {research_path}

{context_section}

Please proceed with reasonable defaults based on the research."""

    if non_interactive:
        # Non-interactive: use -p flag and capture output
        returncode, output, elapsed = run_claude_command(
            ['claude-safe', '--no-firewall', '--', '-p', prompt],
            cwd=project_path,
            timeout=600,
            phase='Planning'
        )
        if returncode != 0:
            raise RuntimeError(f"Planning failed with code {returncode}")

        plan_path = extract_file_path(output, 'plans')
        if not plan_path:
            raise RuntimeError("Could not extract plan file path from output")
        stream_progress("Planning", f"Complete: {plan_path} ({format_duration(elapsed)})")
    else:
        # Interactive: let user interact with Claude, no output capture
        returncode, elapsed = run_claude_interactive_command(
            prompt,
            cwd=project_path,
            phase='Planning'
        )
        if returncode != 0:
            raise RuntimeError(f"Planning failed with code {returncode}")

        # Find the most recent plan file (we can't extract from output in interactive mode)
        plans_dir = Path(project_path) / 'memories' / 'shared' / 'plans'
        if plans_dir.exists():
            plan_files = sorted(plans_dir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)
            plan_path = str(plan_files[0].relative_to(project_path)) if plan_files else None
        else:
            plan_path = None

        if not plan_path:
            raise RuntimeError("Could not find plan file after interactive session")
        stream_progress("Planning", f"Complete: {plan_path} ({format_duration(elapsed)})")

    # Generate summary
    summary = f"""Plan Phase Complete

Research: {research_path}
Plan: {plan_path}

Next step: Review the plan, then run --phase implement"""

    return PlanPhaseResult(
        research_path=research_path,
        plan_path=plan_path,
        summary=summary
    )


def _run_handoff_session(project_path: str, plan_path: str,
                         research_path: str, review_path: str,
                         pre_commit: str, current_commit: str,
                         status: str) -> None:
    """Open an interactive Claude session with full implementation context.

    Shows what was done, what was fixed, and what's open for improvement.
    """
    # Build list of files to read
    read_instructions = []
    read_instructions.append(f'1. Read the plan: `{plan_path}`')
    step = 2
    if research_path:
        read_instructions.append(f'{step}. Read the research: `{research_path}`')
        step += 1
    if review_path:
        read_instructions.append(f'{step}. Read the review: `{review_path}`')
        step += 1
    read_section = '\n'.join(read_instructions)

    handoff_prompt = f"""You are resuming after an automated implementation phase.

## Context Files — read these first
{read_section}
{step}. Run `git log --oneline {pre_commit}..{current_commit}` to see all commits made.
{step + 1}. Run `git diff {pre_commit}..{current_commit} --stat` to see files changed.

## Your Task
Present a clear summary to the user:

### What was done
- List the completed plan phases/tasks based on commits and plan checkboxes.

### What was fixed (from review)
- Summarize fixes applied during review cycles (if any review exists).

### Open for improvement
- List any CRITICAL ISSUES or IMPROVEMENTS from the review that were NOT addressed.
- Note any plan tasks that are still unchecked.
- Mention any test failures or lint warnings if present.

## Review Status: {status}

After presenting the summary, you are in an interactive session.
The user can ask you to fix remaining issues, run tests, make additional changes,
or proceed to cleanup (`/cleanup {plan_path}`).
"""

    run_claude_interactive_command(
        handoff_prompt,
        cwd=project_path,
        phase='Handoff'
    )


def run_phase_implement(plan_path: str, project_path: str,
                        research_path: str = '',
                        config: ImplementConfig | None = None) -> ImplementPhaseResult:
    """Phase 2: /implement_plan → review → fix → handoff.

    Steps:
        1. Validate plan, detect tooling, auto-discover research
        2. Index codebase, ensure feature branch
        3. Run /implement_plan (single invocation, includes plan-validator)
        4. Review → fix cycles (max 3: automated review with verdict, fix if needed)
        5. Archive review, clean up transient artifacts
        6. Interactive handoff session (summary of done/fixed/open)
    """
    # Validate plan exists
    full_plan_path = Path(project_path) / plan_path
    if not full_plan_path.exists():
        raise RuntimeError(f"Plan file not found: {plan_path}")

    # Ensure we're on a feature branch
    print_phase_header('Implement')
    ensure_feature_branch(plan_path, project_path)

    # Build config if not provided
    if config is None:
        config = ImplementConfig()

    config.plan_path = plan_path

    # Detect tooling
    test_cmd, lint_cmd, _ = detect_tooling(project_path)
    config.test_cmd = test_cmd
    config.lint_cmd = lint_cmd

    # Find research file
    if not research_path:
        research_path = auto_discover_research(plan_path, project_path)
    config.research_path = research_path

    if research_path:
        stream_progress('Implement', f'Using research: {research_path}')
    else:
        stream_progress('Implement', 'No research file found (use --research to specify)')

    # Step 1: Index codebase
    stream_progress('Indexing', 'Running /index_codebase via Claude...')
    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', '/index_codebase'],
        cwd=project_path, timeout=600, phase='Indexing'
    )
    if returncode != 0:
        stream_progress('Indexing', f'Warning: Indexing returned code {returncode}')
    else:
        stream_progress('Indexing', f'Complete ({format_duration(elapsed)})')

    # Update config with detected codebase index
    index_path = find_codebase_index(project_path)
    if index_path:
        config.codebase_index = os.path.relpath(index_path, project_path)

    # Step 2: Run /implement_plan (single invocation — includes plan-validator)
    pre_commit = git_rev_parse_head(project_path)

    # Build the /implement_plan prompt with additional context
    implement_prompt = f'/implement_plan {plan_path}'
    context_parts = []
    if research_path:
        context_parts.append(f'- Research: read `{research_path}` for codebase analysis and context.')
    if config.codebase_index:
        context_parts.append(f'- Codebase index: read `{config.codebase_index}` for the project map.')
    context_parts.append(f'- Test command: `{test_cmd}`')
    context_parts.append(f'- Lint command: `{lint_cmd}`')
    if context_parts:
        implement_prompt += '\n\nAdditional context:\n' + '\n'.join(context_parts)

    implement_prompt += """

After completing each phase, commit your work:
```
git add -A && git commit -m "<type>[optional scope]: <description>"
```
Follow Conventional Commits: feat, fix, refactor, test, docs, etc."""

    stream_progress('Implement', 'Running /implement_plan (includes plan-validator)...')
    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', implement_prompt,
         '--max-turns', str(config.max_turns)],
        cwd=project_path,
        timeout=1800,
        phase='Implement'
    )
    stream_progress('Implement',
                    f'/implement_plan complete ({format_duration(elapsed)}, exit={returncode})')

    # Step 3: Review → fix cycle (max review_cycles iterations)
    build_result = BuildResult(success=(returncode == 0), iterations=1, pre_commit=pre_commit)
    review_path = ''
    final_status = 'NEEDS_REVIEW'
    final_review_cycle = 0

    for cycle in range(1, config.max_review_cycles + 1):
        final_review_cycle = cycle

        # Review
        verdict = run_review(project_path, build_result, config, cycle)

        # Archive the review
        saved_review = save_review_with_frontmatter(project_path, cycle)
        if saved_review:
            review_path = saved_review
            stream_progress('Review', f'Saved review: {review_path}')

        # Check verdict
        if verdict == 'REVIEW_PASS':
            final_status = 'PASS'
            _cleanup_impl_artifacts(project_path)
            stream_progress('Implement', f'Review passed on cycle {cycle}')
            break

        # Skip fix on last cycle
        if cycle == config.max_review_cycles:
            stream_progress('Review',
                            f'Final review cycle ({cycle}) still has issues. Manual review needed.')
            break

        # Fix
        stream_progress('Fix', f'Fixing issues from review cycle {cycle}...')
        fix_result = run_fix(project_path, config, pre_commit)

        if fix_result.success:
            stream_progress('Fix', 'Fix complete')
        else:
            stream_progress('Fix', 'Fix did not signal completion — continuing to next review')

    # Clean up transient artifacts
    _cleanup_impl_artifacts(project_path)

    # Count commits made
    result = subprocess.run(
        ['git', 'log', f'{pre_commit}..HEAD', '--oneline'],
        cwd=project_path, capture_output=True, text=True
    )
    commit_count = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0

    # Print summary
    try:
        current_commit = git_rev_parse_head(project_path)
    except RuntimeError:
        current_commit = 'unknown'

    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}", file=sys.stderr, flush=True)
    print(f"\n{Fore.GREEN}{Style.BRIGHT}  Implement Summary{Style.RESET_ALL}\n", file=sys.stderr, flush=True)
    print(f"  Status:           {final_status}", file=sys.stderr, flush=True)
    print(f"  Review cycles:    {final_review_cycle}", file=sys.stderr, flush=True)
    print(f"  Commits made:     {commit_count}", file=sys.stderr, flush=True)
    print(f"  Pre-implement:    {pre_commit[:8]}", file=sys.stderr, flush=True)
    print(f"  Current HEAD:     {current_commit[:8]}", file=sys.stderr, flush=True)
    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)

    # Step 4: Interactive handoff — open a session with full context
    _run_handoff_session(
        project_path, plan_path, research_path, review_path,
        pre_commit, current_commit, final_status,
    )

    return ImplementPhaseResult(
        plan_path=plan_path,
        review_path=review_path,
        status=final_status,
        build_iterations=1,
        review_cycles=final_review_cycle,
        commits_made=commit_count,
        pre_commit=pre_commit,
    )


def run_phase_cleanup(plan_path: str, research_path: str, review_path: str, project_path: str) -> CleanupPhaseResult:
    """Phase 3: Cleanup → Commit remaining → PR → Complete"""

    # Validate plan exists
    full_plan_path = Path(project_path) / plan_path
    if not full_plan_path.exists():
        raise RuntimeError(f"Plan file not found: {plan_path}")

    # Switch to the branch recorded in the plan
    metadata = read_plan_frontmatter(full_plan_path)
    plan_branch = metadata.get('branch', '')
    if plan_branch:
        current = git_current_branch(project_path)
        if current != plan_branch:
            stream_progress('Branch', f'Switching to plan branch: {plan_branch}')
            subprocess.run(['git', 'checkout', plan_branch],
                           cwd=project_path, check=True)
    else:
        # No branch in frontmatter — warn if on main
        current = git_current_branch(project_path)
        if current in ('main', 'master'):
            stream_progress('Branch', f'Warning: on {current} and no branch recorded in plan')

    # Step 1: Cleanup
    cleanup_cmd = f'/cleanup {plan_path}'
    if research_path:
        cleanup_cmd += f' {research_path}'
    if review_path:
        cleanup_cmd += f' {review_path}'

    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', cleanup_cmd],
        cwd=project_path,
        timeout=600,
        phase='Cleanup'
    )
    if returncode != 0:
        raise RuntimeError(f"Cleanup failed with code {returncode}")
    stream_progress("Cleanup", f"Complete ({format_duration(elapsed)})")

    # Step 2: Commit remaining files (non-interactive)
    committed = _commit_remaining(project_path, plan_path)

    # Step 3: Mark plan complete (update frontmatter)
    if committed:
        mark_plan_complete(full_plan_path)

    # Step 4: Create PR if not on main
    pr_url = _create_pr_if_branch(project_path, plan_path, review_path)

    return CleanupPhaseResult(
        committed=committed,
        commit_hash=git_rev_parse_head(project_path) if committed else None,
        pr_url=pr_url,
    )


def _commit_remaining(project_path: str, plan_path: str) -> bool:
    """Commit any remaining uncommitted files. Returns True if a commit was made."""
    # Check if there's anything to commit
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=project_path, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        stream_progress("Commit", "No uncommitted changes")
        return False

    # Stage and commit
    subprocess.run(['git', 'add', '-A'], cwd=project_path, check=True)

    # Derive scope from plan filename: 2026-02-14-add-bruno-indexer.md -> add-bruno-indexer
    plan_name = Path(plan_path).stem
    # Strip date prefix (YYYY-MM-DD-)
    scope_part = re.sub(r'^\d{4}-\d{2}-\d{2}-?', '', plan_name)
    msg = f"chore(cleanup): update docs and best practices for {scope_part}"

    result = subprocess.run(
        ['git', 'commit', '-m', msg],
        cwd=project_path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        stream_progress("Commit", f"Commit failed: {result.stderr.strip()}")
        return False

    stream_progress("Commit", f"Committed cleanup changes")
    return True


def _extract_review_summary(review_path: str, project_path: str) -> str:
    """Extract the SUMMARY section from a review file."""
    full_path = Path(project_path) / review_path
    if not full_path.exists():
        return ''
    try:
        content = full_path.read_text(encoding='utf-8')
    except OSError:
        return ''

    # Extract text between ## SUMMARY and the next ## heading
    match = re.search(
        r'^##\s+SUMMARY\s*\n(.*?)(?=^##\s+|\Z)',
        content, re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ''


def _build_pr_body(plan_path: str, review_path: str,
                   project_path: str) -> tuple[str, str]:
    """Build PR title and body from plan and review. Returns (title, body)."""
    # Title from plan
    full_plan_path = Path(project_path) / plan_path
    try:
        content = full_plan_path.read_text(encoding='utf-8')
        sections = extract_plan_sections(content)
        title = sections['title'].removesuffix(' — Implementation').removesuffix(' Implementation Plan')
    except Exception:
        plan_name = Path(plan_path).stem
        scope_part = re.sub(r'^\d{4}-\d{2}-\d{2}-?', '', plan_name)
        title = scope_part.replace('-', ' ').capitalize()
        sections = {'overview': '', 'files': ''}

    # Body: prefer review summary, fall back to plan overview
    body_parts = []

    review_summary = _extract_review_summary(review_path, project_path) if review_path else ''
    if review_summary:
        body_parts.append(f'## Summary\n\n{review_summary}')
    elif sections['overview']:
        body_parts.append(f'## Summary\n\n{sections["overview"]}')

    if sections['files']:
        body_parts.append(f'## Key Files\n\n{sections["files"]}')

    body_parts.append(f'Plan: `{plan_path}`')

    return title, '\n\n'.join(body_parts)


def _create_pr_if_branch(project_path: str, plan_path: str,
                         review_path: str = '') -> str | None:
    """Create a PR via gh if on a feature branch. Returns PR URL or None."""
    # Get current branch
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=project_path, capture_output=True, text=True,
    )
    branch = result.stdout.strip()
    if branch in ('main', 'master'):
        stream_progress("PR", "On main branch, skipping PR creation")
        return None

    # Push branch
    stream_progress("PR", f"Pushing branch {branch}...")
    result = subprocess.run(
        ['git', 'push', '-u', 'origin', branch],
        cwd=project_path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        stream_progress("PR", f"Push failed: {result.stderr.strip()}")
        return None

    # Check if PR already exists
    result = subprocess.run(
        ['gh', 'pr', 'view', '--json', 'url', '-q', '.url'],
        cwd=project_path, capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        pr_url = result.stdout.strip()
        stream_progress("PR", f"PR already exists: {pr_url}")
        return pr_url

    # Build PR title and body from plan + review
    pr_title, pr_body = _build_pr_body(plan_path, review_path, project_path)

    result = subprocess.run(
        ['gh', 'pr', 'create', '--title', pr_title, '--body', pr_body],
        cwd=project_path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        stream_progress("PR", f"PR creation failed: {result.stderr.strip()}")
        return None

    pr_url = result.stdout.strip()
    stream_progress("PR", f"Created: {pr_url}")
    return pr_url


def mark_plan_complete(plan_path: Path) -> None:
    """Update plan frontmatter to mark as complete."""
    try:
        content = plan_path.read_text()

        # Only update status within YAML frontmatter (between --- markers)
        if content.startswith('---'):
            frontmatter_end = content.find('---', 3)
            if frontmatter_end > 0:
                frontmatter = content[:frontmatter_end]
                body = content[frontmatter_end:]
                if 'status:' in frontmatter:
                    frontmatter = re.sub(r'status:\s*\w+', 'status: complete', frontmatter)
                    plan_path.write_text(frontmatter + body)
    except Exception as e:
        stream_progress("Cleanup", f"Warning: Could not update plan status: {e}")


# --- Output formatting ---

def print_result(result: PlanPhaseResult | ImplementPhaseResult | CleanupPhaseResult, as_json: bool) -> None:
    """Print the result to stdout."""
    if as_json:
        print(json.dumps(asdict(result), indent=2))
    else:
        if isinstance(result, PlanPhaseResult):
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Plan Phase Complete:{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}Research:{Style.RESET_ALL} {result.research_path}")
            print(f"  {Fore.MAGENTA}Plan:{Style.RESET_ALL} {result.plan_path}")
            print(f"\n  {Fore.BLUE}Next:{Style.RESET_ALL} Review the plan, then run --phase implement {result.plan_path}")

        elif isinstance(result, ImplementPhaseResult):
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Implement Phase Complete:{Style.RESET_ALL}")
            print(f"  {Fore.MAGENTA}Plan:{Style.RESET_ALL} {result.plan_path}")
            if result.review_path:
                print(f"  {Fore.BLUE}Review:{Style.RESET_ALL} {result.review_path}")
            print(f"  {Fore.YELLOW}Status:{Style.RESET_ALL} {result.status}")
            print(f"  {Fore.CYAN}Build iterations:{Style.RESET_ALL} {result.build_iterations}")
            print(f"  {Fore.CYAN}Review cycles:{Style.RESET_ALL} {result.review_cycles}")
            print(f"  {Fore.CYAN}Commits made:{Style.RESET_ALL} {result.commits_made}")
            print(f"\n  {Fore.BLUE}Next:{Style.RESET_ALL} Review changes, then run --phase cleanup {result.plan_path}")

        elif isinstance(result, CleanupPhaseResult):
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Cleanup Phase Complete:{Style.RESET_ALL}")
            if result.committed:
                print(f"  {Fore.GREEN}Committed:{Style.RESET_ALL} Yes ({result.commit_hash[:8] if result.commit_hash else 'N/A'})")
            else:
                print(f"  {Fore.YELLOW}Committed:{Style.RESET_ALL} No changes to commit")
            if result.pr_url:
                print(f"  {Fore.GREEN}PR:{Style.RESET_ALL} {result.pr_url}")
            else:
                print(f"  {Fore.YELLOW}PR:{Style.RESET_ALL} Not created (on main or error)")


# --- Main entry point ---

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Multi-phase Claude Code orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Add user authentication"              # Run all phases (with interactive query refinement)
  %(prog)s --no-refine "Fix typo in readme"       # Skip refinement for simple tasks
  %(prog)s --phase plan "Add user authentication" # Plan phase only
  %(prog)s --phase implement path/to/plan.md      # Implement phase (autonomous build/review/fix)
  %(prog)s --phase cleanup path/to/plan.md        # Cleanup phase

  # With review/fix options:
  %(prog)s --phase implement --max-turns 30 path/to/plan.md
  %(prog)s --phase implement --max-review-cycles 5 path/to/plan.md
        """
    )
    parser.add_argument('query_or_path', help='Query (for plan) or plan path (for implement/cleanup)')
    parser.add_argument('--phase', choices=['plan', 'implement', 'cleanup', 'all'],
                        default='all', help='Which phase to run (default: all)')
    parser.add_argument('--project', default='.', help='Project directory path')
    parser.add_argument('--research', help='Research file path (for implement and cleanup phases)')
    parser.add_argument('--review', help='Review file path (for cleanup phase)')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--no-refine', action='store_true', dest='no_refine',
                        help='Skip interactive query refinement (use original query as-is)')
    parser.add_argument('--max-turns', type=int, default=40,
                        help='Turns per Claude iteration (default: 40)')
    parser.add_argument('--max-fix-iterations', type=int, default=5,
                        help='Fix loop iteration limit (default: 5)')
    parser.add_argument('--max-review-cycles', type=int, default=3,
                        help='Review-fix cycle limit (default: 3)')

    args = parser.parse_args()

    # Handle SIGTERM and SIGINT for graceful shutdown
    def handle_signal(signum, frame):
        sig_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
        exit_code = 143 if signum == signal.SIGTERM else 130
        print(f"\n{sig_name} received, shutting down...", file=sys.stderr)
        sys.exit(exit_code)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        total_start = time.time()

        if args.phase == 'plan':
            result = run_phase_plan(args.query_or_path, args.project, skip_refinement=args.no_refine)
            print_result(result, args.json)

        elif args.phase == 'implement':
            config = ImplementConfig(
                max_turns=args.max_turns,
                max_fix_iterations=args.max_fix_iterations,
                max_review_cycles=args.max_review_cycles,
            )
            result = run_phase_implement(
                args.query_or_path, args.project,
                research_path=args.research or '',
                config=config,
            )
            print_result(result, args.json)

        elif args.phase == 'cleanup':
            result = run_phase_cleanup(
                args.query_or_path,
                args.research or '',
                args.review or '',
                args.project
            )
            print_result(result, args.json)

        elif args.phase == 'all':
            # Run all phases sequentially
            # Non-interactive mode for full run - only commit step remains interactive
            plan_result = run_phase_plan(args.query_or_path, args.project,
                                         skip_refinement=args.no_refine,
                                         non_interactive=True)
            print_result(plan_result, args.json)

            config = ImplementConfig(
                max_turns=args.max_turns,
                max_fix_iterations=args.max_fix_iterations,
                max_review_cycles=args.max_review_cycles,
            )
            implement_result = run_phase_implement(
                plan_result.plan_path, args.project,
                research_path=plan_result.research_path,
                config=config,
            )
            print_result(implement_result, args.json)

            cleanup_result = run_phase_cleanup(
                plan_result.plan_path,
                plan_result.research_path,
                implement_result.review_path,
                args.project
            )
            print_result(cleanup_result, args.json)

        total_elapsed = time.time() - total_start
        print(f"\n{Fore.BLUE}Total time:{Style.RESET_ALL} {format_duration(total_elapsed)}", file=sys.stderr)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
