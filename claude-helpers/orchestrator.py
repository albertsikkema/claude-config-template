#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydantic-ai>=0.0.1",
#     "python-dotenv>=1.0.0",
#     "colorama>=0.4.6",
# ]
# ///
"""
Orchestrate Claude Code workflows: index → research → plan → implement → review.

Usage:
    uv run claude-helpers/orchestrator.py "Add user authentication"
    uv run claude-helpers/orchestrator.py --json "Refactor database layer"

Tip: Add an alias to your ~/.zshrc or ~/.bashrc for easy access:
    alias orchestrate='uv run claude-helpers/orchestrator.py'

Then use: orchestrate "Add user authentication"
"""

import argparse
import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass

from colorama import Fore, Style, init
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Initialize colorama and load .env.claude file
init()
load_dotenv('.env.claude')


def get_model() -> str | OpenAIChatModel:
    """Get the appropriate model based on available environment variables.

    Returns OpenAI model string if OPENAI_API_KEY is set,
    otherwise returns Azure OpenAI configured model.
    """
    if os.getenv('OPENAI_API_KEY'):
        return 'openai:gpt-4o'

    # Use Azure OpenAI
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_key = os.getenv('AZURE_OPENAI_API_KEY')
    azure_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
    azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')

    if not azure_endpoint or not azure_key:
        raise ValueError("Neither OPENAI_API_KEY nor Azure OpenAI credentials found in .env")

    # Import here to avoid dependency if not using Azure
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_version=azure_version,
        api_key=azure_key,
    )

    return OpenAIChatModel(
        azure_deployment,
        provider=OpenAIProvider(openai_client=client),
    )

# Color mapping for stages
STAGE_COLORS = {
    'Indexing': Fore.CYAN,
    'Research': Fore.YELLOW,
    'Planning': Fore.MAGENTA,
    'Implement': Fore.GREEN,
    'Review': Fore.BLUE,
}


@dataclass
class OrchestratorDeps:
    """Dependencies for the orchestrator agent."""
    project_path: str
    user_query: str
    implement: bool = True


class WorkflowResult(BaseModel):
    """Structured output for the workflow."""
    index_summary: str = Field(description='Summary of indexing results')
    research_path: str = Field(description='Path to research document')
    plan_path: str = Field(description='Path to implementation plan')
    implemented: bool = Field(default=False, description='Whether plan was implemented')
    implementation_summary: str = Field(default='', description='Summary of what was implemented')
    review_path: str = Field(default='', description='Path to code review document')
    review_summary: str = Field(default='', description='Key findings from code review')
    status: str = Field(description='Overall workflow status')
    error: str | None = Field(default=None, description='Error message if failed')
    tokens_used: int = Field(default=0, description='Total tokens used by orchestrator')


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


def run_claude_command(command: list[str], cwd: str, timeout: int = 600) -> tuple[int, str, float]:
    """Run a Claude Code command with real-time output streaming.

    Returns:
        Tuple of (return_code, captured_output, elapsed_seconds)
    """
    # Extract the slash command from the -p argument
    cmd_display = command[-1] if command else ""
    if cmd_display.startswith('/'):
        cmd_display = cmd_display.split('\n')[0]  # First line only for multi-line prompts
    print(f"{Fore.BLUE}Starting new Claude Code session...{Style.RESET_ALL} ({cmd_display})", file=sys.stderr, flush=True)
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
                print(line, end='', file=sys.stderr, flush=True)
                output_lines.append(line)

        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        elapsed = time.time() - start_time
        raise RuntimeError(f"Command timed out after {format_duration(elapsed)}")

    elapsed = time.time() - start_time
    return process.returncode, ''.join(output_lines), elapsed


def extract_file_path(output: str) -> str | None:
    """Extract file path from Claude Code output."""
    # Look for markdown file paths in the output
    matches = re.findall(r'thoughts/shared/(?:research|plans)/[\w\-]+\.md', output)
    if matches:
        return matches[-1]  # Return last match (most likely the created file)
    return None


# Lazy initialization of orchestrator agent
_orchestrator = None


