# Rationalize Implementation

You are tasked with rationalizing a completed implementation by analyzing what actually happened versus what was planned, and updating documentation to present a clean, coherent narrative—as if the final approach was always the plan.

This implements the "Review & Rationalization Phase" from the blog post "Faking a Rational Design Process in the AI Era", completing the Research → Plan → Implement → Rationalize workflow.

## Philosophy

From Parnas and Clements (1986): Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process. This doesn't mean lying—it means presenting the refined, polished version of our work.

**What rationalization does:**
- Captures what was tried (rejected alternatives)
- Presents the final solution cleanly (updated plan)
- Documents the reasoning (ADRs with rationale)
- Learns from the process (updates to CLAUDE.md)
- Keeps project documentation in sync (project.md, todo.md, done.md)

## Initial Response

When this command is invoked:

1. **Check if a plan file was provided as parameter**:
   - If provided: skip intro, read the plan file immediately, begin rationalization
   - If not provided: show the helpful message below

2. **If no parameter provided**, respond with:
```
I'll help you rationalize your implementation and update documentation to present a clean narrative.

Please provide the implementation plan you want to rationalize:
- Plan file path: e.g., `thoughts/shared/plans/2025-10-18-feature.md`
- Or describe what you implemented: "The authentication feature we just built"

I'll analyze what changed from the plan, help document decisions made, and update all relevant documentation.

Tip: Quick invoke with: `/rationalize thoughts/shared/plans/2025-10-18-feature.md`
```

Then wait for the user's input.

## Process Steps

### Step 1: Gather Context

1. **Read the implementation plan FULLY**:
   - Use Read tool WITHOUT limit/offset parameters
   - Read the entire plan in main context
   - Identify the plan's creation date and commit

2. **Analyze git history since plan creation**:
   ```bash
   # Find commits since plan was created
   git log --since="[plan date]" --oneline --no-merges

   # See what files changed
   git diff [plan-commit]..HEAD --stat

   # Get detailed diff for analysis
   git diff [plan-commit]..HEAD
   ```

3. **Read all files mentioned in the plan**:
   - Read FULLY without limit/offset
   - Compare current state to what plan described
   - Note differences

4. **Create rationalization todo list**:
   - Use TodoWrite to track rationalization tasks
   - Include: investigation, document creation, plan updates, ADR creation, CLAUDE.md updates

### Step 2: Investigation - What Actually Happened?

Spawn parallel research agents to discover implementation reality:

1. **Implementation Analysis** (codebase-analyzer):
   - Analyze the implemented code
   - How does it work now?
   - What's different from what the plan described?
   - Provide specific file:line references for all findings

2. **Pattern Discovery** (codebase-pattern-finder):
   - What patterns emerged from implementation?
   - Are there similar features to compare?
   - What conventions were established or followed?

3. **Historical Context** (thoughts-analyzer):
   - Check for related research documents
   - Look for related plans or earlier decisions
   - Find any existing ADRs that relate

4. **Project Documentation Review** (project-context-analyzer):
   - Read current CLAUDE.md
   - Review existing ADRs in thoughts/shared/adrs/
   - Check project documentation for relevant sections
   - Review thoughts/shared/project/project.md for context
   - Check thoughts/shared/project/todo.md for current/planned work
   - Review thoughts/shared/project/done.md for completed work

**IMPORTANT**: Wait for ALL sub-agents to complete before proceeding.

### Step 3: Create Working Rationalization Document

This is a **temporary working document** that will be deleted when rationalization is complete.

1. **Gather metadata**:
- Run the `claude-helpers/spec_metadata.sh` script to generate all relevant metadata

2. **Create rationalization working doc** at `thoughts/shared/rationalization/YYYY-MM-DD-[topic].md`:

Use this template:

