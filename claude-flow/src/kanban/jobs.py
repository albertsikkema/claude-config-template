"""Background job execution for Claude Code commands."""

import asyncio
import json
import os
import re
import shutil
import threading
import traceback
from pathlib import Path

from sqlalchemy.orm import Session

from kanban.database import SessionLocal, TaskDB
from kanban.models import JobStatus, Stage, WorkflowComplexity

# Store running processes for potential cancellation
running_jobs: dict[str, asyncio.subprocess.Process] = {}

# Project root path (where Claude Code should run)
# jobs.py -> kanban/ -> src/ -> fastapi_app/ -> claude-config-template/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Find claude executable
CLAUDE_PATH = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")

# Maximum characters to store in job_output for UI display.
# This is for display purposes only - actual workflow artifacts (research docs, plans)
# are saved as complete files on disk. Next stages reference file paths, not job_output.
MAX_OUTPUT_LENGTH = 10000


def get_prompt_for_stage(stage: Stage, task: TaskDB) -> str | None:
    """Get the prompt for a stage transition.

    Returns a descriptive prompt that works in non-interactive mode.
    Slash commands only work in interactive mode.
    """
    # Combine title and description for context
    context = task.title
    if task.description:
        context = f"{task.title}\n\nDescription: {task.description}"

    if stage == Stage.RESEARCH:
        return f"""Research the following topic in this codebase:

{context}

Find existing patterns, implementations, best practices, and relevant code.
Create a research document and save it to thoughts/shared/research/ with today's date.
"""
    elif stage == Stage.PLANNING:
        if task.research_path:
            return f"""Based on the research in {task.research_path}, create an implementation plan.

Context: {context}

Create a detailed plan with steps, architecture decisions, and success criteria.
Save the plan to thoughts/shared/plans/ with today's date.
"""
        return None  # Need research first
    elif stage == Stage.IMPLEMENTATION:
        if task.plan_path:
            # Complete workflow - use plan
            return f"""Implement the plan in {task.plan_path}.

Follow each step in the plan and make the necessary code changes.
Run tests and verify everything works.
"""
        elif task.complexity == WorkflowComplexity.SIMPLE:
            # Simple workflow - implement directly from title/description
            return f"""Implement the following change directly:

{context}

This is a simple/quick change. Implement it directly without creating a plan.
Focus on minimal, targeted changes. Run tests if applicable.
Do not create research documents or plans - just implement the change.
"""
        return None  # Complete workflow needs plan first
    elif stage == Stage.REVIEW:
        # Build the review context section based on workflow type
        if task.plan_path:
            # Complete workflow - reference the plan
            review_context = f"""## Context

The implementation followed the plan in {task.plan_path}.

Task: {context}

**Step 0 - Gather Changes**: Before starting the review, run these commands to understand what changed:
1. Run `git diff --name-only` to see which files were modified
2. Run `git diff` to see the actual code changes
3. Read the plan file to understand the requirements
"""
        elif task.complexity == WorkflowComplexity.SIMPLE:
            # Simple workflow - use git diff as the source of truth
            review_context = f"""## Context

Task: {context}

**Step 0 - Gather Changes**: Before starting the review, run these commands to understand what changed:
1. Run `git diff --name-only` to see which files were modified
2. Run `git diff` to see the actual code changes
3. These changes should address the task described above
"""
        else:
            # Fallback
            review_context = f"""## Context

Task: {context}

**Step 0 - Gather Changes**: Run `git diff` to see the code changes to review.
"""

        # Full code_reviewer prompt
        return f"""{review_context}

# Code Review

You are a senior software engineer conducting thorough code reviews. Your role is to analyze code for quality, security, performance, and maintainability.

## Critical First Step

**ALWAYS read relevant docs in `/thoughts/technical_docs`** before starting the review.

## Review Priorities

When reviewing code, evaluate these areas:

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
- Are functions/methods focused on a single responsibility?

### 5. Best Practices
- Does the code follow established patterns and conventions for the language/framework?

### 6. Error Handling
- Are errors properly caught, logged, and handled?
- Are there appropriate fallbacks?

### 7. Testing
- Is the code testable?
- Are there suggestions for test cases that should be written?

## Review Format

Provide:

- **Summary**: Brief overview of what the code does and your overall assessment
- **Critical Issues**: Must-fix problems that could cause bugs, security issues, or system failures
- **Improvements**: Suggestions that would enhance code quality, performance, or maintainability
- **Minor Notes**: Style issues, naming suggestions, or other low-priority observations
- **Positive Feedback**: Highlight what was done well

## Review Approach

- Be constructive and specific in your feedback
- Provide code examples when suggesting improvements
- Explain **why** something should be changed, not just what to change
- Consider the context and requirements of the project
- Balance perfectionism with pragmatism
"""
    elif stage == Stage.CLEANUP:
        if task.plan_path:
            return f"""Clean up after implementing {task.plan_path}.

Document any best practices learned.
Remove temporary files if any.
Update documentation as needed.
"""
        return None

    return None