def get_orchestrator() -> Agent:
    """Get or create the orchestrator agent."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Agent(
            get_model(),
            deps_type=OrchestratorDeps,
            output_type=WorkflowResult,
            system_prompt='''You orchestrate Claude Code automation workflows.

Execute these steps in EXACT order:
1. Call index_codebase to index the codebase
2. Call research_codebase with the user's query topic
3. Extract the research file path from the research output
4. Call create_plan with the research file path AND context to answer questions
5. If deps.implement is True, call implement_plan with the plan file path
6. If deps.implement is True, call code_review to review the changes

IMPORTANT:
- Execute steps sequentially, wait for each to complete
- Parse file paths from tool outputs carefully
- Stop immediately if any step fails
- Report the final file paths in your result
- Set implemented=True in result only if implement_plan was called and succeeded
- Extract a brief implementation_summary (2-3 sentences) describing what was done
- Extract key findings (critical issues, improvements) from the code review output for review_summary

HANDLING INTERACTIVE COMMANDS:
Some commands like /create_plan may ask clarifying questions. When calling create_plan,
provide enough context in the prompt so Claude Code can answer its own questions:
- Include the original user query
- Include key findings from research
- Specify any constraints or preferences mentioned by the user
This allows the command to proceed without blocking on user input.
'''
        )
        # Register tools
        _orchestrator.tool(index_codebase)
        _orchestrator.tool(research_codebase)
        _orchestrator.tool(create_plan)
        _orchestrator.tool(implement_plan)
        _orchestrator.tool(code_review)

    return _orchestrator


# Tool functions
async def index_codebase(ctx: RunContext[OrchestratorDeps]) -> str:
    """Index the codebase using Claude Code /index_codebase command.

    This auto-detects languages and creates index files in thoughts/codebase/.
    """
    stream_progress("Indexing", "Starting codebase indexing...")

    returncode, output, elapsed = run_claude_command(
        ['claude', '--dangerously-skip-permissions', '-p', '/index_codebase'],
        cwd=ctx.deps.project_path,
        timeout=600
    )

    if returncode != 0:
        stream_progress("Indexing", f"FAILED ({format_duration(elapsed)})")
        raise RuntimeError(f"Indexing failed with code {returncode}")

    stream_progress("Indexing", f"Complete ({format_duration(elapsed)})")
    return output or "Indexing completed successfully"


async def research_codebase(ctx: RunContext[OrchestratorDeps], topic: str) -> str:
    """Research the codebase using Claude Code /research_codebase command.

    Args:
        topic: The topic to research (from user query)

    Returns:
        Output containing the path to the research document.
        Parse this to find: thoughts/shared/research/YYYY-MM-DD-*.md
    """
    stream_progress("Research", f"Researching: {topic}...")

    returncode, output, elapsed = run_claude_command(
        ['claude', '--dangerously-skip-permissions', '-p', f'/research_codebase {topic}'],
        cwd=ctx.deps.project_path,
        timeout=600
    )

    if returncode != 0:
        stream_progress("Research", f"FAILED ({format_duration(elapsed)})")
        raise RuntimeError(f"Research failed with code {returncode}")

    file_path = extract_file_path(output)

    if file_path:
        stream_progress("Research", f"Complete: {file_path} ({format_duration(elapsed)})")
    else:
        stream_progress("Research", f"Complete ({format_duration(elapsed)})")

    return output


async def create_plan(ctx: RunContext[OrchestratorDeps], research_file_path: str, context_for_questions: str) -> str:
    """Create implementation plan using Claude Code /create_plan command.

    Args:
        research_file_path: Path to the research document
                           (e.g., thoughts/shared/research/2025-11-21-topic.md)
        context_for_questions: Additional context to help answer any clarifying questions
                              the /create_plan command may ask. Include:
                              - Original user query/intent
                              - Key findings from research
                              - Any constraints or preferences

    Returns:
        Output containing the path to the plan document.
        Parse this to find: thoughts/shared/plans/YYYY-MM-DD-*.md
    """
    stream_progress("Planning", "Creating implementation plan...")

    # Build prompt with context so Claude Code can answer its own questions
    prompt = f"""/create_plan {research_file_path}

Context for any questions that may arise:
{context_for_questions}

User's original request: {ctx.deps.user_query}

Please proceed with reasonable defaults based on the research and context provided."""

    returncode, output, elapsed = run_claude_command(
        ['claude', '--dangerously-skip-permissions', '-p', prompt],
        cwd=ctx.deps.project_path,
        timeout=600
    )

    if returncode != 0:
        stream_progress("Planning", f"FAILED ({format_duration(elapsed)})")
        raise RuntimeError(f"Planning failed with code {returncode}")

    file_path = extract_file_path(output)

    if file_path:
        stream_progress("Planning", f"Complete: {file_path} ({format_duration(elapsed)})")
    else:
        stream_progress("Planning", f"Complete ({format_duration(elapsed)})")

    return output


async def implement_plan(ctx: RunContext[OrchestratorDeps], plan_file_path: str) -> str:
    """Implement the plan using Claude Code /implement_plan command.

    Args:
        plan_file_path: Path to the plan document
                       (e.g., thoughts/shared/plans/2025-11-21-topic.md)

    Returns:
        Output from the implementation process.
    """
    if not ctx.deps.implement:
        return "Implementation skipped (implement=False)"

    stream_progress("Implement", f"Implementing plan: {plan_file_path}...")

    returncode, output, elapsed = run_claude_command(
        ['claude', '--dangerously-skip-permissions', '-p', f'/implement_plan {plan_file_path}'],
        cwd=ctx.deps.project_path,
        timeout=1800  # 30 min timeout for implementation
    )

    if returncode != 0:
        stream_progress("Implement", f"FAILED ({format_duration(elapsed)})")
        raise RuntimeError(f"Implementation failed with code {returncode}")

    stream_progress("Implement", f"Complete ({format_duration(elapsed)})")
    return output


async def code_review(ctx: RunContext[OrchestratorDeps], plan_path: str, research_path: str) -> str:
    """Review code changes using Claude Code /code_reviewer command.

    Reviews both staged and unstaged changes from the implementation,
    using the plan and research as context for the review.

    Args:
        plan_path: Path to the implementation plan
        research_path: Path to the research document

    Returns:
        Output containing the review results and path to the review document.
        Parse this to find: thoughts/shared/reviews/code-review-*.md
        Also extract key findings (critical issues, improvements) for the summary.
    """
    stream_progress("Review", "Reviewing code changes...")

    # Call code_reviewer with plan and research context
    prompt = f"""/code_reviewer

