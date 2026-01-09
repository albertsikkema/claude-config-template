"""Background job execution for Claude Code commands."""

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import threading
import traceback
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

import kanban.models as models
from kanban.database import SessionLocal, TaskDB
from kanban.models import JobStatus, Stage, WorkflowComplexity
from kanban.utils import PROJECT_ROOT, read_slash_command

logger = logging.getLogger(__name__)

# Store running processes for potential cancellation
running_jobs: dict[str, asyncio.subprocess.Process] = {}

# Find claude executable
CLAUDE_PATH = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")

# Maximum characters to store in job_output for UI display.
# This is for display purposes only - actual workflow artifacts (research docs, plans)
# are saved as complete files on disk. Next stages reference file paths, not job_output.
# Increased from 10K to 100K to capture more verbose output from Claude operations
MAX_OUTPUT_LENGTH = 100000


def _build_task_context(task: TaskDB) -> str:
    """Build context string from task title and description."""
    context = task.title
    if task.description:
        context = f"{task.title}\n\nDescription: {task.description}"
    return context


def get_prompt_for_stage(stage: Stage, task: TaskDB) -> str | None:
    """Get the prompt for a stage transition.

    Reads the full slash command content and appends task-specific context.
    This allows subagents to be spawned in non-interactive mode.

    Returns None if command file not found or prerequisites not met.
    """
    context = _build_task_context(task)

    if stage == Stage.RESEARCH:
        cmd_content = read_slash_command("research_codebase")
        if not cmd_content:
            return None
        return f"""{cmd_content}

## Research Topic

{context}

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode. After completing the research document:
1. Present a brief summary of findings
2. List key file references
3. **DO NOT ask follow-up questions or wait for user input**
4. **DO NOT ask "Would you like me to implement this?"**
5. Simply conclude with the document location and exit

The research is complete once the document is saved.
"""

    elif stage == Stage.PLANNING:
        if not task.research_path:
            return None  # Need research first

        cmd_content = read_slash_command("create_plan")
        if not cmd_content:
            return None
        return f"""{cmd_content}

## Planning Context

Task: {context}

Research document: {task.research_path}

Use the research findings to inform the implementation plan.

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode. After creating the plan document:
1. Present a brief summary of the plan
2. State the plan file location
3. **DO NOT ask for user review or feedback**
4. **DO NOT wait for user input**
5. Simply conclude with the plan location and exit

The planning is complete once the document is saved.
"""

    elif stage == Stage.IMPLEMENTATION:
        if task.plan_path:
            # Complete workflow - use plan
            cmd_content = read_slash_command("implement_plan")
            if not cmd_content:
                return None
            return f"""{cmd_content}

## Implementation Context

Plan file: {task.plan_path}

Task: {context}

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode. After completing implementation:
1. Implement all phases from the plan
2. Run tests and verify success criteria
3. Present a summary of what was implemented
4. **DO NOT ask if the user wants to proceed with next steps**
5. **DO NOT wait for user input**
6. Simply conclude with the implementation summary and exit

Implementation is complete once all plan phases are executed.
"""
        elif task.complexity == WorkflowComplexity.SIMPLE:
            # Simple workflow - implement directly from title/description
            return f"""Implement the following change directly:

{context}

This is a simple/quick change. Implement it directly without creating a plan.
Focus on minimal, targeted changes. Run tests if applicable.
Do not create research documents or plans - just implement the change.

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode. After completing the change:
1. Make the required changes
2. Run tests if applicable
3. Present a brief summary
4. **DO NOT ask follow-up questions**
5. **DO NOT wait for user input**
6. Simply conclude and exit
"""
        return None  # Complete workflow needs plan first

    elif stage == Stage.REVIEW:
        cmd_content = read_slash_command("code_reviewer")
        if not cmd_content:
            return None

        # Build review context based on workflow type
        if task.plan_path:
            review_context = f"""## Review Context

The implementation followed the plan in {task.plan_path}.

Task: {context}
"""
        elif task.complexity == WorkflowComplexity.SIMPLE:
            review_context = f"""## Review Context

Task: {context}

This was a simple/quick change implemented directly without a plan.
"""
        else:
            review_context = f"""## Review Context

Task: {context}
"""

        return f"""{cmd_content}

{review_context}

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode. After completing the review:
1. Present the review findings
2. State the review document location (if created)
3. **DO NOT ask if the user wants you to address issues**
4. **DO NOT wait for user input**
5. Simply conclude with the summary and exit

The review is complete once findings are presented.
"""

    elif stage == Stage.CLEANUP:
        if task.plan_path:
            cmd_content = read_slash_command("cleanup")
            if not cmd_content:
                return None
            return f"""{cmd_content}

## Cleanup Context

Plan file: {task.plan_path}
Research file: {task.research_path or "N/A"}
Review file: {task.review_path or "N/A"}

Task: {context}

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode. After completing cleanup:
1. Document any best practices discovered
2. Delete ephemeral artifacts as specified
3. Present a summary of what was cleaned up
4. **DO NOT ask for user confirmation**
5. **DO NOT wait for user input**
6. Simply conclude with the cleanup summary and exit

Cleanup is complete once artifacts are processed.
"""
        elif task.research_path:
            # Research-only task - no implementation happened
            return f"""This was a research-only task. The research document at {task.research_path} is the permanent output.

Review the research document and determine if any best practices should be documented.
If this research leads to implementation, create a plan using /create_plan.
Otherwise, the research document remains as reference material.

## IMPORTANT: Non-Interactive Mode

You are running in automated non-interactive mode:
1. Review the research and document any best practices
2. Present a brief summary
3. **DO NOT ask for user input**
4. Simply conclude and exit
"""
        return None

    return None