def extract_file_path(output: str, stage: Stage) -> str | None:
    """Extract the generated file path from Claude Code output."""
    if stage == Stage.RESEARCH:
        matches = re.findall(r"thoughts/shared/research/[\w\-]+\.md", output)
    elif stage == Stage.PLANNING:
        matches = re.findall(r"thoughts/shared/plans/[\w\-]+\.md", output)
    else:
        return None

    return matches[-1] if matches else None


def update_task_status(
    task_id: str,
    job_status: JobStatus,
    job_output: str | None = None,
    job_error: str | None = None,
    research_path: str | None = None,
    plan_path: str | None = None,
    session_id: str | None = None,
    set_started: bool = False,
    set_completed: bool = False,
) -> None:
    """Update task job status in database."""
    from datetime import datetime

    db = SessionLocal()
    try:
        task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
        if task:
            task.job_status = job_status
            if job_output is not None:
                task.job_output = job_output
            if job_error is not None:
                task.job_error = job_error
            if research_path is not None:
                task.research_path = research_path
            if plan_path is not None:
                task.plan_path = plan_path
            if session_id is not None:
                task.session_id = session_id
            if set_started:
                task.job_started_at = datetime.utcnow()
            if set_completed:
                task.job_completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


async def run_claude_command(
    task_id: str, prompt: str, stage: Stage, model: str = "sonnet"
) -> None:
    """Run a Claude Code command asynchronously and update task status."""
    update_task_status(
        task_id,
        JobStatus.RUNNING,
        job_output=f"Starting Claude Code ({model})...",
        set_started=True,
    )

    try:
        # Ensure HOME env var is set for claude to find its config
        env = os.environ.copy()
        env["HOME"] = str(Path.home())

        # Build args for non-interactive execution
        # Use stream-json for real-time output (newline-delimited JSON)
        # --verbose is required when using stream-json with -p
        #
        # SECURITY NOTE: --dangerously-skip-permissions is required for automated execution.
        # Without it, Claude Code would prompt for permission on each tool use, blocking
        # the background process. This flag allows Claude to execute tools (file reads,
        # writes, bash commands) without user confirmation.
        #
        # RISKS:
        # - Claude can modify any files in the project directory
        # - Claude can execute arbitrary shell commands
        # - No human-in-the-loop for dangerous operations
        #
        # MITIGATIONS:
        # - Only runs in the context of the project root directory
        # - Task prompts are controlled by the application
        # - Job output is logged and visible to users
        # - Users can cancel running jobs at any time
        args = [
            CLAUDE_PATH,
            "--dangerously-skip-permissions",
            "--verbose",
            "--model",
            model,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
        ]

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,  # Separate stderr
            cwd=str(PROJECT_ROOT),
            env=env,
        )

        running_jobs[task_id] = process

        # Collect text content from stream-json events
        text_parts: list[str] = []
        raw_lines: list[str] = []
        captured_session_id: str | None = None

        # Read stdout line by line (stream-json outputs newline-delimited JSON)
        async def read_stream():
            buffer = ""
            while True:
                chunk = await process.stdout.read(1024)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        yield line.strip()

        async for line in read_stream():
            raw_lines.append(line)

            try:
                data = json.loads(line)
                msg_type = data.get("type", "")

                # Extract text content from different message types
                if msg_type == "assistant":
                    # Assistant message with content blocks
                    message = data.get("message", {})
                    for block in message.get("content", []):
                        block_type = block.get("type")
                        if block_type == "text":
                            text = block.get("text", "")
                            if text.strip():
                                text_parts.append(f"\n{text}\n")
                        elif block_type == "tool_use":
                            # Show tool usage with nice formatting
                            tool_name = block.get("name", "unknown")
                            tool_input = block.get("input", {})

                            # Format based on tool type
                            if tool_name == "Bash":
                                cmd = tool_input.get("command", "")[:80]
                                desc = tool_input.get("description", "")
                                text_parts.append(f"\n▶ {desc or 'Running command'}\n  $ {cmd}\n")
                            elif tool_name == "Read":
                                path = tool_input.get("file_path", "")
                                # Show just filename
                                filename = path.split("/")[-1] if "/" in path else path
                                text_parts.append(f"\n📄 Reading: {filename}\n")
                            elif tool_name == "Glob":
                                pattern = tool_input.get("pattern", "")
                                text_parts.append(f"\n🔍 Searching: {pattern}\n")
                            elif tool_name == "Grep":
                                pattern = tool_input.get("pattern", "")
                                text_parts.append(f"\n🔍 Grep: {pattern}\n")
                            elif tool_name == "Write":
                                path = tool_input.get("file_path", "")
                                filename = path.split("/")[-1] if "/" in path else path
                                text_parts.append(f"\n✏️  Writing: {filename}\n")
                            elif tool_name == "Edit":
                                path = tool_input.get("file_path", "")
                                filename = path.split("/")[-1] if "/" in path else path
                                text_parts.append(f"\n✏️  Editing: {filename}\n")
                            elif tool_name == "Task":
                                desc = tool_input.get("description", "")[:60]
                                text_parts.append(f"\n🤖 Agent: {desc}\n")
                            else:
                                desc = tool_input.get("description", "")[:60]
                                text_parts.append(f"\n⚡ {tool_name}: {desc}\n")

                elif msg_type == "content_block_delta":
                    # Incremental streaming content
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text_parts.append(delta.get("text", ""))
                elif msg_type == "content_block_start":
                    # Start of a content block - may contain initial text
                    content_block = data.get("content_block", {})
                    if content_block.get("type") == "text":
                        text = content_block.get("text", "")
                        if text:
                            text_parts.append(text)
                elif msg_type == "user":
                    # User message (includes tool results) - show compact result
                    message = data.get("message", {})
                    for block in message.get("content", []):
                        if block.get("type") == "tool_result":
                            content = str(block.get("content", ""))
                            # Show abbreviated result (first line or truncated)
                            first_line = content.split("\n")[0][:80]
                            if len(content) > 80:
                                first_line += "..."
                            text_parts.append(f"  ✓ {first_line}\n")
                elif msg_type == "result":
                    # Final result
                    result = data.get("result", "")
                    if result:
                        text_parts.append(f"\n{'─' * 40}\n✅ Complete\n\n{result}\n")
                elif msg_type == "system":
                    subtype = data.get("subtype", "")
                    if subtype == "init":
                        captured_session_id = data.get("session_id")
                        display_id = captured_session_id[:8] if captured_session_id else "unknown"
                        text_parts.append(f"🚀 Session {display_id}...\n{'─' * 40}\n")
                        # Store session_id immediately for resumption
                        if captured_session_id:
                            update_task_status(
                                task_id, JobStatus.RUNNING, session_id=captured_session_id
                            )

                # Update database with current progress
                current_text = "".join(text_parts)
                if current_text:
                    update_task_status(task_id, JobStatus.RUNNING, job_output=current_text[-MAX_OUTPUT_LENGTH:])
            except json.JSONDecodeError:
                # Not JSON, append as raw text
                text_parts.append(line + "\n")

        # Wait for process to complete
        await process.wait()

        # Read any stderr
        stderr_output = await process.stderr.read()
        if stderr_output:
            stderr_text = stderr_output.decode("utf-8", errors="replace")
            text_parts.append(f"\n--- Stderr ---\n{stderr_text}")

        full_output = "".join(text_parts)

        if process.returncode == 0:
            # Extract file path from output
            file_path = extract_file_path(full_output, stage)

            # Update with success
            if stage == Stage.RESEARCH:
                update_task_status(
                    task_id,
                    JobStatus.COMPLETED,
                    job_output=full_output[-MAX_OUTPUT_LENGTH:],
                    research_path=file_path,
                    set_completed=True,
                )
            elif stage == Stage.PLANNING:
                update_task_status(
                    task_id,
                    JobStatus.COMPLETED,
                    job_output=full_output[-MAX_OUTPUT_LENGTH:],
                    plan_path=file_path,
                    set_completed=True,
                )
            else:
                update_task_status(
                    task_id,
                    JobStatus.COMPLETED,
                    job_output=full_output[-MAX_OUTPUT_LENGTH:],
                    set_completed=True,
                )
        else:
            update_task_status(
                task_id,
                JobStatus.FAILED,
                job_output=full_output[-MAX_OUTPUT_LENGTH:],
                job_error=f"Command failed with exit code {process.returncode}",
                set_completed=True,
            )

    except Exception as e:
        update_task_status(
            task_id,
            JobStatus.FAILED,
            job_error=str(e),
            set_completed=True,
        )
    finally:
        # Clean up
        if task_id in running_jobs:
            del running_jobs[task_id]


