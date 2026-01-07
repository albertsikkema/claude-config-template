# Claude Flow Board - Backend Implementation Prompts

Use these prompts as input for new Claude Code sessions to implement the backend features documented in `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md`.

---

## Prompt 1: Technical Docs Fetching API

```
I need to implement a backend API endpoint for fetching technical documentation from Context7.

**Reference:** See `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md` section "1. Technical Docs Fetching Feature" for full specification.

**Task:** Implement `POST /api/docs/fetch` endpoint in the FastAPI backend.

**Requirements:**
- Accept JSON body: `{ "packages": ["react", "typescript", ...] }`
- Return immediately with status (fire-and-forget pattern)
- Trigger the `/fetch_technical_docs` slash command in background
- Documentation should be saved to `thoughts/technical_docs/`

**Response format:**
```json
{
  "status": "string",
  "message": "string"
}
```

**Implementation approach:**
1. Create a new router file `src/routers/docs.py` (or add to existing router)
2. Use background tasks to run the documentation fetch asynchronously
3. Integrate with the existing Claude Code command execution pattern

Please read the existing codebase structure first, particularly:
- How other API endpoints are structured
- How background tasks/jobs are currently handled
- The pattern used for executing Claude Code slash commands
```

---

## Prompt 2: Codebase Indexing API

```
I need to implement a backend API endpoint for triggering codebase indexing.

**Reference:** See `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md` section "2. Codebase Indexing Feature" for full specification.

**Task:** Implement `POST /api/codebase/index` endpoint in the FastAPI backend.

**Requirements:**
- No request body needed
- Return immediately with status (fire-and-forget pattern)
- Trigger the `/index_codebase` slash command in background
- Index files generated in `thoughts/codebase/`

**Response format:**
```json
{
  "status": "string",
  "message": "string"
}
```

**Implementation approach:**
1. Add endpoint to docs router or create dedicated codebase router
2. Use background tasks to run indexing asynchronously
3. Follow existing patterns for slash command execution

Please read the existing codebase to understand:
- Current router organization
- Background task execution patterns
- How `/index_codebase` is typically invoked
```

---

## Prompt 3: Security Check System

```
I need to implement a complete security check system with live output streaming and report viewing.

**Reference:** See `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md` section "3. Security Check Feature" for full specification.

**Task:** Implement the full security check API with 5 endpoints.

**Requirements:**

1. **Data Model - SecurityCheck:**
   - id: UUID (primary key)
   - status: enum('pending', 'running', 'completed', 'failed')
   - started_at: datetime
   - completed_at: datetime (nullable)
   - output: text (nullable) - accumulated stdout for streaming
   - error: text (nullable) - accumulated stderr
   - report_path: string (nullable) - path to generated report

2. **Endpoints to implement:**
   - `POST /api/security/check` - Start new security check, return SecurityCheck object
   - `GET /api/security/check/{id}` - Get check status
   - `GET /api/security/check/{id}/output` - Get live output (polled every 2 seconds by frontend)
   - `GET /api/security/check/{id}/report` - Get report content and path (404 if not available)
   - `GET /api/security/checks` - List all checks (most recent first)

3. **Background execution:**
   - Run the `/security` slash command
   - Capture stdout/stderr incrementally for live streaming
   - Update output field periodically (every 1-2 seconds)
   - Set report_path when complete (typically `thoughts/shared/reviews/security-analysis-YYYY-MM-DD.md`)

4. **Persistence:**
   - Store security check history (database table or JSON file)
   - Support listing previous checks

**Implementation approach:**
1. Create `src/models/security.py` for SecurityCheck model
2. Create `src/routers/security.py` for all endpoints
3. Use similar pattern to existing job execution but with output streaming
4. Consider using asyncio subprocess for real-time output capture

Please first explore:
- How existing jobs capture and store output
- The current database/persistence patterns
- How Claude Code slash commands are executed
```

---

## Prompt 4: JobStatus Type Update

```
I need to add 'cancelled' to the JobStatus enum in the backend.

**Reference:** See `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md` section "5. Minor Changes" for context.

**Task:** Update the JobStatus enum to include 'cancelled' status.

**Requirements:**
- Find the JobStatus enum definition in the backend models
- Add 'cancelled' as a valid status
- Ensure database migrations are handled if using SQLAlchemy/Alembic
- Check if any existing code needs to handle the new status

**Changes needed:**
```python
# Before
class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

# After
class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
```

Please locate the JobStatus definition and update it, checking for any downstream impacts.
```

---

## Prompt 5: Git Workflow Settings Backend Support (Future)

```
I need to plan backend support for git workflow settings that affect how tasks are integrated.

**Reference:** See `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md` section "4. Settings Feature" for full specification.

**Context:** The frontend has two git workflow modes stored in localStorage:
- `branch-pr`: Create feature branch → Generate PR description → Create actual PR
- `worktree-merge`: Use git worktree → Direct merge to main

**Task:** Design and implement backend support for git workflow mode.

**Requirements:**

1. **Branch + PR Workflow (`branch-pr`):**
   - When task reaches 'merge' stage:
     - Generate PR description using `/pr` slash command
     - Create actual PR via GitHub CLI (`gh pr create`)
     - Track PR URL in task
   - Handle PR merge completion

2. **Worktree + Merge Workflow (`worktree-merge`):**
   - When task starts (or reaches implementation):
     - Create git worktree for the task
   - When task reaches 'merge' stage:
     - Merge worktree changes to main
     - Push to origin
     - Clean up worktree
   - No PR creation needed

3. **Settings sync:**
   - Option A: Accept workflow mode in request headers
   - Option B: Store settings in backend with API
   - Option C: Include in task update payload when moving to merge stage

**Questions to resolve:**
- How should the frontend communicate the workflow mode to backend?
- Should we store settings server-side for consistency?
- How to handle tasks already in progress when workflow mode changes?

Please first research:
- Current task stage transition logic
- Existing git integration patterns
- How the `/pr` and `/commit` commands work
```

---

## Recommended Implementation Order

1. **Start with Prompt 4** (JobStatus update) - Quick win, unblocks other work
2. **Then Prompt 2** (Codebase Indexing) - Simple fire-and-forget pattern
3. **Then Prompt 1** (Technical Docs) - Similar pattern to indexing
4. **Then Prompt 3** (Security Check) - Most complex, build on patterns from 1 & 2
5. **Finally Prompt 5** (Git Workflow) - Requires more design decisions

---

## Session Setup

Before starting each session, ensure Claude Code has context:

```bash
# Navigate to the claude-flow backend directory
cd claude-helpers/claude-flow

# Read the changes document for context
cat claude-flow-board-changes-2026-01-06.md
```

Or start each prompt with:
```
First, please read `claude-helpers/claude-flow/claude-flow-board-changes-2026-01-06.md` to understand the full frontend API specifications.
```
