#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "colorama>=0.4.6",
# ]
# ///
"""
Ralph Orchestrator — Autonomous implementation with build → review → fix cycles.

Companion to the existing orchestrator. Two phases:
  --convert:   Transform an approved plan into a comprehensive Ralph prompt
  --implement: Run the Ralph loop (build → review → fix)

Workflow:
    orch --phase plan "Add feature"                           # Existing orchestrator
    orch-ralph --convert memories/shared/plans/plan.md        # Plan → Ralph prompt
    orch-ralph --implement memories/shared/ralph/prompt.md    # Ralph loop + review
    orch --phase cleanup memories/shared/plans/plan.md        # Existing orchestrator

Usage:
    uv run .claude/helpers/ralph_orchestrator.py --convert <plan-path>
    uv run .claude/helpers/ralph_orchestrator.py --implement <prompt-path>
    uv run .claude/helpers/ralph_orchestrator.py --convert-and-implement <plan-path>

Aliases: Add to ~/.zshrc or ~/.bashrc:
    alias orch-ralph='uv run .claude/helpers/ralph_orchestrator.py'
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
from dataclasses import dataclass
from pathlib import Path

from colorama import Fore, Style, init

# Initialize colorama
init()

# Color mapping for stages
STAGE_COLORS = {
    'Indexing': Fore.CYAN,
    'Convert': Fore.MAGENTA,
    'Build': Fore.GREEN,
    'Review': Fore.BLUE,
    'Fix': Fore.YELLOW,
    'Cleanup': Fore.YELLOW,
}

# Map index file suffixes to indexer scripts
INDEXER_MAP = {
    '_py.md': 'index_python.py',
    '_js_ts.md': 'index_js_ts.py',
    '_go.md': 'index_go.py',
    '_cpp.md': 'index_cpp.py',
}


# --- Result dataclasses ---

@dataclass
class BuildResult:
    """Result from a build/fix loop."""
    success: bool
    iterations: int
    pre_commit: str


@dataclass
class RalphConfig:
    """Configuration for the ralph implement phase."""
    max_iterations: int = 10
    max_turns: int = 40
    max_fix_iterations: int = 5
    max_review_cycles: int = 3
    plan_path: str = ''
    prompt_path: str = ''
    research_path: str = ''
    test_cmd: str = ''
    lint_cmd: str = ''
    codebase_index: str = ''


# --- Utility functions (duplicated from orchestrator.py — can't import uv scripts) ---

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

    if event_type == 'system' and event.get('subtype') == 'init':
        return None

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

    if event_type == 'result':
        result_text = event.get('result', '')
        if result_text:
            return f"\n{Fore.GREEN}✓ Done{Style.RESET_ALL}\n"
        return None

    return None


def run_claude_command(command: list[str], cwd: str, timeout: int = 600,
                       phase: str = '') -> tuple[int, str, float]:
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
        process.wait()  # Reap the process to avoid zombies
        elapsed = time.time() - start_time
        raise RuntimeError(f"Command timed out after {format_duration(elapsed)}")

    elapsed = time.time() - start_time
    returncode = process.returncode if process.returncode is not None else 1
    return returncode, ''.join(output_lines), elapsed


def find_codebase_index(project_path: str) -> str | None:
    """Find the most recent codebase index file."""
    codebase_dir = Path(project_path) / 'memories' / 'codebase'
    if not codebase_dir.exists():
        return None

    index_files = list(codebase_dir.glob('codebase_overview_*.md'))
    if not index_files:
        return None

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


# --- Convert phase ---

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


def generate_ralph_prompt(plan_path: str, project_path: str) -> str:
    """Generate a Ralph prompt from a plan file.

    Returns the path to the generated prompt file.
    """
    plan_file = Path(project_path) / plan_path
    if not plan_file.exists():
        raise RuntimeError(f"Plan file not found: {plan_path}")

    content = plan_file.read_text(encoding='utf-8')
    sections = extract_plan_sections(content)

    # Detect tooling
    test_cmd, lint_cmd, format_cmd = detect_tooling(project_path)

    # Find codebase index
    index_path = find_codebase_index(project_path)
    if index_path:
        index_rel = os.path.relpath(index_path, project_path)
    else:
        index_rel = 'memories/codebase/ (run /index_codebase first)'

    # Build prompt
    prompt = f"""# {sections['title']} — Implementation