Please review the current git changes (both staged and unstaged).

Context for this review:
- Implementation plan: {plan_path}
- Research document: {research_path}
- Original request: {ctx.deps.user_query}

Focus on:
- Whether the implementation matches the plan's requirements
- Changes made align with the research findings
- Use `git diff` and `git diff --staged` to see all changes
- Provide a thorough review following the standard format"""

    returncode, output, elapsed = run_claude_command(
        ['claude', '--dangerously-skip-permissions', '-p', prompt],
        cwd=ctx.deps.project_path,
        timeout=600
    )

    if returncode != 0:
        stream_progress("Review", f"FAILED ({format_duration(elapsed)})")
        raise RuntimeError(f"Code review failed with code {returncode}")

    # Extract review file path
    review_matches = re.findall(r'thoughts/shared/reviews/[\w\-]+\.md', output)
    review_path = review_matches[-1] if review_matches else ""

    if review_path:
        stream_progress("Review", f"Complete: {review_path} ({format_duration(elapsed)})")
    else:
        stream_progress("Review", f"Complete ({format_duration(elapsed)})")

    return output


async def run_orchestrator(query: str, project_path: str = '.', implement: bool = True) -> WorkflowResult:
    """Run the orchestrator workflow."""
    deps = OrchestratorDeps(
        project_path=project_path,
        user_query=query,
        implement=implement
    )

    orchestrator = get_orchestrator()
    prompt = f'Execute the full workflow for this user request: {query}'
    result = await orchestrator.run(prompt, deps=deps)

    # Get token usage from PydanticAI result
    total_tokens = 0
    try:
        usage = result.usage()
        total_tokens = (usage.input_tokens or 0) + (usage.output_tokens or 0)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not get token usage: {e}{Style.RESET_ALL}", file=sys.stderr)

    # Update result with token count
    output = result.output
    output.tokens_used = total_tokens

    return output


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Orchestrate Claude Code workflows: index → research → plan → implement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Add user authentication"
  %(prog)s --no-implement "Refactor database layer"
  %(prog)s --json "Improve error handling"
        """
    )
    parser.add_argument('query', help='User query for research and planning')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--project', default='.', help='Project directory path')
    parser.add_argument('--no-implement', action='store_true', help='Skip implementation step')

    args = parser.parse_args()

    # Check for API keys
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('AZURE_OPENAI_API_KEY'):
        print("Error: No API key found in .env.claude file", file=sys.stderr)
        print("Create .env.claude with OPENAI_API_KEY or AZURE_OPENAI_API_KEY", file=sys.stderr)
        return 1

    # Show which provider is being used
    if os.getenv('OPENAI_API_KEY'):
        print(f"{Fore.CYAN}Using OpenAI{Style.RESET_ALL}", file=sys.stderr)
    else:
        print(f"{Fore.CYAN}Using Azure OpenAI{Style.RESET_ALL}", file=sys.stderr)

    # Handle SIGTERM for graceful shutdown
    def handle_sigterm(signum, frame):
        print("\nTerminated", file=sys.stderr)
        sys.exit(143)

    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        total_start = time.time()
        result = asyncio.run(run_orchestrator(args.query, args.project, not args.no_implement))
        total_elapsed = time.time() - total_start

        if args.json:
            output = result.model_dump()
            output['total_time'] = format_duration(total_elapsed)
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Workflow Complete:{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}Research:{Style.RESET_ALL} {result.research_path}")
            print(f"  {Fore.MAGENTA}Plan:{Style.RESET_ALL} {result.plan_path}")
            if result.implemented:
                print(f"  {Fore.GREEN}Implemented:{Style.RESET_ALL} Yes")
            if result.implementation_summary:
                print(f"  {Fore.GREEN}Summary:{Style.RESET_ALL}")
                for line in result.implementation_summary.split('\n'):
                    if line.strip():
                        print(f"    {line}")
            if result.review_path:
                print(f"  {Fore.BLUE}Review:{Style.RESET_ALL} {result.review_path}")
            if result.review_summary:
                print(f"  {Fore.BLUE}Review Findings:{Style.RESET_ALL}")
                for line in result.review_summary.split('\n'):
                    if line.strip():
                        print(f"    {line}")
            if result.error:
                print(f"  {Fore.RED}Error:{Style.RESET_ALL} {result.error}")
            print(f"  {Fore.BLUE}Total time:{Style.RESET_ALL} {format_duration(total_elapsed)}")
            print(f"  {Fore.YELLOW}Tokens used:{Style.RESET_ALL} {result.tokens_used:,}")

        return 0 if result.status == 'success' else 1

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps({'error': str(e)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