```markdown
---
date: [ISO format with timezone from metadata]
file-id: [UUID from metadata]
parentfile-id: [plan's file-id - find this in the plan's frontmatter]
claude-sessionid: [session ID from metadata]
researcher: [Username from metadata]
git_commit: [Current commit hash]
branch: [Branch name]
repository: [Repository name]
topic: "[What was rationalized]"
tags: [rationalization, relevant-components]
status: in_progress
last_updated: [YYYY-MM-DD HH:mm]
last_updated_by: [Username]
related_plan: thoughts/shared/plans/YYYY-MM-DD-[topic].md
---

# Rationalization: [Feature/Topic]

**Date**: [timestamp]
**Related Plan**: `thoughts/shared/plans/YYYY-MM-DD-[topic].md`
**Git Commit Range**: [plan-commit]...[current-commit]

> **NOTE**: This is a working document for the rationalization process.
> It will be DELETED when rationalization is complete.
> Permanent outputs: updated plan, ADRs, CLAUDE.md updates.

## Summary
[What was implemented and how it evolved from the plan]

## Implementation Evolution

### Original Plan Approach
[Summary of what the plan described - quote relevant sections]

### What Actually Happened
[Summary of final implementation with file:line references]

### Key Discoveries During Implementation

1. **Discovery**: [What was learned]
   - **Impact**: [How it changed the approach]
   - **Evidence**: [file.ext:line or commit reference]
   - **Why this matters**: [Explanation]

2. **Discovery**: [Another finding]
   - **Impact**: [Effect on implementation]
   - **Evidence**: [file.ext:line]
   - **Why this matters**: [Explanation]

[Continue for all significant discoveries...]

## Technical Decisions Made

List all significant technical decisions that emerged during implementation:

1. **Decision**: [What was chosen]
   - **Context**: [What problem this solved]
   - **Rationale**: [Why this approach]
   - **Alternatives Considered**: [What else was possible]
   - **Trade-offs**: [What we gave up, what we gained]
   - **Code Reference**: [file.ext:line]
   - **ADR Needed?**: Yes/No - [If yes, note ADR number to create]

2. **Decision**: [Another decision]
   [Same structure...]

## Rejected Alternatives

Document approaches that were tried and didn't work (prevents re-exploration):

### Approach 1: [Name]
**What we tried**: [Description with code examples if available]
**Why it didn't work**: [Technical reason, issue encountered]
**When we tried it**: [Commit or timeframe]
**Don't try this again because**: [Key lesson]

### Approach 2: [Name]
[Same structure...]

## Patterns & Conventions Discovered

New patterns or conventions that emerged:

1. **Pattern**: [Name of pattern]
   - **Description**: [What it is]
   - **Where used**: [file.ext:line]
   - **When to use**: [Guidance for future]
   - **Add to CLAUDE.md?**: Yes/No

2. **Convention**: [Name]
   [Same structure...]

## Rationalized Narrative

### The Approach (As Intended)

[This is the clean story - write this as if the final implementation was always the plan.
Present the solution elegantly, showing the key insights and decisions as if they were
obvious from the start. This section should read like good technical documentation,
not a discovery journal.]

Example structure:
- High-level approach and why it's right for this problem
- Key architectural decisions and their rationale
- Important implementation details
- How it integrates with existing systems

### Code References
- `src/feature/main.py:123` - Core implementation
- `src/models/entity.py:45` - Data model
- `tests/test_feature.py:67` - Test patterns

## Documentation Updates Needed

### Plan Updates
Track what needs to change in the original plan:

- [ ] Phase 1: Update to reflect [specific change]
- [ ] Phase 2: Add section for [discovery made during implementation]
- [ ] Success Criteria: Update to include [new verification]
- [ ] Add note at top linking to this rationalization (temporary, will remove when done)

### CLAUDE.md Updates
What should be added to project documentation:

- [ ] Add pattern: [Pattern name] to [section of CLAUDE.md]
- [ ] Update [section]: [what to change]
- [ ] Add to "Common Pitfalls": [lesson learned]
- [ ] Update [section]: [convention established]

### ADRs to Create
List ADRs needed for significant decisions:

- [ ] ADR-001: [Decision title] - [Brief description]
- [ ] ADR-002: [Another decision] - [Brief description]

### Project Documentation Updates
Track what needs to change in project documentation:

**todo.md** (`thoughts/shared/project/todo.md`):
- [ ] Move completed items from Must Haves/Should Haves to done.md
- [ ] Remove `[BLOCKED]` prefix if any items were unblocked
- [ ] Add new technical debt or work items discovered during implementation
- [ ] Update priorities based on implementation experience
- [ ] Reorder items if dependencies changed

**done.md** (`thoughts/shared/project/done.md`):
- [ ] Add completed work items with completion date
- [ ] Link to this implementation plan
- [ ] Link to relevant research documents
- [ ] Link to ADRs created during rationalization
- [ ] Link to PR/commits
- [ ] Add key outcomes and learnings

**project.md** (`thoughts/shared/project/project.md`):
- [ ] Update architecture section if significant changes
- [ ] Update technical stack if new dependencies added
- [ ] Update constraints if any were discovered
- [ ] Update "Out of Scope" if scope decisions were made

## Code References Summary
- `path/to/file.ext:123` - [What's there]
- `another/file.ext:45` - [What's there]

## Next Steps
- [ ] Review this rationalization with user
- [ ] Get approval on which updates to make
- [ ] Create ADRs
- [ ] Update plan
- [ ] Update CLAUDE.md
- [ ] Delete this rationalization document
```

