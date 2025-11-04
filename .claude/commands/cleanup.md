# Cleanup Implementation

You are tasked with cleaning up after a completed implementation by analyzing what actually happened, creating documentation for significant decisions, and removing ephemeral artifacts.

This implements the "Review & Rationalization Phase" from the blog post "Faking a Rational Design Process in the AI Era", completing the Research → Plan → Implement → Cleanup workflow.

## Philosophy

From Parnas and Clements (1986): Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process. This doesn't mean lying—it means presenting the refined, polished version of our work.

**What cleanup does:**
- Captures what was tried (rejected alternatives in best practices)
- Documents best practices discovered during implementation
- Learns from the process (updates to CLAUDE.md)
- Keeps project documentation in sync (project.md, todo.md, done.md)
- Removes ephemeral artifacts (plans, research docs)

## Initial Response

When this command is invoked:

1. **Check if a plan file was provided as parameter**:
   - If provided: skip intro, read the plan file immediately, begin cleanup
   - If not provided: show the helpful message below

2. **If no parameter provided**, respond with:
```
I'll help you clean up after your implementation and update documentation.

Please provide the implementation plan you want to clean up:
- Plan file path: e.g., `thoughts/shared/plans/2025-10-18-feature.md`

I'll analyze what changed, document best practices, update documentation, and remove ephemeral artifacts.

Tip: Quick invoke with: `/cleanup thoughts/shared/plans/2025-10-18-feature.md`
```

Then wait for the user's input.

## Process Steps

### Step 1: Gather Context

1. **Read the implementation plan FULLY**:
   - Use Read tool WITHOUT limit/offset parameters
   - Read the entire plan in main context
   - Extract frontmatter metadata, especially:
     - `file-id`: Plan's unique ID
     - `parentfile-id`: Research document that preceded this plan
     - Plan creation date and commit

2. **Check for uncommitted changes**:
   ```bash
   # Check git status for uncommitted changes
   git status --porcelain

   # See what uncommitted changes exist
   git diff HEAD

   # Check staged changes
   git diff --cached
   ```
   **IMPORTANT**: Uncommitted changes are part of the implementation and must be included in the analysis

3. **Analyze git history since plan creation (including uncommitted)**:
   ```bash
   # Find commits since plan was created
   git log --since="[plan date]" --oneline --no-merges

   # See what files changed (committed)
   git diff [plan-commit]..HEAD --stat

   # Get detailed diff for analysis (committed)
   git diff [plan-commit]..HEAD

   # Include uncommitted changes in analysis
   git diff HEAD --stat
   git diff HEAD
   ```
   **Scope**: The full implementation includes both committed AND uncommitted changes

4. **Read all files mentioned in the plan PLUS uncommitted files**:
   - Read FULLY without limit/offset
   - Include files with uncommitted changes (from git status)
   - Compare current state to what plan described
   - Note differences

5. **Create cleanup todo list**:
   - Use TodoWrite to track cleanup tasks
   - Include: investigation, best practices documentation, CLAUDE.md updates, project doc updates, artifact deletion

### Step 2: Investigation - What Actually Happened?

Spawn parallel research agents to discover implementation reality:

**CRITICAL**: All agents must analyze both committed AND uncommitted changes. The implementation scope includes all changes since the plan was created, regardless of commit status.

1. **Implementation Analysis** (codebase-analyzer):
   - Analyze the implemented code (including uncommitted changes)
   - How does it work now?
   - What's different from what the plan described?
   - Include analysis of files with uncommitted changes
   - Provide specific file:line references for all findings
   - Note which changes are committed vs uncommitted

2. **Pattern Discovery** (codebase-pattern-finder):
   - What patterns emerged from implementation?
   - Include patterns in uncommitted code
   - Are there similar features to compare?
   - What conventions were established or followed?

3. **Historical Context** (thoughts-analyzer):
   - Check for related research documents
   - Look for related plans or earlier decisions
   - Find any existing best practices that relate

