# Complete Development Workflow Guide

This guide describes the complete development workflow using Claude Code with this configuration template. The workflow is based on **"Faking a Rational Design Process in the AI Era"** - a systematic approach that ensures documentation stays current and presents a clean, rational narrative of your implementation.

## Philosophy

From Parnas & Clements (1986): *"Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process."*

**Why this matters for AI-assisted development:**
- AI assistants have **no memory between sessions**
- Documentation becomes the **"single source of truth"** that guides each interaction
- Without rationalized documentation, design decisions get lost
- Prevents the codebase from becoming a patchwork of different "styles"

**The workflow ensures:**
- ✅ Plans reflect reality (what was actually built)
- ✅ Decisions are documented (ADRs with rationale)
- ✅ Patterns are captured (CLAUDE.md updates)
- ✅ Rejected alternatives are recorded (prevents re-exploration)
- ✅ Future AI sessions have proper context

---

## The Ultra-Lean 3-File Documentation Method

> Minimal project documentation for AI-assisted development

### Why 3 Files?

Traditional project management (epics, user stories, sprints) is often overkill for small teams and AI-assisted development. This method provides **just enough** documentation for:
- AI assistants to understand project context between sessions
- Clear prioritization and progress tracking
- Traceability from completed work back to plans

### The 3 Files

#### 1. project.md - Project Context (Stable)
**Purpose**: What you're building and why

**Contains**:
- Project description and value proposition
- Technical stack (backend, frontend, infrastructure)
- Success metrics and constraints
- Architecture overview
- What's explicitly out of scope

**Update frequency**: Rarely (only when project direction changes)

#### 2. todo.md - Active Work (Living Document)
**Purpose**: What needs to be done, prioritized

**Structure**:
```markdown
## Must Haves
_Critical for MVP/current release. Cannot ship without these._

### Features
- [ ] Feature description
- [ ] [BLOCKED] Feature - blocker description
- [ ] Feature with dependency (requires: authentication)

### Bugs & Fixes
- [ ] Bug description

### Improvements
- [ ] Improvement description

### Technical & Infrastructure
- [ ] Technical work

## Should Haves
_Important but not blocking launch._
[Same categories as above]
```

**Key Features**:
- **MoSCoW prioritization**: Must Have (critical) vs Should Have (important but not blocking)
- **Inline blocking**: `[BLOCKED]` prefix with blocker description
- **Dependency tracking**:
  - Ordering (do top items first)
  - Explicit mentions: `(requires: other-feature)`
- **Categories**: Features, Bugs & Fixes, Improvements, Technical & Infrastructure

**Update frequency**: Constantly (add items, check off completed work, reorder priorities)

#### 3. done.md - Completed Work (Historical Record)
**Purpose**: Traceability from completed work to implementation

**Structure**:
```markdown
## 2025-10 October

### Features
- [x] Feature description (2025-10-20)
  - Plan: `memories/shared/plans/2025-10-20-feature.md`
  - Research: `memories/shared/research/2025-10-15-topic.md`
  - PR: #123
  - Notes: Key outcomes, metrics improved, lessons learned

### Bugs & Fixes
- [x] Bug fix (2025-10-18)
  - Issue: #456
  - PR: #457
  - Impact: Performance improved from 3s to 200ms
```

**Key Features**:
- Organized by month/year (most recent first)
- Links to plans, research, ADRs, PRs
- Same categories as todo.md
- Includes completion dates and outcomes

**Update frequency**: When work is completed (immediately after checking off in todo.md)

### Daily Workflow with 3 Files

**Daily Work:**
1. Review **todo.md** Must Haves
2. Work on highest priority unblocked item
3. When complete:
   - Check off item in todo.md
   - Add to done.md with full details (plan link, PR, notes)

**Adding New Work:**
1. Add to appropriate section in **todo.md**
2. Choose Must Have (blocking) or Should Have (nice-to-have)
3. Add category (Features/Bugs/Improvements/Technical)
4. Note dependencies if needed: `(requires: other-item)`

**Blocked Work:**
1. Add `[BLOCKED]` prefix inline: `- [ ] [BLOCKED] Item - waiting for API keys (contact@example.com)`
2. Keep in original priority section (stays Must Have or Should Have)
3. Remove `[BLOCKED]` when unblocked

**Completed Work:**
1. Check off in todo.md: `- [x] Item`
2. Add to done.md:
   - Add to current month/year section
   - Include completion date
   - Link to plan, research, ADR (if applicable)
   - Link to PR/commit
   - Add notes on outcomes or learnings