def extract_file_path(output: str, stage: Stage) -> str | None:
    """Extract the generated file path from Claude Code output."""
    if stage == Stage.RESEARCH:
        matches = re.findall(r"thoughts/shared/research/[\w\-]+\.md", output)
    elif stage == Stage.PLANNING:
        matches = re.findall(r"thoughts/shared/plans/[\w\-]+\.md", output)
    elif stage == Stage.REVIEW:
        matches = re.findall(r"thoughts/shared/reviews/[\w\-]+\.md", output)
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
    review_path: str | None = None,
    session_id: str | None = None,
    set_started: bool = False,
    set_completed: bool = False,
) -> None:
    """Update task job status in database."""
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
            if review_path is not None:
                task.review_path = review_path
            if session_id is not None:
                task.session_id = session_id
            if set_started:
                task.job_started_at = datetime.utcnow()
            if set_completed:
                task.job_completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def auto_progress_task(
    task_id: str,
    from_stage: Stage,
    to_stage: Stage,
    order: int | None = None,
    db: Session | None = None,
) -> bool:
    """Automatically progress a task to the next stage after job completion.

    This function:
    1. Updates the task's stage in the database
    2. Triggers the command for the new stage (if any)

    Args:
        task_id: UUID of the task
        from_stage: Current stage of the task (for verification)
        to_stage: Target stage to move to
        order: Position in the new stage column (default: None = use config default)
        db: Optional database session to reuse (creates new if None).
            When provided, the caller is responsible for session lifecycle.

    Returns:
        True if auto-progression succeeded, False otherwise
    """
    # Check if auto-progression is globally enabled
    if not models.AUTO_PROGRESSION_CONFIG.enabled:
        logger.debug("Auto-progression disabled globally", extra={"task_id": task_id})
        return False

    # Check if this specific stage transition is configured
    configured_target = models.AUTO_PROGRESSION_CONFIG.stage_transitions.get(from_stage)
    if configured_target != to_stage:
        logger.debug(
            "Stage transition not configured for auto-progression",
            extra={
                "task_id": task_id,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "configured_transitions": models.AUTO_PROGRESSION_CONFIG.stage_transitions,
            },
        )
        return False

    # Use configured default order if not specified
    if order is None:
        order = models.AUTO_PROGRESSION_CONFIG.default_order

    # Session management: create new session if not provided
    should_close_session = False
    if db is None:
        db = SessionLocal()
        should_close_session = True

    try:
        task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
        if not task:
            logger.warning(
                "Auto-progress failed: Task not found",
                extra={
                    "task_id": task_id,
                    "from_stage": from_stage,
                    "to_stage": to_stage,
                },
            )
            return False

        # Verify task is still in expected stage (race condition check)
        if task.stage != from_stage:
            logger.warning(
                "Auto-progress skipped: Stage changed",
                extra={
                    "task_id": task_id,
                    "expected_stage": from_stage,
                    "actual_stage": task.stage,
                    "target_stage": to_stage,
                    "task_title": task.title,
                },
            )
            return False

        # Update stage and position
        old_stage = task.stage
        task.stage = to_stage
        task.order = order
        task.updated_at = datetime.now(UTC)
        db.commit()

        logger.info(
            "Auto-progressed task successfully",
            extra={
                "task_id": task_id,
                "task_title": task.title,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "order": order,
                "workflow_complexity": task.complexity,
            },
        )

        # Trigger command for new stage with protective error handling
        # At this point, the stage update has been committed. If trigger_stage_command
        # fails, the task is in the new stage but no command runs. This is logged
        # for visibility but doesn't rollback the stage change (partial success).
        try:
            command_triggered = trigger_stage_command(task_id, old_stage, to_stage, db)

            if command_triggered:
                logger.info(
                    "Stage command triggered after auto-progression",
                    extra={"task_id": task_id, "stage": to_stage},
                )
            else:
                logger.warning(
                    "Auto-progression completed but command trigger returned False",
                    extra={
                        "task_id": task_id,
                        "stage": to_stage,
                        "reason": "trigger_stage_command returned False (no command for stage or idempotency check)",
                    },
                )
        except Exception as trigger_error:
            logger.error(
                "Auto-progression completed but command trigger raised exception",
                extra={
                    "task_id": task_id,
                    "stage": to_stage,
                    "error": str(trigger_error),
                },
                exc_info=True,
            )
            # Don't re-raise - task is already in new stage, partial success is OK
            # Manual intervention can fix a task stuck in Review without a running job

        return True
    except Exception as e:
        logger.error(
            "Auto-progress failed with exception",
            extra={
                "task_id": task_id,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "error": str(e),
            },
            exc_info=True,
        )
        # Only rollback if we own the session
        if should_close_session:
            db.rollback()
        return False
    finally:
        # Only close if we created the session
        if should_close_session:
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
                                text_parts.append(f"\n⏺ {text}\n")
                        elif block_type == "tool_use":
                            # Format like Claude Code terminal output
                            tool_name = block.get("name", "unknown")
                            tool_input = block.get("input", {})

                            # Build tool call display
                            if tool_name == "Bash":
                                cmd = tool_input.get("command", "")
                                text_parts.append(
                                    f"\n⏺ Bash({cmd[:100]}{'...' if len(cmd) > 100 else ''})\n"
                                )
                            elif tool_name == "Read":
                                path = tool_input.get("file_path", "")
                                text_parts.append(f"\n⏺ Read({path})\n")
                            elif tool_name == "Glob":
                                pattern = tool_input.get("pattern", "")
                                text_parts.append(f"\n⏺ Glob({pattern})\n")
                            elif tool_name == "Grep":
                                pattern = tool_input.get("pattern", "")
                                path = tool_input.get("path", "")
                                text_parts.append(
                                    f"\n⏺ Grep({pattern}{', ' + path if path else ''})\n"
                                )
                            elif tool_name == "Write":
                                path = tool_input.get("file_path", "")
                                text_parts.append(f"\n⏺ Write({path})\n")
                            elif tool_name == "Edit":
                                path = tool_input.get("file_path", "")
                                text_parts.append(f"\n⏺ Edit({path})\n")
                            elif tool_name == "Task":
                                desc = tool_input.get("description", "")
                                agent = tool_input.get("subagent_type", "")
                                text_parts.append(f"\n⏺ Task({agent}: {desc})\n")
                            elif tool_name == "TodoWrite":
                                text_parts.append("\n⏺ TodoWrite()\n")
                            elif tool_name == "WebSearch":
                                query = tool_input.get("query", "")
                                text_parts.append(f"\n⏺ WebSearch({query})\n")
                            elif tool_name == "WebFetch":
                                url = tool_input.get("url", "")
                                text_parts.append(f"\n⏺ WebFetch({url})\n")
                            else:
                                text_parts.append(f"\n⏺ {tool_name}(...)\n")

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
                    # User message (includes tool results) - show like terminal
                    message = data.get("message", {})
                    for block in message.get("content", []):
                        if block.get("type") == "tool_result":
                            content = str(block.get("content", ""))
                            lines = content.strip().split("\n")

                            # Format result like Claude terminal with ⎿
                            if not content.strip():
                                text_parts.append("  ⎿  (No output)\n")
                            elif len(lines) == 1:
                                text_parts.append(f"  ⎿  {lines[0][:120]}\n")
                            elif len(lines) <= 6:
                                # Show all lines for short output
                                for line in lines:
                                    text_parts.append(f"  ⎿  {line[:120]}\n")
                            else:
                                # Show first 3 lines + count for longer output
                                for line in lines[:3]:
                                    text_parts.append(f"  ⎿  {line[:120]}\n")
                                text_parts.append(f"  ⎿  ... +{len(lines) - 3} more lines\n")
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
                    update_task_status(
                        task_id, JobStatus.RUNNING, job_output=current_text[-MAX_OUTPUT_LENGTH:]
                    )
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
            elif stage == Stage.REVIEW:
                update_task_status(
                    task_id,
                    JobStatus.COMPLETED,
                    job_output=full_output[-MAX_OUTPUT_LENGTH:],
                    review_path=file_path,
                    set_completed=True,
                )
            elif stage == Stage.CLEANUP:
                # /cleanup command handles artifact deletion
                # Clear the paths in the database since cleanup removes the files
                db = SessionLocal()
                try:
                    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
                    if task:
                        task.plan_path = None
                        task.research_path = None
                        task.review_path = None
                        db.commit()
                finally:
                    db.close()

                update_task_status(
                    task_id,
                    JobStatus.COMPLETED,
                    job_output=full_output[-MAX_OUTPUT_LENGTH:],
                    set_completed=True,
                )
            elif stage == Stage.IMPLEMENTATION:
                # Update status first
                update_task_status(
                    task_id,
                    JobStatus.COMPLETED,
                    job_output=full_output[-MAX_OUTPUT_LENGTH:],
                    set_completed=True,
                )

                logger.info(
                    "Implementation job completed, initiating auto-progression",
                    extra={"task_id": task_id, "exit_code": process.returncode},
                )

                # Auto-progress to Review stage
                success = auto_progress_task(
                    task_id,
                    from_stage=Stage.IMPLEMENTATION,
                    to_stage=Stage.REVIEW,
                    order=0,  # Place at top of Review column
                )

                if not success:
                    logger.warning(
                        "Auto-progression failed, task remains in Implementation",
                        extra={"task_id": task_id},
                    )
            else:
                # Other stages (MERGE, DONE, BACKLOG)
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
    with contextlib.suppress(ProcessLookupError):
        process.terminate()

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

    Includes idempotency protection to prevent duplicate job execution:
    - Checks in-memory running_jobs dict
    - Checks database job_status for RUNNING state
    """

    # Idempotency check 1: In-memory running jobs dict
    if task_id in running_jobs:
        logger.warning(
            "Job already running in memory, skipping trigger",
            extra={"task_id": task_id, "new_stage": new_stage},
        )
        return False

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

    # Idempotency check 2: Database job status (handles server restart case)
    if task.job_status == JobStatus.RUNNING:
        logger.warning(
            "Task already has running job in database, skipping trigger",
            extra={"task_id": task_id, "new_stage": new_stage, "job_status": task.job_status},
        )
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