You are implementing an approved plan. Work through the tasks systematically.

## Project Context
- **Codebase index**: `{index_rel}`
- **Test command**: `{test_cmd}`
- **Lint command**: `{lint_cmd}`
- **Format command**: `{format_cmd}`

## Before You Start
1. Read `{index_rel}` for the full project map.
2. Run `git log --oneline -20` to see what has already been committed. Skip completed tasks.
3. Run `{test_cmd}` to verify baseline.
4. Run `{lint_cmd}` to verify baseline.

"""
    # Add overview if present
    if sections['overview']:
        prompt += f"""## Overview

{sections['overview']}

"""

    # Add tasks
    prompt += f"""## Your Tasks

{sections['phases']}

"""

    # Add files section if extracted
    if sections['files']:
        prompt += f"""## Key Files

{sections['files']}

"""

    # Add rules
    prompt += f"""## Rules

### Testing & Linting
1. Run tests after every change: `{test_cmd}`
2. Run linter after every change: `{lint_cmd}`
3. Fix failures before moving on
4. Do not delete or break existing functionality

### Self-Review Before Committing
- Correctness — edge cases handled?
- Security — input validation, no injection, no credential exposure
- Performance — no N+1 queries, unbounded loops
- Simplicity — avoid over-engineering

### Commit Style
Use Conventional Commits. One commit per sub-task:
```
git add -A && git commit -m "<type>: <description>"
```

## Completion Criteria
"""

    # Add plan criteria
    if sections['criteria']:
        prompt += sections['criteria'] + '\n'
    else:
        prompt += '- [ ] All plan tasks completed\n'

    prompt += f"""- [ ] All tests pass (`{test_cmd}`)
- [ ] Linter passes (`{lint_cmd}`)
- [ ] Each sub-task committed to git

## When You Are Done
When ALL completion criteria are met, output exactly:
RALPH_DONE
"""

    # Save to memories/shared/ralph/
    ralph_dir = Path(project_path) / 'memories' / 'shared' / 'ralph'
    ralph_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from plan path
    plan_stem = plan_file.stem  # e.g., 2026-02-08-feature
    date = time.strftime('%Y-%m-%d')
    # Use plan stem if it starts with a date, otherwise prepend today's date
    if re.match(r'\d{4}-\d{2}-\d{2}', plan_stem):
        slug = plan_stem
    else:
        slug = f'{date}-{plan_stem}'

    prompt_filename = f'{slug}-prompt.md'
    prompt_path = ralph_dir / prompt_filename
    prompt_path.write_text(prompt, encoding='utf-8')

    rel_path = os.path.relpath(prompt_path, project_path)
    return rel_path


# --- Implement phase ---

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


def run_build_loop(prompt_path: str, project_path: str,
                   max_iterations: int, max_turns: int,
                   phase_name: str = 'Build',
                   pre_commit: str | None = None) -> BuildResult:
    """Run the Ralph build loop: iterate Claude with the prompt until RALPH_DONE.

    Args:
        pre_commit: If provided, use this as the pre-loop commit hash instead of
                    snapshotting HEAD. Used by fix loop to preserve the original
                    build baseline.

    Returns BuildResult with success status and iteration count.
    """
    pre_ralph_commit = pre_commit or git_rev_parse_head(project_path)
    prompt_content = Path(project_path, prompt_path).read_text(encoding='utf-8')

    log_dir = Path(project_path) / 'ralph-logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, max_iterations + 1):
        stream_progress(phase_name, f'Iteration {i}/{max_iterations}')

        # Refresh existing indexes (cheap — direct indexer, no Claude call)
        refresh_codebase_indexes(project_path)

        # Run Claude iteration
        returncode, output, elapsed = run_claude_command(
            ['claude-safe', '--no-firewall', '--', '-p', prompt_content,
             '--max-turns', str(max_turns)],
            cwd=project_path,
            timeout=900,
            phase=f'{phase_name} ({i}/{max_iterations})'
        )

        # Log raw output
        log_path = log_dir / f'{phase_name.lower()}-{i}.log'
        log_path.write_text(output, encoding='utf-8')

        stream_progress(phase_name,
                        f'Iteration {i} complete ({format_duration(elapsed)}, exit={returncode})')

        # Check completion signal
        if 'RALPH_DONE' in output:
            stream_progress(phase_name, f'RALPH_DONE detected at iteration {i}')
            return BuildResult(success=True, iterations=i, pre_commit=pre_ralph_commit)

    stream_progress(phase_name, f'Reached max iterations ({max_iterations}) without RALPH_DONE')
    return BuildResult(success=False, iterations=max_iterations, pre_commit=pre_ralph_commit)


def run_review(project_path: str, build_result: BuildResult,
               config: RalphConfig, review_cycle: int) -> str:
    """Run a code review on changes since pre_ralph_commit.

    Returns 'REVIEW_PASS', 'REVIEW_NEEDS_FIXES', or 'REVIEW_UNKNOWN'.
    """
    stream_progress('Review', f'Review cycle {review_cycle}/{config.max_review_cycles}')

    # Generate diff into ralph-logs/ to avoid accidental commits from git add -A
    log_dir = Path(project_path) / 'ralph-logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    diff_file = log_dir / 'RALPH_DIFF.patch'
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
    if config.prompt_path:
        context_files.append(f'- Ralph prompt/specs: `{config.prompt_path}`')
    context_files.append(f'- Diff: `{diff_rel}`')
    context_section = '\n'.join(context_files)

    # REVIEW.md also goes in ralph-logs/ to avoid accidental commits
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
1. Read the plan, research, and prompt files listed above.
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


def run_fix_loop(project_path: str, config: RalphConfig,
                 pre_commit: str) -> BuildResult:
    """Run the fix loop to address review findings.

    Creates a fix prompt from REVIEW.md and runs a ralph loop.
    pre_commit is the original build baseline, preserved across fix iterations.
    """
    review_md_rel = os.path.relpath(
        Path(project_path) / 'ralph-logs' / 'REVIEW.md', project_path
    )
    fix_prompt = f"""You are fixing issues identified in a code review.