3. Remove from todo.md

### Why This Works

**For Humans**:
- Clear priorities (Must vs Should)
- Visibility into blocked work
- Progress tracking (what's done)
- Quick to scan and update

**For AI Assistants**:
- Context-rich project.md provides essential background
- Current work visible in todo.md
- Historical decisions traceable through done.md → plans → research
- No memory needed between sessions

**Lean Principles**:
- Just enough context (no exhaustive details)
- Action-focused (everything is actionable)
- Living documents (update constantly)
- Simple prioritization (2 levels, not 5)
- Traceability (links to implementation artifacts)

---

## Overview: The 8-Phase Workflow

```
Phase 0: Index (optional but recommended)
    ↓
Phase 1: Project Setup (one-time)
    ↓
Phase 2: Research
    ↓
Phase 3: Plan
    ↓
Phase 4: Implement
    ↓
Phase 5: Validate
    ↓
Phase 6: Code Review
    ↓
Phase 7: Cleanup (MANDATORY)
    ↓
Phase 8: Commit & PR
```

---

## Phase 0: Index Codebase (Optional but Recommended)

**Purpose:** Create searchable indexes of your codebase for faster research and planning.

**When to do this:**
- First time setting up the workflow
- After major refactoring
- Periodically (weekly/monthly) as codebase evolves

**Command:**
```bash
/index_codebase
```

**What it does:**
- Auto-detects Python and TypeScript projects
- Generates comprehensive indexes with:
  - All classes, functions, methods
  - File locations and line numbers
  - Dependency relationships
  - Called-by relationships
- For FastAPI projects: Fetches OpenAPI schema

**Output:**
```
memories/codebase/
├── codebase_overview_backend_py.md     # Python index
├── codebase_overview_frontend_ts.md    # TypeScript index
└── openapi.json                        # FastAPI schema (if applicable)
```

**Benefits:**
- Research agents can quickly find relevant code (file:line references)
- Planning becomes more accurate and faster
- Reduces context usage by targeting specific areas

**Example:**
```bash
You: /index_codebase

Claude: Detecting project structure...
Found Python project in: backend/
Found TypeScript project in: frontend/
Detected FastAPI - fetching OpenAPI schema...

Indexing complete:
- memories/codebase/codebase_overview_backend_py.md (2,453 lines)
- memories/codebase/codebase_overview_frontend_ts.md (1,892 lines)
- memories/codebase/openapi.json (FastAPI endpoints)

Future research and planning will be much faster!
```

---

## Phase 1: Project Setup (One-Time)

**Purpose:** Establish foundational project documentation that guides all future work.

**When to do this:**
- Once per project after installation
- When starting a new major feature/epic
- When project scope changes significantly

**Command:**
```bash
/project <what you want>
```

**What it does:**
- Creates customized project documentation from templates
- Interactive process with targeted questions
- Ensures consistency with existing documentation
- Saves to `memories/shared/project/`

**Typical Documents Created:**
```
memories/shared/project/
├── project.md                   # Project context (what/why/stack/constraints)
├── todo.md                      # Active work (Must Haves/Should Haves)
└── done.md                      # Completed work history with traceability
```

**Example:**
```bash
You: /project Create full documentation for my e-commerce platform

Claude: I'll help create comprehensive project documentation.

What is your project about? [Your description here]

What are the must-have features for MVP?
[Claude asks targeted questions based on context]

Creating documentation...
✓ memories/shared/project/project.md
✓ memories/shared/project/todo.md
✓ memories/shared/project/done.md

Your project documentation is ready!
```

**Templates Used:**
- `memories/templates/project.md.template` - Project context
- `memories/templates/todo.md.template` - Active work tracking
- `memories/templates/done.md.template` - Completed work history

---

## Phase 2: Research

**Purpose:** Thoroughly investigate and understand the codebase before making changes.

**When to do this:**
- Before creating any implementation plan
- When exploring unfamiliar code areas
- When investigating bugs or performance issues
- When evaluating different approaches

**Command:**
```bash
/research_codebase <topic or question>
```

**What it does:**
1. Checks for codebase indexes (Phase 0) and uses them for targeted research
2. Spawns parallel specialized agents:
   - `project-context-analyzer` - Project goals and requirements
   - `codebase-analyzer` - How code works (with file:line references)
   - `codebase-locator` - Where files/features exist
   - `codebase-pattern-finder` - Similar implementations
   - `memories-locator` - Historical context from memories/
3. Synthesizes findings into comprehensive research document
4. Saves with full metadata and lineage tracking

**Output:**
```
memories/shared/research/YYYY-MM-DD-topic.md
```

**Example:**
```bash
You: /research_codebase payment processing flow

Claude: I'll research the payment processing flow. Let me investigate...

[Spawns parallel agents to analyze payment code, patterns, project context]

Research complete! Here's what I found:

## Key Findings:
- Payment processing handled in `src/payments/service.py:123`
- Uses Stripe API with webhook validation
- Transaction tracking in `PaymentTransaction` model
- Missing: retry logic for failed payments

Full research: memories/shared/research/2025-10-18-payment-processing.md
```

**Research Document Structure:**
```yaml
---
date: 2025-10-18 14:30:00 CEST
file-id: [unique UUID]
researcher: albert
git_commit: abc123
branch: main
topic: "Payment processing flow"
tags: [research, codebase, payments, stripe]
status: complete
---

# Research: Payment Processing Flow

## Research Question
How does payment processing work in our application?

## Summary
[High-level findings]

## Project Context
[Relevant project goals and requirements]

## Detailed Findings
### Payment Service
- Finding with reference (src/payments/service.py:123)
[...]

## Code References
- `src/payments/service.py:123` - Main payment handler
- `src/models/payment.py:45` - PaymentTransaction model

## Architecture Insights
[Patterns discovered]

## Open Questions
[Areas needing further investigation]
```

**Pro Tips:**
- Research can include follow-up questions (appended to same document)
- Link research to related research documents
- Always include file:line references for navigation
- Run fresh research even if old research exists (code changes)

---

## Phase 3: Plan

**Purpose:** Create a detailed, actionable implementation plan based on research findings.

**When to do this:**
- After completing research (Phase 2)
- When you have a clear understanding of what needs to change
- Before any significant implementation work

**Command:**
```bash
/create_plan <description or file reference>
```

**What it does:**
1. Reads any referenced files FULLY (research docs, tickets)
2. Checks codebase indexes for targeted agent prompts
3. Spawns research agents to fill knowledge gaps
4. Interactive planning with user validation at each step:
   - Presents understanding and asks clarifying questions
   - Shows design options and gets feedback
   - Creates structure outline for approval
   - Writes detailed plan with your input
5. Saves plan with metadata linking to parent research

**Output:**
```
memories/shared/plans/YYYY-MM-DD-feature.md
```

**Example:**
```bash
You: /create_plan Add retry logic for failed payments

Claude: I'll create an implementation plan. Let me gather context...

[Reads research, checks indexes, spawns targeted agents]

Based on my research, here's my understanding:
- Failed payments currently have no retry mechanism
- Stripe webhooks can fail due to network issues
- Need exponential backoff strategy

Questions before I proceed:
1. Should retries be automatic or manual?
2. How many retry attempts?
3. What's the backoff strategy?

[Interactive back-and-forth continues]

Creating implementation plan...
✓ memories/shared/plans/2025-10-18-payment-retry-logic.md

Plan is ready for review!
```

**Plan Document Structure:**
```yaml
---
date: 2025-10-18 15:00:00 CEST
file-id: [unique UUID]
parentfile-id: [research document's file-id]
researcher: albert
git_commit: abc123
branch: feature/payment-retry
topic: "Payment retry logic implementation"
tags: [plan, payments, stripe, retry-logic]
status: pending
---

# Payment Retry Logic Implementation Plan

## Overview
[Brief description]

## Current State Analysis
[What exists, what's missing, constraints]

### Key Discoveries:
- [Finding with file:line reference from research]

## Desired End State
[Specification with verification steps]

## What We're NOT Doing
[Explicit out-of-scope items]

## Implementation Approach
[High-level strategy]

## Phase 1: Add Retry Queue

### Overview
[What this accomplishes]

### Changes Required:

#### 1. Database Schema
**File**: `src/models/payment.py`
**Changes**: Add retry tracking fields

```python
class PaymentTransaction(Base):
    # Existing fields...
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    max_retries = Column(Integer, default=3)
```

### Success Criteria:

#### Automated Verification:
- [ ] Migration applies: `make migrate`
- [ ] Tests pass: `make test-payments`
- [ ] Type checking: `make typecheck`

#### Manual Verification:
- [ ] Can view retry status in admin panel
- [ ] Failed payments queue for retry

---

## Phase 2: Implement Retry Logic
[Similar structure...]

---

## Testing Strategy
[Comprehensive testing approach]

## Performance Considerations
[Impact analysis]

## Migration Notes
[Data migration strategy]

## References
- Research: `memories/shared/research/2025-10-18-payment-processing.md`
- Stripe Docs: [URL]
```

**Critical Guidelines:**
- Plans assume perfect knowledge (even though you don't have it)
- Separate automated vs manual success criteria
- Include specific file:line references
- Break into phases for incremental progress
- Resolve all open questions before finalizing
- Interactive - get buy-in at each step

---

## Phase 4: Implement

**Purpose:** Execute the approved implementation plan step-by-step.

**When to do this:**
- After plan is approved (Phase 3)
- When you're ready to write code

**Command:**
```bash
/implement_plan memories/shared/plans/YYYY-MM-DD-feature.md
```

**What it does:**
1. Reads plan completely, checks for existing checkmarks
2. Reads original research/ticket and all mentioned files FULLY
3. Creates todo list to track progress
4. Implements each phase sequentially
5. Updates checkboxes `- [x]` in plan as work completes
6. Verifies work against success criteria
7. Stops if finds mismatches between plan and reality

**Example:**
```bash
You: /implement_plan memories/shared/plans/2025-10-18-payment-retry-logic.md

Claude: Reading plan and gathering context...

Creating implementation todo list:
- [ ] Phase 1: Add retry queue
- [ ] Phase 2: Implement retry logic
- [ ] Phase 3: Add monitoring

Starting implementation...

[Implements Phase 1]
✓ Created migration for retry fields
✓ Updated PaymentTransaction model
✓ Tests passing

Updating plan with checkmarks...

[Continues through all phases]

Implementation complete! All phases done.
Next: /validate_plan to verify correctness
```

**Key Behaviors:**
- Follows plan's intent while adapting to code reality
- Implements fully before moving to next phase
- Updates plan checkboxes as sections complete
- Runs verification at natural stopping points
- **STOPS** if plan significantly differs from reality (asks for guidance)
- Can resume from last unchecked item if interrupted

**Success Criteria Execution:**
- **Automated**: Runs commands like `make test`, `make lint`
- **Manual**: Notes what needs human verification

---

## Phase 5: Validate

**Purpose:** Verify implementation correctness against the plan and success criteria.

**When to do this:**
- After implementation (Phase 4)
- Before cleanup (Phase 6)
- To verify all requirements were met

**Command:**
```bash
/validate_plan memories/shared/plans/YYYY-MM-DD-feature.md
```

**What it does:**
1. Reads implementation plan completely
2. Analyzes git history to discover what was implemented
3. Spawns parallel agents to verify:
   - Database changes match plan
   - Code changes are complete
   - Tests cover requirements
4. Runs all automated verification commands
5. Generates comprehensive validation report
6. Identifies deviations from plan

**Example:**
```bash
You: /validate_plan memories/shared/plans/2025-10-18-payment-retry-logic.md

Claude: Validating implementation against plan...

[Analyzes git history, spawns verification agents]

## Validation Report: Payment Retry Logic

### Implementation Status
✓ Phase 1: Add Retry Queue - Fully implemented
✓ Phase 2: Implement Retry Logic - Fully implemented
✓ Phase 3: Add Monitoring - Fully implemented

### Automated Verification Results
✓ Migration applies: `make migrate`
✓ Tests pass: `make test-payments` (45 tests, 100% coverage)
✓ Type checking: `make typecheck`
✗ Linting: `make lint` (2 warnings in retry_service.py)

### Deviations from Plan:
- Used exponential backoff instead of linear (improvement)
- Added retry_reason field to track failure causes (enhancement)

### Manual Testing Required:
- [ ] Verify retry UI in admin panel
- [ ] Test with actual failed Stripe webhook
- [ ] Confirm monitoring alerts trigger

### Recommendations:
- Fix linting warnings before merge
- Consider adding integration test for full retry flow
- Update API documentation with retry endpoints

Implementation is solid! Address linting, then run cleanup.
```

**Validation Report Sections:**
- Implementation status (phases completed)
- Automated verification results
- Code review findings (matches plan, deviations, issues)
- Manual testing checklist
- Recommendations for improvement

---

## Phase 6: Code Review

**Purpose:** Review code quality, security, and best practices before documenting and committing changes.

**When to do this:**
- After validation passes (Phase 5)
- Before cleanup (Phase 7)
- Recommended for all non-trivial implementations

**Command:**
```bash
/code_reviewer
```

**What it does:**
1. **Analyzes Code Quality**:
   - Reviews recent changes in the codebase
   - Identifies code smells and anti-patterns
   - Checks adherence to language-specific best practices
   - Reviews error handling and edge cases

2. **Security Review**:
   - Identifies potential security vulnerabilities
   - Checks for common OWASP issues
   - Reviews input validation and sanitization
   - Checks for secure coding practices

3. **Provides Actionable Feedback**:
   - Prioritized list of issues (critical, high, medium, low)
   - Specific code locations with line numbers
   - Suggested fixes with code examples
   - Explains why each issue matters

**Example:**
```bash
You: /code_reviewer

Claude: Reviewing recent code changes...

[Analyzes git diff, security patterns, best practices]

## Code Review Report

### Critical Issues (2)
1. **SQL Injection Risk** (src/api/payments.ts:45)
   - User input directly concatenated in query
   - Fix: Use parameterized queries

2. **Missing Error Handling** (src/services/retry.ts:78)
   - Unhandled promise rejection
   - Fix: Add try/catch block

### High Priority (3)
...

### Medium Priority (5)
...

All critical issues should be addressed before proceeding to cleanup.
```

**When to skip:**
- Trivial changes (documentation, config)
- Urgent hotfixes (review after deployment)

---

## Phase 7: Cleanup (MANDATORY)

**Purpose:** Document best practices and update documentation to reflect what actually happened, presented as if it was always the plan.

**This is the most important phase** - it captures the messy reality of implementation and transforms it into a clean, coherent narrative that will guide future AI sessions.

**When to do this:**
- After code review (Phase 6)
- Before creating commits (Phase 8)
- **MANDATORY** - Never skip this step

**Command:**
```bash
/cleanup memories/shared/plans/YYYY-MM-DD-feature.md
```

**What it does:**
1. **Investigates Reality**:
   - Reads implementation plan
   - Analyzes git history since plan was created
   - Spawns parallel agents:
     - `codebase-analyzer` - How implementation actually works
     - `codebase-pattern-finder` - Patterns that emerged
     - `memories-analyzer` - Historical context
     - `project-context-analyzer` - Project documentation review

2. **Investigates What Actually Happened**:
   - Documents discoveries made during implementation
   - Lists technical decisions with rationale
   - Captures rejected alternatives
   - Identifies patterns/conventions discovered

3. **Interactive Decision Making**:
   - Presents findings to you
   - Asks which decisions warrant ADRs
   - Asks which patterns should go in CLAUDE.md
   - Asks if plan should be updated
   - Gets your approval on what to document

4. **Creates Permanent Outputs**:
   - **Best Practices**: Documented patterns in `memories/best_practices/`
   - **CLAUDE.md Updates**: New patterns and conventions
   - **Project Docs**: Updated todo.md, done.md, project.md

**Example:**
```bash
You: /cleanup memories/shared/plans/2025-10-18-payment-retry-logic.md

Claude: Analyzing implementation vs plan...

[Analyzes git history, reads changed files]

## Key Discoveries During Implementation:
1. **Discovery**: Exponential backoff works better than linear
   - **Impact**: Changed retry strategy mid-implementation

2. **Discovery**: Need to track failure reasons
   - **Impact**: Added retry_reason field (not in plan)
   - **Why**: Critical for debugging and monitoring

### Technical Decisions Made:
1. **Decision**: Use Celery for retry queue
   - **Context**: Needed reliable background task processing
   - **Rationale**: Already using Celery, avoids new dependency
   - **Alternatives**: Redis Queue (more to maintain), AWS SQS (vendor lock-in)
   - **ADR Needed?**: Yes - significant architectural choice

2. **Decision**: Max 3 retries with exponential backoff
   - **Context**: Balance recovery vs resource usage
   - **Rationale**: 3 retries covers 99% of transient failures
   - **ADR Needed?**: Yes - business logic decision

### Rejected Alternatives:
1. **Linear backoff**: Tried first, caused server congestion
2. **Immediate retry**: Failed due to Stripe rate limits

### Patterns Discovered:
1. **Pattern**: Retry decorator for idempotent operations
   - Add to CLAUDE.md?: Yes
2. **Convention**: Always log retry attempts
   - Add to CLAUDE.md?: Yes

---

✓ Created best practice: retry-exponential-backoff-pattern.md
✓ Updated CLAUDE.md:
  - Added "Retry Pattern" to Architecture Patterns section
✓ Updated project docs:
  - todo.md: marked payment retry as complete
  - done.md: added with plan link and notes

Cleanup complete! All knowledge captured in:
- Best practices (novel patterns)
- CLAUDE.md (reusable conventions)
- Project docs (todo.md, done.md updated)
```

**The Rationalization Philosophy (Parnas & Clements, 1986):**

The cleanup phase implements "Faking a Rational Design Process" — presenting the refined, polished version of what happened rather than the messy discovery path. This isn't lying:

- The messy reality is captured: rejected alternatives, unexpected discoveries, decisions made under pressure
- The clean narrative is what guides future work: best practices, updated conventions, project docs
- Like mathematicians publish elegant proofs, not the tortured discovery process

**Why Cleanup is Mandatory:**

1. **AI Has No Memory**: Without updated docs, next session loses all context
2. **Prevents Re-exploration**: Rejected alternatives and dead ends are documented so they aren't tried again
3. **Builds Knowledge**: CLAUDE.md and best practices become smarter with each implementation
4. **Clean Narrative**: Future developers (and AI sessions) see coherent decisions, not messy iteration
5. **Keeps Project Docs Current**: todo.md and done.md stay in sync

---

## Phase 8: Commit & PR

**Purpose:** Create well-formatted git commits and comprehensive PR description.

**When to do this:**
- After cleanup (Phase 7)
- When implementation is complete and documented

### Step 8a: Create Commits

**Command:**
```bash
/commit
```

**What it does:**
1. Reviews conversation history and changes
2. Plans logical commits with clear messages
3. Presents commit plan to you for approval
4. Creates commits following project conventions
5. Uses imperative mood, focuses on "why"

**Example:**
```bash
You: /commit

Claude: I'll create commits for the payment retry implementation.

## Proposed Commits:

1. **Add retry fields to PaymentTransaction model**
   - Migration: Add retry_count, next_retry_at, max_retries, retry_reason
   - Update model with retry tracking

   Why: Foundation for retry logic, tracks retry state and history

2. **Implement exponential backoff retry service**
   - Add RetryService with Celery tasks
   - Implement exponential backoff (1min, 2min, 4min)
   - Add retry reason tracking

   Why: Handles transient payment failures automatically with smart backoff

3. **Add monitoring and alerting for retries**
   - Add retry metrics to monitoring dashboard
   - Configure alerts for high retry rates
   - Add logging for retry attempts

   Why: Operations visibility into payment health

Should I proceed with these commits?

You: Yes

Claude: Creating commits...

✓ Commit 1/3: Add retry fields to PaymentTransaction model
✓ Commit 2/3: Implement exponential backoff retry service
✓ Commit 3/3: Add monitoring and alerting for retries

All commits created! Next: /pr
```

**Commit Message Format:**
```
Subject line (imperative, 50 chars)

Body explaining:
- What changed (briefly)
- Why it changed (focus here)
- Any important context

References: ENG-1234
```

### Step 8b: Create PR Description

**Command:**
```bash
/pr
```

**What it does:**
1. Reads PR description template (if exists)
2. Gathers full PR diff and commit history via `gh` CLI
3. Analyzes changes thoroughly for impact
4. Runs verification commands when possible
5. Generates comprehensive PR description
6. Saves to `memories/shared/prs/{number}_description.md`
7. Updates PR description directly via `gh pr edit`

**Example:**
```bash
You: /pr

Claude: Generating PR description...

[Analyzes git diff, commit history, runs tests]

## PR Description Created

### Summary
Implements automatic retry logic for failed payment processing with exponential backoff strategy. Handles transient Stripe API failures and webhook delivery issues.

### Changes
- **Database**: Added retry tracking fields to PaymentTransaction
- **Service**: New RetryService using Celery for background processing
- **Monitoring**: Retry metrics and alerting
- **Tests**: 12 new tests covering retry scenarios

### Technical Details
- Exponential backoff: 1min → 2min → 4min
- Max 3 retries per payment
- Celery queue: `payment_retries`
- Tracks failure reasons for debugging

### Testing
✓ All tests passing (45 tests)
✓ Type checking passed
✓ Linting clean
- [ ] Manual: Test with failed Stripe webhook
- [ ] Manual: Verify admin panel shows retry status

### References
- Plan: memories/shared/plans/2025-10-18-payment-retry-logic.md
- Research: memories/shared/research/2025-10-18-payment-processing.md
- Ticket: ENG-1234

---

PR description saved to: memories/shared/prs/123_description.md
Updated PR #123 on GitHub

Your PR is ready for review!
```

---

## Complete Workflow Example

Here's how the entire workflow looks in practice:

```bash
# ============================================================
# Phase 0: Index (First time or after major changes)
# ============================================================
You: /index_codebase

Claude: Indexing codebase...
✓ Python index: memories/codebase/codebase_overview_backend_py.md
✓ TypeScript index: memories/codebase/codebase_overview_frontend_ts.md
✓ FastAPI schema: memories/codebase/openapi.json

Future research will be much faster!

# ============================================================
# Phase 1: Project Setup (One-time)
# ============================================================
You: /project Create full documentation for e-commerce platform

Claude: [Interactive questions about project...]

✓ memories/shared/project/project.md
✓ memories/shared/project/todo.md
✓ memories/shared/project/done.md

Your project documentation is ready!

# ============================================================
# Phase 2: Research
# ============================================================
You: /research_codebase payment processing flow

Claude: [Spawns parallel agents, uses indexes for targeting...]

Research complete!
- Stripe integration at src/payments/service.py:123
- Missing: retry logic for failures
- Pattern: webhook validation in all payment endpoints

Full research: memories/shared/research/2025-10-18-payment-processing.md

# ============================================================
# Phase 3: Plan
# ============================================================
You: /create_plan Add retry logic for failed payments

Claude: [Interactive planning with research context...]

Questions:
1. How many retries? → You: 3 with exponential backoff
2. Automatic or manual? → You: Automatic
3. Monitoring needed? → You: Yes, with alerts

Creating plan...
✓ memories/shared/plans/2025-10-18-payment-retry-logic.md

Plan ready! Includes 3 phases:
1. Add retry queue
2. Implement retry logic
3. Add monitoring

# ============================================================
# Phase 4: Implement
# ============================================================
You: /implement_plan memories/shared/plans/2025-10-18-payment-retry-logic.md

Claude: [Implements all phases, updates checkboxes...]

✓ Phase 1: Add retry queue
✓ Phase 2: Implement retry logic
✓ Phase 3: Add monitoring

Implementation complete! All tests passing.

# ============================================================
# Phase 5: Validate
# ============================================================
You: /validate_plan memories/shared/plans/2025-10-18-payment-retry-logic.md

Claude: [Analyzes implementation, runs verifications...]

Validation Report:
✓ All phases implemented
✓ Tests passing (45 tests, 100% coverage)
✓ Type checking passed
✗ 2 linting warnings (fixable)

Deviations:
- Used exponential backoff (improvement over linear)
- Added retry_reason field (enhancement)

Ready for code review after fixing lint!

# ============================================================
# Phase 6: Code Review
# ============================================================
You: /code_reviewer

Claude: Reviewing recent code changes...

[Analyzes git diff, security patterns, best practices]

## Code Review Report

### Summary
Payment retry logic implementation looks solid. Found 2 minor issues and several good practices.

### Critical Issues
None found.

### Improvements (2)
1. **Add input validation** (src/services/retry.ts:45)
   - Consider validating retry_count before processing

2. **Error logging enhancement** (src/services/retry.ts:78)
   - Add structured logging for better observability

### Well Done
- Excellent error handling throughout
- Good separation of concerns
- Comprehensive test coverage

All issues are minor - safe to proceed to cleanup.

# ============================================================
# Phase 7: Cleanup (MANDATORY)
# ============================================================
You: /cleanup memories/shared/plans/2025-10-18-payment-retry-logic.md

Claude: [Analyzes what actually happened vs plan...]

✓ Created best practice: retry-exponential-backoff-pattern.md
✓ Updated CLAUDE.md with retry patterns
✓ Updated project docs (todo.md → done.md)
✓ Committed cleanup changes
✓ Created PR: https://github.com/org/repo/pull/123

Cleanup complete!
```

---

## Document Lineage and Traceability

The workflow creates a traceable lineage of decisions:

```
Project Documentation (project.md, todo.md, done.md)
    ↓ informs
Research (file-id: uuid-1)
    ↓ parentfile-id
Plan (file-id: uuid-2, parentfile-id: uuid-1)
    ↓ implemented
Review (code review with verdict)
    ↓ cleanup
Best Practices + CLAUDE.md updates + PR
```

**Every document includes metadata:**
```yaml
date: 2025-10-18 16:30:00 CEST
file-id: unique-uuid-for-this-doc
parentfile-id: uuid-of-parent-doc
researcher: albert
git_commit: abc123def
branch: feature/payment-retry
repository: claude-config-template
claude-sessionid: session-uuid
```

This creates a complete audit trail:
- What was researched (research docs)
- What was planned (plan docs)
- What decisions were made (ADRs)
- What patterns emerged (CLAUDE.md)
- What was actually built (git commits)
- Why it was built that way (best practices, CLAUDE.md)

---

## File Naming Conventions

**Research & Plans:**
```
YYYY-MM-DD-description.md
YYYY-MM-DD-TICKET-123-description.md

Examples:
memories/shared/research/2025-10-18-payment-processing.md
memories/shared/plans/2025-10-18-ENG-1234-payment-retry.md
```

**Best Practices:**
```
[category]-[topic].md

Examples:
memories/best_practices/api-fire-and-forget-claude-integration.md
memories/best_practices/security-defense-in-depth-validation.md
```

**Project Documentation:**
```
Ultra-lean 3-file structure

Examples:
memories/shared/project/project.md    # Project context
memories/shared/project/todo.md       # Active work
memories/shared/project/done.md       # Completed work history
```

---

## Tips for Success

### 1. Always Index First
- Run `/index_codebase` before starting work
- Re-index after major refactoring
- Indexes make research 10x faster

### 2. Never Skip Research
- Even for "small" changes
- Research prevents wrong assumptions
- Discovers existing patterns to follow

### 3. Make Plans Interactive
- Don't rush through questions
- Provide detailed answers
- Review outline before full plan
- Better planning = easier implementation

### 4. Implement One Phase at a Time
- Don't jump ahead
- Verify each phase before next
- Easier to debug when issues arise

### 5. Always Validate
- Catches issues before cleanup
- Identifies deviations early
- Ensures nothing was missed

### 6. NEVER Skip Cleanup
- This is where knowledge is preserved
- Future you will thank present you
- Future AI sessions depend on this
- Takes 10 minutes, saves hours later

### 7. Update CLAUDE.md Regularly
- Add patterns as they emerge
- Update conventions when they change
- Remove outdated information
- Keep it current and relevant

---

## Troubleshooting

### "Research is taking too long"
- **Solution**: Run `/index_codebase` first
- Indexes enable targeted research with file:line references
- Reduces context usage dramatically

### "Plan doesn't match codebase reality"
- **Solution**: This is normal! Plans assume perfect knowledge
- During `/implement_plan`, adjust as needed
- Document changes during `/cleanup`
- Update plan to show final approach as intended

### "I forgot to run cleanup"
- **Solution**: You can still run cleanup after commits
- Git history shows what changed
- ADRs and CLAUDE.md still valuable
- Better late than never!

### "Too many ADRs"
- **Solution**: Not every decision needs an ADR
- Focus on: architecture, technology choices, design patterns
- Skip: minor implementation details, obvious choices
- Quality over quantity

### "CLAUDE.md getting too long"
- **Solution**: Organize into sections
- Use table of contents
- Move historical info to ADRs
- Keep CLAUDE.md focused on current patterns

---

## What Makes This Workflow Special

**Traditional Development:**
```
Code → Commit → PR → (documentation maybe?)
```
- Documentation lags reality
- Decisions lost in code reviews
- Patterns not captured
- Each AI session starts from scratch

**This Workflow:**
```
Research → Plan → Implement → Review → Cleanup → PR
```
- Documentation reflects reality (cleanup ensures it)
- Decisions preserved in best practices
- Patterns captured in CLAUDE.md
- Each AI session builds on previous knowledge

**The Result:**
- ✅ Coherent architecture emerges from coherent documentation
- ✅ More effective AI collaboration (proper context every session)
- ✅ Easier maintenance (understand why, not just what)
- ✅ Reduced technical debt (decisions documented systematically)
- ✅ Knowledge compounds over time (instead of being lost)

---

## Summary

The complete workflow is:

0. **Index** (optional but recommended) → Faster research
1. **Project Setup** (one-time) → Foundation for all work
2. **Research** → Understand before changing
3. **Plan** → Design with full knowledge
4. **Implement** → Execute systematically
5. **Validate** → Verify correctness
6. **Rationalize** (MANDATORY) → Clean up the narrative
7. **Commit & PR** → Ship with confidence

**The key insight from Parnas (1986):**
> "It's not about achieving perfect rationality (impossible), but about documenting as if you had."

In the AI era, this transforms from nice-to-have into **essential discipline**.

Your documentation is no longer just a record of what you built—it's the instruction manual that guides every AI interaction toward your vision.

**Keep it current, keep it rational, and keep faking it.** The results will speak for themselves. 🚀