def cancel_running_job(task_id: str) -> bool:
    """Cancel a running job by terminating its process.

    Returns True if a job was cancelled, False if no running job found.
    """
    if task_id not in running_jobs:
        return False

    process = running_jobs[task_id]
    try:
        process.terminate()
    except ProcessLookupError:
        # Process already finished
        pass

    # Update task status
    update_task_status(
        task_id,
        JobStatus.CANCELLED,
        job_error="Job cancelled by user",
        set_completed=True,
    )

    # Clean up
    if task_id in running_jobs:
        del running_jobs[task_id]

    return True


def trigger_stage_command(task_id: str, old_stage: Stage, new_stage: Stage, db: Session) -> bool:
    """Trigger the appropriate command when task moves to a new stage.

    Returns True if a command was triggered, False otherwise.
    Only triggers on forward movement, not backward.
    """

    # Define stage order for forward movement detection
    stage_order = [
        Stage.BACKLOG,
        Stage.RESEARCH,
        Stage.PLANNING,
        Stage.IMPLEMENTATION,
        Stage.REVIEW,
        Stage.CLEANUP,
        Stage.MERGE,
        Stage.DONE,
    ]

    old_index = stage_order.index(old_stage) if old_stage in stage_order else -1
    new_index = stage_order.index(new_stage) if new_stage in stage_order else -1

    # Only trigger on forward movement
    if new_index <= old_index:
        return False

    # Get task from database
    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not task:
        return False

    # Get prompt for the new stage
    prompt = get_prompt_for_stage(new_stage, task)
    if not prompt:
        return False

    # Set initial status
    task.job_status = JobStatus.PENDING
    task.job_output = None
    task.job_error = None
    db.commit()

    # Get model from task (default to sonnet)
    model = task.model.value if task.model else "sonnet"

    # Review stage requires at least sonnet for quality analysis
    if new_stage == Stage.REVIEW and model == "haiku":
        model = "sonnet"

    # Start background task in a separate thread with its own event loop
    def run_in_thread() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_claude_command(task_id, prompt, new_stage, model))
            finally:
                loop.close()
        except Exception as e:
            # Catch any thread-level exceptions and update task status
            error_msg = f"Thread error: {str(e)}\n{traceback.format_exc()}"
            update_task_status(
                task_id,
                JobStatus.FAILED,
                job_error=error_msg,
                set_completed=True,
            )

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    return True