### Step 4: Interactive Review & Decision Making

Present the rationalization to the user and ask what to update:

```
I've analyzed the implementation and created a working rationalization document.

Here's what I found:

## Key Discoveries
[Summarize 3-5 most important discoveries]

## Decisions Made During Implementation
[List significant technical decisions with brief rationale]

## Rejected Alternatives
[List approaches that didn't work]

## Documentation Updates Needed

I've identified these potential updates:

### ADRs (Architecture Decision Records)
[List decisions that warrant ADRs]

Which of these should I create ADRs for?
- All of them
- Let me select specific ones
- Skip ADRs for now

### CLAUDE.md Updates
[List patterns/conventions to add]

Which should I add to CLAUDE.md?
- All of them
- Let me select specific ones
- Skip CLAUDE.md updates for now

### Plan Updates
The plan needs updates to reflect what actually happened. Should I:
- Update the plan to show the final approach (recommended)
- Leave the plan as-is
- Let me review the changes first

### Project Documentation Updates
[List updates needed for todo.md, done.md, project.md]

Which project documentation should I update?
- All relevant documents
- Let me select specific documents
- Skip project documentation updates for now

The full rationalization is at: thoughts/shared/rationalization/YYYY-MM-DD-topic.md
```

Wait for user's response on what to update.

### Step 5: Create ADRs (if requested)

For each ADR the user wants created:

1. **Determine ADR number**:
   - Check thoughts/shared/adrs/ for existing ADRs
   - Use next sequential number (001, 002, etc.)

2. **Create ADR file** at `thoughts/shared/adrs/NNN-decision-title.md`:

```markdown
# ADR-NNN: [Decision Title]

**Date**: [YYYY-MM-DD]
**Status**: Accepted
**Deciders**: [Username from metadata]
**Related**: [Link to implementation plan]

## Context

[What is the issue we're seeing that is motivating this decision?
Include background, constraints, and requirements that led to this decision.]

## Decision

[What is the change we're actually proposing or have agreed to implement?
Be specific and clear about what was decided.]

## Rationale

[Why did we choose this approach?
Include technical reasoning, alignment with project goals, and key insights.]

## Consequences

### What becomes easier:
- [Benefit 1]
- [Benefit 2]

### What becomes more difficult:
- [Trade-off 1]
- [Trade-off 2]

## Alternatives Considered

### Option 1: [Alternative approach name]
**Description**: [What it would have been]
**Pros**:
- [Benefit]
**Cons**:
- [Drawback]
**Why rejected**: [Key reason this wasn't chosen]

### Option 2: [Another alternative]
[Same structure...]

## Implementation

**Code References**:
- `path/to/file.ext:line` - [What's implemented]

**Related Documents**:
- Implementation Plan: `thoughts/shared/plans/YYYY-MM-DD-topic.md`

## Notes

[Any additional context, future considerations, or related decisions]
```

3. **Update the ADR index** if one exists at `thoughts/shared/adrs/README.md`

### Step 6: Update Plan (if requested)

Edit the implementation plan to reflect the rationalized narrative:

1. **Add rationalization note at top** (temporary - will be removed after cleanup):
   ```markdown
   > **Rationalization in Progress**
   > This plan is being updated to reflect the final implementation.
   > Working doc: `thoughts/shared/rationalization/YYYY-MM-DD-topic.md`
   ```

2. **Update phases to reflect final approach**:
   - Rewrite implementation steps to show what was actually done
   - Present changes as if they were always the plan
   - Keep the phase structure, update the details
   - Update code examples to match reality
   - Adjust file references to actual locations

3. **Update success criteria if needed**:
   - Add any new verification steps discovered
   - Update commands to reflect actual testing approach

4. **Keep the clean narrative**:
   - Don't document the tortured path
   - Show the elegant solution
   - Rejected alternatives are documented in ADRs, not in the plan

### Step 7: Update CLAUDE.md (if requested)

For each pattern/convention to add:

1. **Identify the right section**:
   - Architecture patterns → Architecture section
   - Coding standards → Coding standards section
   - Testing patterns → Testing section
   - Common pitfalls → Common Pitfalls section (create if doesn't exist)

2. **Add the update**:
   - Use Edit tool to add to appropriate section
   - Include code examples where relevant
   - Reference file:line for real examples in the codebase
   - Keep formatting consistent with existing CLAUDE.md style

3. **Create "Common Pitfalls" section if it doesn't exist**:
   ```markdown
   ## Common Pitfalls

   [List of things to avoid with explanations of why and how to do it correctly instead]
   ```

### Step 8: Update Project Documentation (if requested)

For each project documentation file that needs updates:

1. **Discover existing project documentation**:
   ```bash
   # Find project documentation files
   find thoughts/shared/project -type f -name "*.md" 2>/dev/null
   ```

2. **Read relevant files**:
   - Read FULLY without limit/offset parameters
   - Identify what needs to be updated based on the implementation

3. **Update todo.md - Remove Completed Items**:
   - File: `thoughts/shared/project/todo.md`
   - Actions:
     - Find items in Must Haves or Should Haves that were completed
     - Note their full description, category, and any notes
     - Prepare to move them to done.md (next step)
     - Remove `[BLOCKED]` prefix from any items that were unblocked
     - Add new work items discovered during implementation
     - Reorder items if dependencies or priorities changed
   - Example removal from todo.md:
     ```markdown
     ## Must Haves

     ### Features
     - [x] User authentication with OAuth2 ← REMOVE THIS, move to done.md
     - [ ] Product catalog with search
     ```

4. **Update done.md - Add Completed Work**:
   - File: `thoughts/shared/project/done.md`
   - Actions:
     - Add new month/year section if it doesn't exist (e.g., `## 2025-10 (October 2025)`)
     - Add completed items from todo.md with full traceability
     - Include completion date, plan reference, ADRs, PR links, outcomes
   - Example addition to done.md:
     ```markdown
     ## 2025-10 (October 2025)

     ### Features
     - [x] User authentication with OAuth2 (2025-10-20)
       - Plan: `thoughts/shared/plans/2025-10-15-oauth-support.md`
       - Research: `thoughts/shared/research/2025-10-14-auth-libraries.md`
       - ADR: `thoughts/shared/adrs/001-oauth-provider-choice.md`
       - PR: #123
       - Notes: Implemented OAuth2 with Google and GitHub providers. Initial implementation used Passport.js but switched to @auth/core after performance testing (see ADR-001). Key insight: token refresh logic at `src/auth/refresh.ts:45` needs monitoring in production.
     ```

5. **Update project.md - Architecture & Stack Changes**:
   - File: `thoughts/shared/project/project.md`
   - Updates only if there were significant changes:
     - Update Technical Stack section if new dependencies added
     - Update Architecture Overview if system design changed
     - Update Key Constraints if new constraints discovered
     - Update "Out of Scope" if scope decisions were made
   - Example addition:
     ```markdown
     ## Technical Stack

     **Backend**:
     - Framework: FastAPI
     - Language: Python 3.11
     - Database: PostgreSQL
     - Authentication: OAuth2 via @auth/core ← ADDED

     ## Architecture Overview

     Added authentication layer between API gateway and backend services.
     OAuth2 tokens validated at gateway, user context propagated via headers.
     See ADR-001 for decision rationale.
     ```

6. **Track updates in rationalization doc**:
   - Mark each project doc update as completed in the rationalization working document
   - Note what was changed and why

### Step 9: Final Review & Cleanup

1. **Present summary of changes made**:
   ```
   Rationalization Complete!

   ## Updates Made:

   ### ADRs Created:
   - ADR-001: [Title] at thoughts/shared/adrs/001-title.md
   - ADR-002: [Title] at thoughts/shared/adrs/002-title.md

   ### Plan Updated:
   - Updated Phase 2 to reflect actual database approach
   - Added Phase 2.5 for data migration
   - Updated success criteria

   ### CLAUDE.md Updated:
   - Added pattern for async validation
   - Updated testing requirements
   - Added common pitfall about race conditions

   ### Project Documentation Updated:
   - todo.md: Moved 3 completed items to done.md, added 2 new technical debt items
   - done.md: Added OAuth2 authentication with full traceability (plan, research, ADRs, PR)
   - project.md: Updated technical stack to include @auth/core

   ## Next Step: Cleanup

   The rationalization working document can now be deleted:
   - thoughts/shared/rationalization/YYYY-MM-DD-topic.md

   All permanent knowledge has been captured in:
   - Updated plan (shows final approach as if always intended)
   - ADRs (permanent record of decisions)
   - CLAUDE.md (patterns and conventions)

   Should I delete the rationalization working document now?
   ```

2. **If user approves, delete the rationalization document**:
   ```bash
   rm thoughts/shared/rationalization/YYYY-MM-DD-topic.md
   ```

3. **Remove rationalization note from plan**:
   - Edit the plan to remove the "Rationalization in Progress" note added in Step 6

4. **Final confirmation**:
   ```
   ✓ Rationalization complete
   ✓ Working document deleted
   ✓ Plan updated to show final approach
   ✓ [N] ADRs created
   ✓ CLAUDE.md updated with [N] patterns/conventions
   ✓ Project documentation updated ([N] files)

   Your implementation is now properly documented with a clean, rational narrative.
   Next Claude Code sessions will benefit from this rationalized knowledge.

   Recommended next step: /describe_pr to create PR description
   ```

## Important Guidelines

### Be Investigative
- Look for evidence in code, git history, tests, and comments
- Consider constraints that might not be obvious
- Check commit messages for context on changes
- Review test files to understand intent

### Distinguish Facts from Inferences
- **Facts**: "The code does X at file.py:123"
- **Inferences**: "This approach was likely chosen because Y"
- **Unknown**: "Would need to verify if Z was considered"
- Mark inferences clearly when rationale isn't documented

### Be Thorough But Focused
- Read all relevant code completely
- Check git history for significant commits
- Look for patterns across the codebase
- Focus on significant decisions, not every small choice

### Interactive Collaboration
- Don't make all updates automatically
- Ask user which changes to make
- Present options for ADRs, CLAUDE.md updates, plan changes
- Get approval before creating documents

### Preserve Clean Narratives
- Plans should show the elegant solution, not the messy path
- ADRs document the reasoning and alternatives
- CLAUDE.md captures reusable patterns
- Rejected alternatives prevent re-exploration

### Document Metadata
- Always use spec_metadata.sh for metadata
- Include parentfile-id linking to plan
- Track git commit range for implementation
- Use consistent YAML frontmatter

## Working Document is Ephemeral

**CRITICAL**: The rationalization document in `thoughts/shared/rationalization/` is a **working document only**.

- It helps organize thoughts during rationalization
- It structures the investigation and review process
- It is **deleted** when rationalization is complete
- It is **never committed** to version control
- It is **never referenced** in other documents

The permanent outputs are:
1. **Updated plan** - Shows final approach as if always intended
2. **ADRs** - Permanent record of decisions with rationale
3. **Updated CLAUDE.md** - Patterns and conventions for future work
4. **Updated project documentation** - project.md, todo.md, done.md kept in sync

## Integration with Workflow

The complete workflow is:

```
1. /research_codebase → thoughts/shared/research/YYYY-MM-DD-topic.md
2. /create_plan → thoughts/shared/plans/YYYY-MM-DD-feature.md
3. /implement_plan → Code changes + updated plan checkboxes
4. /validate_plan → Verification of correctness
5. /rationalize → Update plan + create ADRs + update CLAUDE.md + update project docs
6. /commit → Create git commits
7. /describe_pr → Create PR description
```

Rationalization is **mandatory** - it ensures documentation stays current and future AI sessions have proper context.

## Output Locations

- **Working doc** (temporary): `thoughts/shared/rationalization/YYYY-MM-DD-topic.md`
- **ADRs** (permanent): `thoughts/shared/adrs/NNN-decision-title.md`
- **Updated plan** (permanent): `thoughts/shared/plans/YYYY-MM-DD-feature.md`
- **Updated CLAUDE.md** (permanent): `CLAUDE.md`
- **Updated project docs** (permanent): `thoughts/shared/project/*.md` (project.md, todo.md, done.md)

## Success Criteria

A rationalization is complete when:
- [ ] All significant decisions have ADRs or are documented in CLAUDE.md
- [ ] Plan reflects final implementation as if it was always the approach
- [ ] Rejected alternatives are documented (in ADRs)
- [ ] New patterns/conventions are in CLAUDE.md
- [ ] Project documentation updated (todo.md items moved to done.md with full traceability, project.md updated if needed)
- [ ] Working rationalization document is deleted
- [ ] User confirms documentation accurately reflects implementation
