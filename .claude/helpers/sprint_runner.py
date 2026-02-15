#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "colorama>=0.4.6",
# ]
# ///
"""
Sprint Runner with Reflection Loop

Picks tasks from todo.md, runs the orchestrator for each, and runs a reflection
phase after each run to consolidate learnings into project memory.

Flow per item:
    1. Parse todo.md → find next actionable item
    2. Enrich query (project.md + decisions.md context)
    3. orch --phase plan "enriched query"
    4. Micro-reflect → append to scratchpad.md
    5. orch --phase implement plan.md
    6. Micro-reflect → append to scratchpad.md
    7. orch --phase cleanup plan.md
    8. Consolidate: scratchpad.md → decisions.md
    9. Update todo.md / done.md
   10. Checkpoint → show summary, ask to continue

Usage:
    uv run .claude/helpers/sprint_runner.py
    uv run .claude/helpers/sprint_runner.py --max-items 3
    uv run .claude/helpers/sprint_runner.py --dry-run
    uv run .claude/helpers/sprint_runner.py --skip-reflection

Aliases: Add to ~/.zshrc or ~/.bashrc:
    alias sprint='uv run .claude/helpers/sprint_runner.py'
    alias sprint-dry='uv run .claude/helpers/sprint_runner.py --dry-run'
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
    'Sprint': Fore.MAGENTA,
    'Todo': Fore.CYAN,
    'Enrich': Fore.YELLOW,
    'Plan': Fore.MAGENTA,
    'Implement': Fore.GREEN,
    'Cleanup': Fore.YELLOW,
    'Reflect': Fore.BLUE,
    'Consolidate': Fore.CYAN,
    'Checkpoint': Fore.WHITE,
    'Error': Fore.RED,
}


# --- Data classes ---

@dataclass
class TodoItem:
    text: str               # "Add rate limiting to API endpoints"
    priority: str            # 'must_have' | 'should_have' | 'could_have'
    category: str            # 'features' | 'bugs' | 'improvements' | 'technical'
    is_blocked: bool
    dependencies: list[str]  # ["user authentication"]
    line_number: int         # For surgical editing of todo.md

    def __str__(self) -> str:
        prefix = '[BLOCKED] ' if self.is_blocked else ''
        return f"{prefix}{self.text} ({self.priority}/{self.category})"


@dataclass
class SprintResult:
    todo_item: TodoItem
    plan_path: str = ''
    review_path: str = ''
    decisions_added: int = 0
    completed: bool = False
    error: str = ''


# --- Utility functions ---

def stream_progress(stage: str, message: str) -> None:
    """Print progress update to stderr for real-time feedback."""
    color = STAGE_COLORS.get(stage, Fore.WHITE)
    if 'FAILED' in message or 'Error' in message:
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


def print_phase_header(phase_name: str) -> None:
    """Print a prominent phase header with separators."""
    color = STAGE_COLORS.get(phase_name, Fore.WHITE)
    print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}", file=sys.stderr, flush=True)
    print(f"\n{color}  {phase_name}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)
    print(f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)


# --- Todo parsing ---

def parse_todo(path: Path) -> list[TodoItem]:
    """Parse todo.md into list of TodoItem dataclasses.

    Extracts priority section, category, blocked status, dependencies, and line number.
    Expected format: MoSCoW sections (## Must Haves, ## Should Haves, ## Could Haves)
    with category sub-sections (### Features, ### Bugs, etc.)
    Items are markdown checkboxes: - [ ] item text or - [x] completed item
    """
    if not path.exists():
        return []

    content = path.read_text(encoding='utf-8')
    lines = content.splitlines()

    items: list[TodoItem] = []
    current_priority = 'should_have'
    current_category = 'features'

    # Map section headings to priority levels
    priority_map = {
        'must have': 'must_have',
        'must haves': 'must_have',
        'should have': 'should_have',
        'should haves': 'should_have',
        'could have': 'could_have',
        'could haves': 'could_have',
    }

    # Map category headings
    category_map = {
        'feature': 'features',
        'features': 'features',
        'bug': 'bugs',
        'bugs': 'bugs',
        'fix': 'bugs',
        'fixes': 'bugs',
        'improvement': 'improvements',
        'improvements': 'improvements',
        'technical': 'technical',
        'tech debt': 'technical',
        'technical debt': 'technical',
        'infrastructure': 'technical',
    }

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Detect priority sections (## headings)
        if stripped.startswith('## '):
            heading = stripped[3:].strip().lower()
            for key, val in priority_map.items():
                if key in heading:
                    current_priority = val
                    break

        # Detect category sub-sections (### headings)
        elif stripped.startswith('### '):
            heading = stripped[4:].strip().lower()
            for key, val in category_map.items():
                if key in heading:
                    current_category = val
                    break

        # Detect unchecked todo items (- [ ] text)
        elif re.match(r'^[-*]\s+\[ \]\s+', stripped):
            # Extract the item text
            text = re.sub(r'^[-*]\s+\[ \]\s+', '', stripped)

            # Check for [BLOCKED] prefix
            is_blocked = '[BLOCKED]' in text.upper()
            text = re.sub(r'\[BLOCKED\]\s*', '', text, flags=re.IGNORECASE).strip()

            # Extract dependencies: (requires: X, Y) or (depends on: X)
            dependencies: list[str] = []
            dep_match = re.search(r'\((?:requires|depends on|depends|needs):\s*([^)]+)\)', text, re.IGNORECASE)
            if dep_match:
                dep_text = dep_match.group(1)
                dependencies = [d.strip() for d in dep_text.split(',') if d.strip()]
                # Remove the dependency annotation from text
                text = re.sub(r'\s*\((?:requires|depends on|depends|needs):[^)]+\)', '', text, flags=re.IGNORECASE).strip()

            items.append(TodoItem(
                text=text,
                priority=current_priority,
                category=current_category,
                is_blocked=is_blocked,
                dependencies=dependencies,
                line_number=line_num,
            ))

    return items


def find_next_actionable(items: list[TodoItem], done_path: Path) -> TodoItem | None:
    """Filter out checked/blocked items, check dependencies against done.md.

    Returns highest-priority topmost item.
    """
    # Load done items for dependency checking
    done_items: set[str] = set()
    if done_path.exists():
        done_content = done_path.read_text(encoding='utf-8').lower()
        # Extract completed item descriptions
        for match in re.finditer(r'[-*]\s+\[x\]\s+(.+)', done_content):
            done_items.add(match.group(1).strip().lower())

    # Priority order
    priority_order = {'must_have': 0, 'should_have': 1, 'could_have': 2}

    # Filter actionable items
    actionable = []
    for item in items:
        if item.is_blocked:
            continue

        # Check if dependencies are met
        deps_met = True
        for dep in item.dependencies:
            dep_lower = dep.lower()
            # Check if any done item contains this dependency text
            if not any(dep_lower in done for done in done_items):
                deps_met = False
                break

        if not deps_met:
            continue

        actionable.append(item)

    if not actionable:
        return None

    # Sort by priority (must_have first), then by line number (topmost first)
    actionable.sort(key=lambda i: (priority_order.get(i.priority, 9), i.line_number))
    return actionable[0]


# --- Query enrichment ---

def enrich_query(item: TodoItem, project_path: str) -> str:
    """Read project.md + decisions.md and formulate an enriched query.

    Uses Claude (via subprocess) to create a 4-8 sentence enriched query
    from the todo item + project context.
    """
    project_dir = Path(project_path)
    project_md = project_dir / 'memories' / 'shared' / 'project' / 'project.md'
    decisions_md = project_dir / 'memories' / 'shared' / 'project' / 'decisions.md'

    # Build context from available files
    context_parts = []

    if project_md.exists():
        content = project_md.read_text(encoding='utf-8')
        # Take first 4000 chars for context
        context_parts.append(f"## Project Context (from project.md):\n{content[:4000]}")

    if decisions_md.exists():
        content = decisions_md.read_text(encoding='utf-8')
        # decisions.md is the primary feedback loop — include generously
        context_parts.append(f"## Project Decisions (from decisions.md):\n{content[:12000]}")

    if not context_parts:
        # No context files — return the raw item text
        stream_progress('Enrich', 'No project context files found, using raw query')
        return item.text

    context = '\n\n'.join(context_parts)

    prompt = f"""You are enriching a todo item with project context for an AI coding assistant.

## Todo Item:
{item.text}
Priority: {item.priority}
Category: {item.category}

## Project Context:
{context}

## Instructions:
Write a 4-8 sentence enriched query that includes:
1. The original task clearly stated
2. Relevant tech stack and architecture context from project.md (2-3 sentences)
3. Any relevant existing decisions, constraints, or conventions from decisions.md
4. Dependency information if applicable

Output ONLY the enriched query text, nothing else. No markdown formatting, no headers."""

    try:
        result = subprocess.run(
            ['claude', '-p', prompt, '--max-turns', '1', '--output-format', 'text'],
            cwd=project_path, capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            enriched = result.stdout.strip()
            stream_progress('Enrich', f'Enriched query: {enriched[:100]}...')
            return enriched
    except (subprocess.TimeoutExpired, OSError) as e:
        stream_progress('Enrich', f'Warning: Enrichment failed ({e}), using raw query')

    return item.text


# --- Orchestrator invocation ---

def run_phase(phase: str, args: list[str], project_path: str,
              max_turns: int = 40, max_review_cycles: int = 3) -> tuple[int, str, float]:
    """Invoke orchestrator.py --phase <plan|implement|cleanup> --json.

    Returns (returncode, stdout, elapsed_seconds).
    """
    helpers_dir = Path(project_path) / '.claude' / 'helpers'
    orchestrator = helpers_dir / 'orchestrator.py'

    cmd = ['uv', 'run', str(orchestrator),
           '--phase', phase,
           '--json',
           '--project', project_path,
           '--max-turns', str(max_turns),
           '--max-review-cycles', str(max_review_cycles)]

    # Add phase-specific flags
    if phase == 'plan':
        cmd.append('--no-refine')  # Query is already enriched

    cmd.extend(args)

    stream_progress(phase.capitalize(), f'Running orchestrator --phase {phase}...')
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd, cwd=project_path,
            capture_output=True, text=True,
            timeout=2400,  # 40 minutes max per phase
        )
        elapsed = time.time() - start_time
        stream_progress(phase.capitalize(),
                        f'Complete ({format_duration(elapsed)}, exit={result.returncode})')
        return result.returncode, result.stdout, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        stream_progress(phase.capitalize(), f'TIMEOUT after {format_duration(elapsed)}')
        return 1, '', elapsed


# --- Micro-reflection ---

def micro_reflect(phase: str, plan_path: str, project_path: str,
                  research_path: str = '', review_path: str = '') -> bool:
    """Lightweight Claude call that appends raw observations to scratchpad.md.

    Fast, append-only. Called after plan and implement phases.
    Returns True on success.
    """
    stream_progress('Reflect', f'Running micro-reflection after {phase} phase...')

    # Build the reflect command args
    reflect_args = plan_path
    if research_path:
        reflect_args += f' {research_path}'
    if review_path:
        reflect_args += f' {review_path}'

    try:
        result = subprocess.run(
            ['claude', '-p', f'/reflect {reflect_args}',
             '--max-turns', '5', '--output-format', 'text'],
            cwd=project_path,
            capture_output=True, text=True,
            timeout=180,
        )
        if result.returncode == 0:
            stream_progress('Reflect', 'Observations appended to scratchpad.md')
            return True
        else:
            stream_progress('Reflect', f'Warning: Reflection returned code {result.returncode}')
            return False
    except (subprocess.TimeoutExpired, OSError) as e:
        stream_progress('Reflect', f'Warning: Reflection failed ({e})')
        return False


# --- Consolidation ---

def consolidate_memory(project_path: str) -> bool:
    """Claude call that reads scratchpad.md + decisions.md and integrates.

    Slow, deliberate. Called after all phases of one sprint item.
    Returns True on success.
    """
    stream_progress('Consolidate', 'Integrating scratchpad into decisions.md...')

    scratchpad = Path(project_path) / 'memories' / 'shared' / 'project' / 'scratchpad.md'
    if not scratchpad.exists() or not scratchpad.read_text(encoding='utf-8').strip():
        stream_progress('Consolidate', 'Scratchpad is empty, nothing to consolidate')
        return True

    try:
        result = subprocess.run(
            ['claude', '-p', '/consolidate_memory',
             '--max-turns', '10', '--output-format', 'text'],
            cwd=project_path,
            capture_output=True, text=True,
            timeout=300,
        )
        if result.returncode == 0:
            stream_progress('Consolidate', 'Successfully integrated into decisions.md')
            return True
        else:
            stream_progress('Consolidate', f'Warning: Consolidation returned code {result.returncode}')
            return False
    except (subprocess.TimeoutExpired, OSError) as e:
        stream_progress('Consolidate', f'Warning: Consolidation failed ({e})')
        return False


# --- Todo/Done updates ---

def update_todo_done(item: TodoItem, plan_path: str, project_path: str,
                     new_tasks: list[str] | None = None) -> None:
    """Check off completed item in todo.md, add to done.md with traceability."""
    project_dir = Path(project_path)
    todo_path = project_dir / 'memories' / 'shared' / 'project' / 'todo.md'
    done_path = project_dir / 'memories' / 'shared' / 'project' / 'done.md'

    # Update todo.md — check off the item
    if todo_path.exists():
        content = todo_path.read_text(encoding='utf-8')
        lines = content.splitlines()

        if 1 <= item.line_number <= len(lines):
            line = lines[item.line_number - 1]
            # Replace [ ] with [x]
            updated_line = re.sub(r'\[ \]', '[x]', line, count=1)
            lines[item.line_number - 1] = updated_line

        # Add newly discovered tasks at the end of the appropriate section
        if new_tasks:
            # Find the end of the current priority section to append
            lines.append('')
            lines.append(f'<!-- Discovered during sprint: {item.text[:50]} -->')
            for task in new_tasks:
                lines.append(f'- [ ] {task}')

        todo_path.write_text('\n'.join(lines), encoding='utf-8')
        stream_progress('Todo', f'Checked off: {item.text[:60]}')

    # Update done.md — add the completed item
    if done_path.exists():
        content = done_path.read_text(encoding='utf-8')
    else:
        done_path.parent.mkdir(parents=True, exist_ok=True)
        content = '# Done\n\n'

    date_str = time.strftime('%Y-%m-%d')
    month_section = time.strftime('## %Y-%m (%B %Y)')

    # Build the entry
    entry = f'- [x] {item.text} ({date_str})\n'
    if plan_path:
        entry += f'  - Plan: `{plan_path}`\n'

    # Check if month section exists
    if month_section not in content:
        content += f'\n{month_section}\n'

    # Add the completed item under the category header within the month section
    category_header = f'### {item.category.replace("_", " ").title()}'
    if category_header not in content:
        content += f'\n{category_header}\n{entry}'
    else:
        # Insert entry right after the category header
        pos = content.rfind(category_header)
        insert_at = pos + len(category_header)
        # Skip past the newline after the header
        if insert_at < len(content) and content[insert_at] == '\n':
            insert_at += 1
        content = content[:insert_at] + entry + content[insert_at:]
    done_path.write_text(content, encoding='utf-8')
    stream_progress('Todo', f'Added to done.md: {item.text[:60]}')


# --- Checkpoint ---

def show_checkpoint(result: SprintResult, item_num: int) -> bool:
    """Display summary and ask user whether to continue.

    Returns True to continue, False to stop.
    """
    print_phase_header('Checkpoint')

    status = f"{Fore.GREEN}completed{Style.RESET_ALL}" if result.completed else f"{Fore.RED}failed{Style.RESET_ALL}"

    print(f"  Item #{item_num}: {status}", file=sys.stderr, flush=True)
    print(f"  Task: {result.todo_item.text[:70]}", file=sys.stderr, flush=True)
    if result.plan_path:
        print(f"  Plan: {result.plan_path}", file=sys.stderr, flush=True)
    if result.error:
        print(f"  {Fore.RED}Error: {result.error}{Style.RESET_ALL}", file=sys.stderr, flush=True)

    print(f"\n{Fore.BLUE}{'─' * 40}{Style.RESET_ALL}", file=sys.stderr, flush=True)

    # Ask user
    if not sys.stdin.isatty():
        # Non-interactive: always continue
        return True

    try:
        response = input(f"\n  {Fore.WHITE}Continue to next item? [Y/n/r(etry)]: {Style.RESET_ALL}").strip().lower()
        if response in ('n', 'no', 'stop', 'q', 'quit'):
            return False
        # 'r' or 'retry' would need special handling — for now treat as continue
        return True
    except (EOFError, KeyboardInterrupt):
        return False


# --- Extract paths from orchestrator JSON output ---

def extract_orch_result(output: str) -> dict:
    """Parse JSON output from orchestrator --json."""
    # Try to find JSON in the output (may be mixed with stderr)
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    # Try the whole output as JSON
    try:
        return json.loads(output.strip())
    except (json.JSONDecodeError, ValueError):
        return {}


# --- Main sprint loop ---

def run_sprint(
    project_path: str,
    max_items: int = 0,
    max_turns: int = 40,
    max_review_cycles: int = 3,
    skip_reflection: bool = False,
    dry_run: bool = False,
    output_json: bool = False,
) -> list[SprintResult]:
    """Main sprint loop: parse todo → enrich → orch → reflect → consolidate → repeat."""

    project_dir = Path(project_path)
    todo_path = project_dir / 'memories' / 'shared' / 'project' / 'todo.md'
    done_path = project_dir / 'memories' / 'shared' / 'project' / 'done.md'

    if not todo_path.exists():
        stream_progress('Sprint', f'No todo.md found at {todo_path}')
        return []

    results: list[SprintResult] = []
    consecutive_failures = 0
    item_count = 0
    seen_line_numbers: set[int] = set()  # Track seen items for dry-run mode

    while True:
        # Check max items
        if max_items > 0 and item_count >= max_items:
            stream_progress('Sprint', f'Reached max items ({max_items}), stopping')
            break

        # Re-parse todo.md each iteration (it may have been updated)
        items = parse_todo(todo_path)
        if not items:
            stream_progress('Sprint', 'No items found in todo.md')
            break

        next_item = find_next_actionable(items, done_path)
        if next_item is None:
            stream_progress('Sprint', 'No actionable items remaining')
            break

        item_count += 1
        print_phase_header(f'Sprint Item #{item_count}')
        stream_progress('Sprint', f'Next: {next_item.text}')
        stream_progress('Sprint', f'Priority: {next_item.priority}, Category: {next_item.category}')

        if dry_run:
            # Prevent infinite loop: in dry-run mode items are never checked off,
            # so find_next_actionable() would return the same item forever.
            if next_item.line_number in seen_line_numbers:
                break
            seen_line_numbers.add(next_item.line_number)

            # Dry run: preview what would run without any API calls
            print(f"\n{Fore.CYAN}Dry run — would execute:{Style.RESET_ALL}", file=sys.stderr, flush=True)
            print(f"  Item: {next_item.text}", file=sys.stderr, flush=True)
            print(f"  Priority: {next_item.priority}", file=sys.stderr, flush=True)
            print(f"  Category: {next_item.category}", file=sys.stderr, flush=True)
            print(f"  Query would be enriched with project.md + decisions.md context", file=sys.stderr, flush=True)
            results.append(SprintResult(todo_item=next_item))
            continue

        # --- Execute the sprint item ---
        result = SprintResult(todo_item=next_item)

        try:
            # Step 1: Enrich query
            enriched_query = enrich_query(next_item, project_path)

            # Step 2: Plan phase
            returncode, output, elapsed = run_phase(
                'plan', [enriched_query],
                project_path, max_turns=max_turns, max_review_cycles=max_review_cycles,
            )

            if returncode != 0:
                result.error = f'Plan phase failed (exit={returncode})'
                raise RuntimeError(result.error)

            orch_result = extract_orch_result(output)
            plan_path = orch_result.get('plan_path', '')
            research_path = orch_result.get('research_path', '')

            if not plan_path:
                # Try to find the most recent plan file
                plans_dir = project_dir / 'memories' / 'shared' / 'plans'
                if plans_dir.exists():
                    plan_files = sorted(plans_dir.glob('*.md'),
                                        key=lambda f: f.stat().st_mtime, reverse=True)
                    if plan_files:
                        plan_path = str(plan_files[0].relative_to(project_dir))

            if not plan_path:
                result.error = 'Could not find plan file after plan phase'
                raise RuntimeError(result.error)

            result.plan_path = plan_path
            stream_progress('Sprint', f'Plan created: {plan_path}')

            # Step 3: Micro-reflect after plan (skip if --skip-reflection)
            if not skip_reflection:
                micro_reflect('plan', plan_path, project_path, research_path=research_path)

            # Step 4: Implement phase
            impl_args = [plan_path]
            if research_path:
                impl_args = ['--research', research_path] + impl_args

            returncode, output, elapsed = run_phase(
                'implement', impl_args,
                project_path, max_turns=max_turns, max_review_cycles=max_review_cycles,
            )

            if returncode != 0:
                result.error = f'Implement phase failed (exit={returncode})'
                raise RuntimeError(result.error)

            impl_result = extract_orch_result(output)
            review_path = impl_result.get('review_path', '')
            result.review_path = review_path

            # Step 5: Micro-reflect after implement (skip if --skip-reflection)
            if not skip_reflection:
                micro_reflect('implement', plan_path, project_path,
                              research_path=research_path, review_path=review_path)

            # Step 6: Cleanup phase
            cleanup_args = [plan_path]
            if research_path:
                cleanup_args = ['--research', research_path] + cleanup_args

            returncode, output, elapsed = run_phase(
                'cleanup', cleanup_args,
                project_path, max_turns=max_turns, max_review_cycles=max_review_cycles,
            )

            cleanup_succeeded = (returncode == 0)
            if not cleanup_succeeded:
                stream_progress('Cleanup', f'Warning: Cleanup phase failed (exit={returncode})')
                # Don't fail the whole sprint item for cleanup issues

            # Step 7: Consolidate (skip if --skip-reflection)
            if not skip_reflection:
                consolidate_memory(project_path)

            # Step 8: Update todo.md / done.md (only if cleanup didn't handle it)
            if not cleanup_succeeded:
                update_todo_done(next_item, plan_path, project_path)

            result.completed = True
            consecutive_failures = 0

        except RuntimeError as e:
            result.error = str(e)
            result.completed = False
            consecutive_failures += 1
            stream_progress('Error', f'Item failed: {e}')

        except Exception as e:
            result.error = f'Unexpected error: {e}'
            result.completed = False
            consecutive_failures += 1
            stream_progress('Error', f'Unexpected: {e}')

        results.append(result)

        # Check for 3 consecutive failures
        if consecutive_failures >= 3:
            stream_progress('Sprint', 'Stopping: 3 consecutive failures')
            break

        # Checkpoint
        if not show_checkpoint(result, item_count):
            stream_progress('Sprint', 'User requested stop')
            break

    return results


# --- Main entry point ---

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Sprint Runner with Reflection Loop',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run sprint (processes items from todo.md)
  %(prog)s --max-items 3                      # Process at most 3 items
  %(prog)s --dry-run                          # Show what would run without executing
  %(prog)s --skip-reflection                  # Skip micro-reflections and consolidation
  %(prog)s --max-turns 30 --max-review-cycles 5  # Custom orchestrator limits
        """
    )
    parser.add_argument('--max-items', type=int, default=0,
                        help='Max items to process before stopping (default: unlimited)')
    parser.add_argument('--max-turns', type=int, default=40,
                        help='Claude turns per orchestrator run (default: 40)')
    parser.add_argument('--max-review-cycles', type=int, default=3,
                        help='Review-fix cycles per run (default: 3)')
    parser.add_argument('--skip-reflection', action='store_true',
                        help='Skip the reflection/consolidation phase')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse todo.md and show what would run, without executing')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    parser.add_argument('--project', default='.', help='Project directory path')

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

        print_phase_header('Sprint Runner')
        stream_progress('Sprint', f'Project: {os.path.abspath(args.project)}')

        results = run_sprint(
            project_path=args.project,
            max_items=args.max_items,
            max_turns=args.max_turns,
            max_review_cycles=args.max_review_cycles,
            skip_reflection=args.skip_reflection,
            dry_run=args.dry_run,
            output_json=args.json,
        )

        total_elapsed = time.time() - total_start

        # Print summary
        completed = sum(1 for r in results if r.completed)
        failed = sum(1 for r in results if not r.completed and r.error)

        print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}", file=sys.stderr, flush=True)
        print(f"\n{Fore.GREEN}{Style.BRIGHT}  Sprint Summary{Style.RESET_ALL}\n", file=sys.stderr, flush=True)
        print(f"  Items processed: {len(results)}", file=sys.stderr, flush=True)
        print(f"  Completed:       {completed}", file=sys.stderr, flush=True)
        print(f"  Failed:          {failed}", file=sys.stderr, flush=True)
        print(f"  Total time:      {format_duration(total_elapsed)}", file=sys.stderr, flush=True)
        print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n", file=sys.stderr, flush=True)

        if args.json:
            output = {
                'items_processed': len(results),
                'completed': completed,
                'failed': failed,
                'total_seconds': round(total_elapsed, 1),
                'results': [asdict(r) for r in results],
            }
            print(json.dumps(output, indent=2))

        return 0 if failed == 0 else 1

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