## Before You Start
1. Read `{review_md_rel}` for the review findings.
2. Read the codebase index at `{config.codebase_index}`.
3. Run tests: `{config.test_cmd}`
4. Run linter: `{config.lint_cmd}`

## Fix Priority
1. Critical Issues — MUST fix
2. Improvements — SHOULD fix
3. Minor Notes — SKIP

## Rules
- Run tests after every change: `{config.test_cmd}`
- Run linter after every change: `{config.lint_cmd}`
- Fix failures before moving on
- Commit each fix: `git add -A && git commit -m "fix: <description>"`

## When Done
When all Critical Issues and Improvements are fixed, tests pass, linter passes:
RALPH_DONE
"""

    # Save fix prompt to a temp file
    fix_prompt_path = Path(project_path) / 'ralph-logs' / 'fix-prompt.md'
    fix_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    fix_prompt_path.write_text(fix_prompt, encoding='utf-8')

    fix_rel = os.path.relpath(fix_prompt_path, project_path)

    return run_build_loop(
        fix_rel, project_path,
        max_iterations=config.max_fix_iterations,
        max_turns=config.max_turns,
        phase_name='Fix',
        pre_commit=pre_commit,
    )


def save_review_with_frontmatter(project_path: str, review_cycle: int) -> str | None:
    """Save REVIEW.md with proper frontmatter to memories/shared/reviews/.

    Returns path to saved review, or None on failure.
    """
    review_file = Path(project_path) / 'ralph-logs' / 'REVIEW.md'
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
    filename = f'code-review-{date_str}-ralph-iter{review_cycle}.md'

    frontmatter = f"""---
date: {date}
file-id: {uuid}
claude-sessionid: {session_id}
reviewer: ralph-orchestrator
git_commit: {git_commit}
branch: {branch}
repository: {repo_name}
review_type: ralph_review
review_iteration: {review_cycle}
tags: [code-review, ralph, automated]
status: complete
last_updated: {time.strftime('%Y-%m-%d %H:%M')}
last_updated_by: ralph-orchestrator
---

