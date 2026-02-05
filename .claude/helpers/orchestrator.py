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
    'Review': Fore.BLUE,
    'Cleanup': Fore.YELLOW,
    'Commit': Fore.GREEN,
}


# --- Result dataclasses ---

@dataclass
class PlanPhaseResult:
    """Result from the plan phase."""
    research_path: str
    plan_path: str
    summary: str


@dataclass
class ImplementPhaseResult:
    """Result from the implement phase."""
    plan_path: str
    review_path: str
    changes_summary: str
    issues: list[str]


@dataclass
class CleanupPhaseResult:
    """Result from the cleanup phase."""
    committed: bool
    commit_hash: str | None


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



# --- Query refinement ---

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


def run_phase_implement(plan_path: str, project_path: str,
                        non_interactive: bool = False) -> ImplementPhaseResult:
    """Phase 2: Implement → Review"""

    # Validate plan exists
    full_plan_path = Path(project_path) / plan_path
    if not full_plan_path.exists():
        raise RuntimeError(f"Plan file not found: {plan_path}")

    # Step 1: Implement plan (includes validation)
    returncode, output, elapsed = run_claude_command(
        ['claude-safe', '--no-firewall', '--', '-p', f'/implement_plan {plan_path}'],
        cwd=project_path,
        timeout=1800,  # 30 min for implementation
        phase='Implement'
    )
    if returncode != 0:
        raise RuntimeError(f"Implementation failed with code {returncode}")
    stream_progress("Implement", f"Complete ({format_duration(elapsed)})")

    # Step 2: Code review (interactive so user can ask questions and suggest improvements)
    code_review_cmd = f'/code_reviewer {plan_path}'
    if non_interactive:
        # Non-interactive: use -p flag and capture output
        returncode, review_output, elapsed = run_claude_command(
            ['claude-safe', '--no-firewall', '--', '-p', code_review_cmd],
            cwd=project_path,
            timeout=600,
            phase='Review'
        )
        if returncode != 0:
            raise RuntimeError(f"Code review failed with code {returncode}")

        review_path = extract_file_path(review_output, 'reviews')
        stream_progress("Review", f"Complete: {review_path or 'no file created'} ({format_duration(elapsed)})")

        # Extract issues from review output (simple heuristic)
        issues = []
        skip_patterns = ['no critical', 'no issues', 'no problems', 'no bugs', 'no errors',
                         'without issue', 'without error', 'none found', '0 issues', '0 errors']
        for line in review_output.split('\n'):
            line_lower = line.lower()
            # Skip lines that indicate absence of issues
            if any(skip in line_lower for skip in skip_patterns):
                continue
            if any(marker in line_lower for marker in ['critical', 'issue', 'problem', 'bug', 'error']):
                cleaned = line.strip()
                if cleaned and len(cleaned) > 10:  # Skip short/empty lines
                    issues.append(cleaned)
    else:
        # Interactive: let user interact with Claude for review feedback
        returncode, elapsed = run_claude_interactive_command(
            code_review_cmd,
            cwd=project_path,
            phase='Review'
        )
        if returncode != 0:
            raise RuntimeError(f"Code review failed with code {returncode}")

        # Find the most recent review file
        reviews_dir = Path(project_path) / 'memories' / 'shared' / 'reviews'
        if reviews_dir.exists():
            review_files = sorted(reviews_dir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)
            review_path = str(review_files[0].relative_to(project_path)) if review_files else None
        else:
            review_path = None

        stream_progress("Review", f"Complete: {review_path or 'no file created'} ({format_duration(elapsed)})")
        issues = []  # Can't extract issues from interactive session

    summary = f"""Implement Phase Complete

Plan: {plan_path}
Review: {review_path or 'N/A'}
Issues found: {len(issues)}

Next step: Review the changes manually, then run --phase cleanup"""

    return ImplementPhaseResult(
        plan_path=plan_path,
        review_path=review_path or '',
        changes_summary=summary,
        issues=issues[:10]  # Limit to top 10
    )


def run_phase_cleanup(plan_path: str, research_path: str, review_path: str, project_path: str) -> CleanupPhaseResult:
    """Phase 3: Cleanup → Commit (interactive) → Complete"""

    # Validate plan exists
    full_plan_path = Path(project_path) / plan_path
    if not full_plan_path.exists():
        raise RuntimeError(f"Plan file not found: {plan_path}")

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

    # Step 2: Commit - INTERACTIVE
    stream_progress("Commit", "Starting interactive commit (approval required)...")
    returncode = run_claude_interactive(
        '/commit',
        cwd=project_path
    )

    committed = returncode == 0

    # Step 3: Mark plan complete (update frontmatter)
    if committed:
        mark_plan_complete(full_plan_path)

    return CleanupPhaseResult(
        committed=committed,
        commit_hash=get_current_commit_hash(project_path) if committed else None
    )


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


def get_current_commit_hash(project_path: str) -> str | None:
    """Get the current HEAD commit hash."""
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


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
            print(f"  {Fore.YELLOW}Issues found:{Style.RESET_ALL} {len(result.issues)}")
            if result.issues:
                for issue in result.issues[:5]:
                    print(f"    - {issue[:80]}...")
            print(f"\n  {Fore.BLUE}Next:{Style.RESET_ALL} Review changes, then run --phase cleanup {result.plan_path}")

        elif isinstance(result, CleanupPhaseResult):
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Cleanup Phase Complete:{Style.RESET_ALL}")
            if result.committed:
                print(f"  {Fore.GREEN}Committed:{Style.RESET_ALL} Yes ({result.commit_hash[:8] if result.commit_hash else 'N/A'})")
            else:
                print(f"  {Fore.YELLOW}Committed:{Style.RESET_ALL} No (user declined or error)")
            print(f"\n  {Fore.BLUE}Next:{Style.RESET_ALL} Run /pr to create a pull request")


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
  %(prog)s --phase implement path/to/plan.md      # Implement phase
  %(prog)s --phase cleanup path/to/plan.md        # Cleanup phase
        """
    )
    parser.add_argument('query_or_path', help='Query (for plan) or plan path (for implement/cleanup)')
    parser.add_argument('--phase', choices=['plan', 'implement', 'cleanup', 'all'],
                        default='all', help='Which phase to run (default: all)')
    parser.add_argument('--project', default='.', help='Project directory path')
    parser.add_argument('--research', help='Research file path (for cleanup phase)')
    parser.add_argument('--review', help='Review file path (for cleanup phase)')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--no-refine', action='store_true', dest='no_refine',
                        help='Skip interactive query refinement (use original query as-is)')

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
            result = run_phase_implement(args.query_or_path, args.project)
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

            implement_result = run_phase_implement(plan_result.plan_path, args.project,
                                                   non_interactive=True)
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