4. **Project Documentation Review** (project-context-analyzer):
   - Read current CLAUDE.md
   - Review existing best practices in thoughts/best_practices/
   - Check project documentation for relevant sections
   - Review thoughts/shared/project/project.md for context
   - Check thoughts/shared/project/todo.md for current/planned work
   - Review thoughts/shared/project/done.md for completed work

**IMPORTANT**:
- Wait for ALL sub-agents to complete before proceeding
- Ensure agents have access to uncommitted changes via git diff HEAD output

### Step 3: Create Working Rationalization Document

This is a **temporary working document** that will be deleted when cleanup is complete.

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
**Uncommitted Changes**: [Yes/No - if yes, note what's uncommitted]

> **NOTE**: This is a working document for the rationalization process.
> It will be DELETED when rationalization is complete.
> Permanent outputs: Best practices docs, CLAUDE.md updates, project doc updates.

## Summary
[What was implemented and how it evolved from the plan. Include both committed and uncommitted changes.]

## Implementation Evolution

### Original Plan Approach
[Summary of what the plan described - quote relevant sections]

### What Actually Happened
[Summary of final implementation with file:line references. Include both committed and uncommitted changes. Note which changes are committed vs uncommitted.]

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
   - **Document as best practice?**: Yes/No - [If yes, note topic/category]

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

### Best Practices to Document
List best practices discovered during implementation:

- [ ] [Category]: [Best practice name] - [Brief description]
- [ ] [Category]: [Another best practice] - [Brief description]

### CLAUDE.md Updates
What should be added to project documentation:

- [ ] Add pattern: [Pattern name] to [section of CLAUDE.md]
- [ ] Update [section]: [what to change]
- [ ] Add to "Common Pitfalls": [lesson learned]
- [ ] Update [section]: [convention established]

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
- [ ] Link to best practices documented during cleanup
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
```

### Step 4: Document Best Practices

For each best practice discovered during implementation (including those in uncommitted code):

1. **Read existing best practices**:
   - Check `thoughts/best_practices/` directory for existing files
   ```bash
   # List all existing best practices
   ls -la thoughts/best_practices/*.md 2>/dev/null
   ```
   - Read relevant existing files to understand what's already documented
   - Avoid duplicating content that already exists
   - Consider updating existing files if the new practice is related

2. **Determine filename and category**:
   - Use descriptive, topic-based names: `[category]-[topic].md`
   - Examples:
     - `authentication-oauth-patterns.md`
     - `database-transaction-handling.md`
     - `api-error-handling.md`
     - `testing-integration-patterns.md`
     - `caching-invalidation-strategies.md`

3. **Create best practice file** at `thoughts/best_practices/[category]-[topic].md`:

```markdown
# [Category]: [Topic]

**Date**: [YYYY-MM-DD]
**Author**: [Username from metadata]
**Related Implementation**: [Brief description or commit range]

## Overview

[Brief description of what this best practice is about and when to use it]

## The Practice

[Clear, concise description of the best practice itself]

### When to Use

- [Situation 1 where this applies]
- [Situation 2 where this applies]
- [Situation 3 where this applies]

### When NOT to Use

- [Situation where this practice doesn't apply]
- [Anti-pattern or exception case]

## Implementation

### Recommended Approach

[Step-by-step guide or code examples showing the best practice in action]

```[language]
// Code example demonstrating the best practice
[actual code from implementation with file:line references]
```

**Code References**:
- `path/to/file.ext:line` - [What's implemented there]
- `path/to/another.ext:line` - [Related implementation]

### Key Considerations

1. **[Consideration 1]**: [Explanation]
2. **[Consideration 2]**: [Explanation]
3. **[Consideration 3]**: [Explanation]

## Alternatives Tried

### Approach 1: [Alternative name]
**What we tried**: [Description]
**Why it didn't work**: [Technical reason]
**Key lesson**: [What we learned]

### Approach 2: [Another alternative]
**What we tried**: [Description]
**Why it didn't work**: [Technical reason]
**Key lesson**: [What we learned]

## Trade-offs

### Benefits

- [Benefit 1]
- [Benefit 2]
- [Benefit 3]

### Costs

- [Cost/limitation 1]
- [Cost/limitation 2]

## Common Pitfalls

1. **[Pitfall 1]**: [Description and how to avoid]
2. **[Pitfall 2]**: [Description and how to avoid]

## Related Practices

- See also: `thoughts/best_practices/[related-file].md`
- Builds on: `thoughts/best_practices/[foundational-file].md`

## Examples in Codebase

### Example 1: [Feature/Component]
**Location**: `path/to/implementation.ext:line`
**Context**: [When/why this example is relevant]

### Example 2: [Feature/Component]
**Location**: `path/to/another.ext:line`
**Context**: [When/why this example is relevant]

## Notes

[Any additional context, future considerations, or lessons learned]
```

4. **Ensure directory exists**:
   ```bash
   mkdir -p thoughts/best_practices
   ```

### Step 5: Update CLAUDE.md

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

### Step 6: Update Project Documentation

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

4. **Update done.md - Add Completed Work**:
   - File: `thoughts/shared/project/done.md`
   - Actions:
     - Add new month/year section if it doesn't exist (e.g., `## 2025-10 (October 2025)`)
     - Add completed items from todo.md with full traceability
     - Include completion date, best practices references, PR links, outcomes
   - Example addition to done.md:
     ```markdown
     ## 2025-10 (October 2025)

     ### Features
     - [x] User authentication with OAuth2 (2025-10-20)
       - Best Practices: `thoughts/best_practices/authentication-oauth-patterns.md`
       - PR: #123
       - Notes: Implemented OAuth2 with Google and GitHub providers. Documented token refresh patterns and error handling. Key insight: token refresh logic at `src/auth/refresh.ts:45` needs monitoring in production.
     ```

5. **Update project.md - Architecture & Stack Changes**:
   - File: `thoughts/shared/project/project.md`
   - Updates only if there were significant changes:
     - Update Technical Stack section if new dependencies added
     - Update Architecture Overview if system design changed
     - Update Key Constraints if new constraints discovered
     - Update "Out of Scope" if scope decisions were made

6. **Track updates in rationalization doc**:
   - Mark each project doc update as completed in the rationalization working document
   - Note what was changed and why

### Step 7: Delete Ephemeral Artifacts

1. **Find the research document**:
   - Extract `parentfile-id` from the plan's frontmatter
   - Search for research documents in `thoughts/shared/research/` with matching `file-id`
   ```bash
   # Search for research doc with matching file-id
   grep -l "file-id: [parentfile-id]" thoughts/shared/research/*.md
   ```

2. **Find related review documents**:
   - Extract the plan's `file-id` from the plan's frontmatter
   - Search for review documents that reference this plan
   - Reviews might reference the plan via `parentfile-id` or `related_plan` fields
   ```bash
   # Search for reviews with matching parentfile-id or related_plan
   grep -l "parentfile-id: [plan-file-id]\|related_plan.*YYYY-MM-DD-[topic].md" thoughts/shared/reviews/*.md 2>/dev/null

   # Also search for reviews with the same date (common pattern)
   ls thoughts/shared/reviews/*YYYY-MM-DD*.md 2>/dev/null
   ```

3. **Delete the plan file**:
   ```bash
   rm thoughts/shared/plans/YYYY-MM-DD-[topic].md
   ```

4. **Delete the research document** (if found):
   ```bash
   rm thoughts/shared/research/YYYY-MM-DD-[topic].md
   ```

5. **Delete related review documents** (if found):
   ```bash
   rm thoughts/shared/reviews/[review-filename].md
   ```
   Note: Delete all reviews that reference the plan or share the same date/topic

6. **Delete the rationalization working document**:
   ```bash
   rm thoughts/shared/rationalization/YYYY-MM-DD-[topic].md
   ```

### Step 8: Summary

Present a concise summary of what was done:

```
✓ Cleanup Complete

## Documentation Created:
- [N] Best Practices in thoughts/best_practices/
  - [category]-[topic].md: [Best Practice Title]
  - [category]-[topic].md: [Another Best Practice]

## Documentation Updated:
- CLAUDE.md: [N] patterns/conventions added
- todo.md: [N] completed items moved to done.md
- done.md: [N] items added with full traceability
- project.md: [Updated if architecture/stack changed]

## Artifacts Removed:
- Plan: thoughts/shared/plans/YYYY-MM-DD-[topic].md
- Research: thoughts/shared/research/YYYY-MM-DD-[topic].md
- Reviews: thoughts/shared/reviews/[N] related review(s)
- Rationalization: thoughts/shared/rationalization/YYYY-MM-DD-[topic].md

Your implementation is now properly documented with clean, permanent knowledge.
Ephemeral artifacts have been removed.

Recommended next step: /describe_pr to create PR description
```

## Important Guidelines

### Be Investigative
- Look for evidence in code, git history, tests, and comments
- **Include uncommitted changes** - they are part of the implementation
- Consider constraints that might not be obvious
- Check commit messages for context on changes
- Review test files to understand intent
- Always check `git status` and `git diff HEAD` for uncommitted work

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

### Preserve Clean Narratives
- Best practices document the reasoning and alternatives
- CLAUDE.md captures reusable patterns
- Rejected alternatives prevent re-exploration
- Project documentation stays in sync

### Document Metadata
- Always use spec_metadata.sh for metadata
- Include parentfile-id linking to plan
- Track git commit range for implementation
- **Document uncommitted changes** - note what's committed vs uncommitted
- Use consistent YAML frontmatter

## Working Document is Ephemeral

**CRITICAL**: The rationalization document in `thoughts/shared/rationalization/` is a **working document only**.

- It helps organize thoughts during cleanup
- It structures the investigation process
- It is **deleted** when cleanup is complete
- It is **never committed** to version control
- It is **never referenced** in other documents

The permanent outputs are:
1. **Best Practices** - Permanent record of practices, decisions, and patterns with rationale
2. **Updated CLAUDE.md** - Patterns and conventions for future work
3. **Updated project documentation** - project.md, todo.md, done.md kept in sync

The ephemeral artifacts that get deleted:
1. **Plan file** - Implementation plan (no longer needed after completion)
2. **Research document** - Research that preceded the plan (referenced by parentfile-id)
3. **Review documents** - Related reviews (security, code review, etc. that reference the plan)
4. **Rationalization document** - Working document for cleanup process

## Integration with Workflow

The complete workflow is:

```
1. /research_codebase → thoughts/shared/research/YYYY-MM-DD-topic.md
2. /create_plan → thoughts/shared/plans/YYYY-MM-DD-feature.md
3. /implement_plan → Code changes + updated plan checkboxes
4. /cleanup → Document best practices + update CLAUDE.md + update project docs + delete artifacts
5. /commit → Create git commits
6. /describe_pr → Create PR description
```

Cleanup is **mandatory** - it ensures documentation stays current, ephemeral artifacts are removed, and future AI sessions have proper context.

## Output Locations

**Permanent outputs:**
- **Best Practices**: `thoughts/best_practices/[category]-[topic].md`
- **Updated CLAUDE.md**: `CLAUDE.md`
- **Updated project docs**: `thoughts/shared/project/*.md` (project.md, todo.md, done.md)

**Deleted artifacts:**
- **Plan**: `thoughts/shared/plans/YYYY-MM-DD-feature.md`
- **Research**: `thoughts/shared/research/YYYY-MM-DD-topic.md` (found via parentfile-id)
- **Reviews**: `thoughts/shared/reviews/*.md` (related reviews found via plan reference or date)
- **Working doc**: `thoughts/shared/rationalization/YYYY-MM-DD-topic.md`

## Success Criteria

A cleanup is complete when:
- [ ] All significant decisions and best practices are documented in thoughts/best_practices/
- [ ] Rejected alternatives are documented (in best practices)
- [ ] New patterns/conventions are in CLAUDE.md
- [ ] Project documentation updated (todo.md items moved to done.md with full traceability, project.md updated if needed)
- [ ] Plan file is deleted
- [ ] Research document is deleted (if parentfile-id found)
- [ ] Related review documents are deleted (if found)
- [ ] Working rationalization document is deleted