"""

    # Save to memories/shared/reviews/
    reviews_dir = Path(project_path) / 'memories' / 'shared' / 'reviews'
    reviews_dir.mkdir(parents=True, exist_ok=True)

    output_path = reviews_dir / filename
    output_path.write_text(frontmatter + review_content, encoding='utf-8')

    return os.path.relpath(output_path, project_path)


def _cleanup_ralph_artifacts(project_path: str) -> None:
    """Remove transient ralph artifacts (diff, review) from ralph-logs/ after archiving."""
    log_dir = Path(project_path) / 'ralph-logs'
    for name in ('RALPH_DIFF.patch', 'REVIEW.md', 'fix-prompt.md'):
        artifact = log_dir / name
        if artifact.exists():
            artifact.unlink()


def run_ralph_implement(prompt_path: str, project_path: str, config: RalphConfig) -> None:
    """Run the full Ralph implement phase: index → build → review → fix cycle."""

    # Step 1: Initial index via Claude (smart detection, full context)
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

    # Step 2: Build loop
    build_result = run_build_loop(
        prompt_path, project_path,
        max_iterations=config.max_iterations,
        max_turns=config.max_turns,
        phase_name='Build'
    )

    if not build_result.success:
        stream_progress('Build', 'Build loop did not complete — proceeding to review anyway')

    # Step 3-5: Review-fix cycle
    for cycle in range(1, config.max_review_cycles + 1):
        # Step 3: Review
        verdict = run_review(project_path, build_result, config, cycle)

        # Archive the review
        review_path = save_review_with_frontmatter(project_path, cycle)
        if review_path:
            stream_progress('Review', f'Saved review: {review_path}')

        # Check verdict
        if verdict == 'REVIEW_PASS':
            _cleanup_ralph_artifacts(project_path)
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Ralph Complete!{Style.RESET_ALL}",
                  file=sys.stderr, flush=True)
            print(f"  Review passed on cycle {cycle}", file=sys.stderr, flush=True)
            _print_summary(project_path, build_result, cycle, 'PASS')
            return

        # Skip fix on last cycle
        if cycle == config.max_review_cycles:
            stream_progress('Review',
                            f'Final review cycle ({cycle}) still has issues. Manual review needed.')
            break

        # Step 4: Fix loop
        stream_progress('Fix', f'Fixing issues from review cycle {cycle}...')
        fix_result = run_fix_loop(project_path, config, build_result.pre_commit)

        if fix_result.success:
            stream_progress('Fix', f'Fix loop complete at iteration {fix_result.iterations}')
        else:
            stream_progress('Fix', 'Fix loop did not complete — continuing to next review')

    # Clean up transient artifacts (review is already archived to memories/shared/reviews/)
    _cleanup_ralph_artifacts(project_path)

    # Final summary
    _print_summary(project_path, build_result, config.max_review_cycles, 'NEEDS_REVIEW')


def _print_summary(project_path: str, build_result: BuildResult,
                   review_cycles: int, status: str) -> None:
    """Print final summary."""
    try:
        current_commit = git_rev_parse_head(project_path)
    except RuntimeError:
        current_commit = 'unknown'

    # Count commits since pre-ralph
    result = subprocess.run(
        ['git', 'log', f'{build_result.pre_commit}..HEAD', '--oneline'],
        cwd=project_path, capture_output=True, text=True
    )
    commit_count = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0

    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}", file=sys.stderr, flush=True)
    print(f"\n{Fore.GREEN}{Style.BRIGHT}  Ralph Summary{Style.RESET_ALL}\n", file=sys.stderr, flush=True)
    print(f"  Status:          {status}", file=sys.stderr, flush=True)
    print(f"  Build iterations: {build_result.iterations}", file=sys.stderr, flush=True)
    print(f"  Review cycles:   {review_cycles}", file=sys.stderr, flush=True)
    print(f"  Commits made:    {commit_count}", file=sys.stderr, flush=True)
    print(f"  Pre-ralph:       {build_result.pre_commit[:8]}", file=sys.stderr, flush=True)
    print(f"  Current HEAD:    {current_commit[:8]}", file=sys.stderr, flush=True)
    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)

    if status == 'NEEDS_REVIEW':
        print(f"  {Fore.YELLOW}Review REVIEW.md for remaining issues{Style.RESET_ALL}",
              file=sys.stderr, flush=True)

    print(f"  {Fore.BLUE}Next:{Style.RESET_ALL} orch --phase cleanup <plan-path>",
          file=sys.stderr, flush=True)


# --- Main entry point ---

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Ralph Orchestrator — Autonomous implementation with build/review/fix cycles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --convert memories/shared/plans/plan.md
  %(prog)s --implement memories/shared/ralph/prompt.md
  %(prog)s --convert-and-implement memories/shared/plans/plan.md
  %(prog)s --implement --max-iterations 20 --max-turns 30 prompt.md
        """
    )

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--convert', metavar='PLAN_PATH',
                        help='Convert a plan file to a Ralph prompt')
    action.add_argument('--implement', metavar='PROMPT_PATH',
                        help='Run the Ralph build/review/fix loop')
    action.add_argument('--convert-and-implement', metavar='PLAN_PATH',
                        dest='convert_and_implement',
                        help='Convert plan then run Ralph loop')

    parser.add_argument('--project', default='.', help='Project directory (default: .)')
    parser.add_argument('--max-iterations', type=int, default=10,
                        help='Build loop iteration limit (default: 10)')
    parser.add_argument('--max-turns', type=int, default=40,
                        help='Turns per Claude iteration (default: 25)')
    parser.add_argument('--max-fix-iterations', type=int, default=5,
                        help='Fix loop iteration limit (default: 5)')
    parser.add_argument('--max-review-cycles', type=int, default=3,
                        help='Review-fix cycle limit (default: 3)')
    parser.add_argument('--plan', help='Plan file to reference in review context (for --implement)')
    parser.add_argument('--research', help='Research file to reference in review')

    args = parser.parse_args()

    # Handle signals
    def handle_signal(signum, frame):
        sig_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
        exit_code = 143 if signum == signal.SIGTERM else 130
        print(f"\n{sig_name} received, shutting down...", file=sys.stderr)
        sys.exit(exit_code)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        total_start = time.time()
        project_path = os.path.abspath(args.project)

        if args.convert:
            # Convert phase only
            stream_progress('Convert', f'Converting plan: {args.convert}')
            prompt_path = generate_ralph_prompt(args.convert, project_path)
            stream_progress('Convert', f'Generated prompt: {prompt_path}')
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Prompt generated:{Style.RESET_ALL} {prompt_path}")
            print(f"\n  {Fore.BLUE}Next:{Style.RESET_ALL} orch-ralph --implement {prompt_path}")

        elif args.implement:
            # Implement phase only
            config = RalphConfig(
                max_iterations=args.max_iterations,
                max_turns=args.max_turns,
                max_fix_iterations=args.max_fix_iterations,
                max_review_cycles=args.max_review_cycles,
                plan_path=args.plan or '',
                prompt_path=args.implement,
                research_path=args.research or '',
            )

            # Detect tooling
            test_cmd, lint_cmd, _ = detect_tooling(project_path)
            config.test_cmd = test_cmd
            config.lint_cmd = lint_cmd

            run_ralph_implement(args.implement, project_path, config)

        elif args.convert_and_implement:
            # Convert + implement
            stream_progress('Convert', f'Converting plan: {args.convert_and_implement}')
            prompt_path = generate_ralph_prompt(args.convert_and_implement, project_path)
            stream_progress('Convert', f'Generated prompt: {prompt_path}')

            config = RalphConfig(
                max_iterations=args.max_iterations,
                max_turns=args.max_turns,
                max_fix_iterations=args.max_fix_iterations,
                max_review_cycles=args.max_review_cycles,
                plan_path=args.convert_and_implement,
                prompt_path=prompt_path,
                research_path=args.research or '',
            )

            test_cmd, lint_cmd, _ = detect_tooling(project_path)
            config.test_cmd = test_cmd
            config.lint_cmd = lint_cmd

            run_ralph_implement(prompt_path, project_path, config)

        total_elapsed = time.time() - total_start
        print(f"\n{Fore.BLUE}Total time:{Style.RESET_ALL} {format_duration(total_elapsed)}",
              file=sys.stderr)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
