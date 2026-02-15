   # Cleanup Implementation

You are tasked with cleaning up after a completed implementation by analyzing what actually happened and creating documentation for significant decisions.

This implements the "Review & Rationalization Phase" from the blog post "Faking a Rational Design Process in the AI Era", completing the Research → Plan → Implement → Cleanup workflow.

## Philosophy

From Parnas and Clements (1986): Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process. This doesn't mean lying—it means presenting the refined, polished version of our work.

<!-- Origin: D.L. Parnas & P.C. Clements, "A rational design process: How and why to fake it", IEEE TSE, Feb 1986. https://users.ece.utexas.edu/~perry/education/SE-Intro/fakeit.pdf -->

**What cleanup does:**
- Captures what was tried (rejected alternatives in decisions.md)
- Captures implementation learnings via reflection into decisions.md
- Learns from the process (updates to CLAUDE.md)
- Keeps project documentation in sync (project.md, todo.md, done.md, decisions.md)
- Updates documentation to reflect the final state of the codebase

## Initial Response

When this command is invoked:

1. **Check if parameters were provided**:
   - If files provided: skip intro, read the files immediately, begin cleanup
   - If not provided: show the helpful message below

2. **If no parameters provided**, respond with:
```
I'll help you clean up after your implementation and update documentation.

Please provide the file paths:
- Plan file (required): e.g., `memories/shared/plans/2025-10-18-feature.md`
- Research file (optional): e.g., `memories/shared/research/2025-10-18-topic.md`
- Review file (optional): e.g., `memories/shared/reviews/2025-10-18-review.md`

I'll analyze what changed, document best practices, and update documentation.

Tip: Quick invoke with all files:
`/cleanup memories/shared/plans/2025-10-18-feature.md memories/shared/research/2025-10-18-topic.md memories/shared/reviews/2025-10-18-review.md`
```

Then wait for the user's input.

## Process Steps

### Step 1: Gather Context

1. **Read all provided files FULLY**:
   - **Plan file** (required): Use Read tool WITHOUT limit/offset parameters
   - **Research file** (if provided): Read the entire research document
   - **Review file** (if provided): Read the entire review document

2. **Check for uncommitted changes**:
   ```bash
   # Check git status for uncommitted changes
   git status --porcelain

   # See what uncommitted changes exist
   git diff HEAD

   # Check staged changes
   git diff --cached
   ```
   **IMPORTANT**: Uncommitted changes are part of the implementation and must be included in the analysis, documentation, and best practices.

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

4. **Read key changed files**:
   - Read 8-10 most important changed files FULLY (from git diff)
   - Include files with uncommitted changes (from git status)
   - Compare current state to what plan described
   - Note differences

5. **Create cleanup todo list**:
   - Use TodoWrite to track cleanup tasks
   - Include: investigation, best practices documentation, CLAUDE.md updates, project doc updates

### Step 2: Rationalize — What Actually Happened?

This step implements the "Faking a Rational Design Process" approach: compare what was planned vs what was actually built, capture the messy reality (rejected alternatives, discoveries, pivots), and present the refined version for future reference.

You already have the context from reading plan, research, and review files and git history in Step 1.

1. **Compare plan vs reality** (based on plan, research, review, and git diff):
   - Where did implementation deviate from the plan? Why?
   - What discoveries changed the approach mid-implementation?
   - What alternatives were tried and rejected? What failed and why?

2. **Identify what's worth preserving** (max 5 items):
   - Key technical decisions with rationale (what was chosen, what was rejected, why)
   - Patterns or conventions that emerged during implementation
   - Lessons learned about architecture, design, testing, or deployment
   - Dead ends — approaches that don't work for this codebase (prevents re-exploration)

### Step 3: Rewrite Documentation to Reflect Final State

Update all project documentation so it reads as if the current code was always the intended outcome. No "we changed X because the plan said Y" — just describe what the code does and why.

**This applies to ALL text — both existing and newly written.** New text introduced by this implementation is just as likely to contain "trail of changes" language (e.g., "this replaces the old X", "previously we used Y", "unlike the former approach"). Scan every line you've added or modified with the same critical eye.

1. **Code comments**: Review comments in changed files — both pre-existing and newly added. They should explain the *purpose* of the code, not the history of changes. Remove any comments that reference the implementation journey or contrast with a previous approach (e.g., "changed from X to Y", "originally this was...", "this replaces the old...", "unlike the previous version..."). Comments should answer "why does this code exist?" not "how is this different from before?".

2. **README.md**: Update if the implementation changed user-facing behavior, installation steps, configuration, or API usage. Describe the current state as the intended design.

3. **CLAUDE.md**: Update architecture sections, conventions, and patterns to match the final implementation. If a pattern was added or changed, document it as established practice — not as a recent change.

4. **Other project docs** (e.g., API docs, configuration docs): Rewrite any sections affected by the implementation to describe the current state cleanly.

5. **Newly written documentation and instructions**: Re-read all text you wrote or modified during this implementation. Look for phrases that explain the current design by contrasting it with what came before — these are trail-of-changes violations even though you just wrote them. Rewrite to describe the current state on its own terms.

**The rule**: A reader encountering any documentation for the first time should see a coherent, intentional design — not a trail of changes. This rule applies equally to text you just wrote — freshly written text that says "this replaces X" is still a trail of changes.

### Step 4: Capture Learnings in decisions.md

Knowledge capture from implementation is handled by `decisions.md` — the project's living technical memory. Micro-reflections during work and periodic consolidation keep it current with low overhead.

**When running inside the sprint runner**: Micro-reflections and consolidation already handle this automatically. Skip this step.

**When running standalone (outside sprint runner)**: Run the reflection and consolidation commands to capture learnings:

1. **Reflect**: Run `/reflect <plan-path> [research-path] [review-path]` to capture raw observations into `memories/shared/project/scratchpad.md`
2. **Consolidate**: Run `/consolidate_memory` to integrate scratchpad observations into `memories/shared/project/decisions.md`

If `decisions.md` doesn't exist yet, create it from the template at `memories/templates/decisions.md.template`.

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
   find memories/shared/project -type f -name "*.md" 2>/dev/null
   ```

2. **Read relevant files**:
   - Read FULLY without limit/offset parameters
   - Identify what needs to be updated based on the implementation
   - Include `decisions.md` — check if any entries need updating based on the implementation

3. **Update todo.md - Remove Completed Items**:
   - File: `memories/shared/project/todo.md`
   - Actions:
     - Find items in Must Haves or Should Haves that were completed
     - Note their full description, category, and any notes
     - Prepare to move them to done.md (next step)
     - Remove `[BLOCKED]` prefix from any items that were unblocked
     - Add new work items discovered during implementation
     - Reorder items if dependencies or priorities changed

4. **Update done.md - Add Completed Work**:
   - File: `memories/shared/project/done.md`
   - Actions:
     - Add new month/year section if it doesn't exist (e.g., `## 2025-10 (October 2025)`)
     - Add completed items from todo.md with full traceability
     - Include completion date, best practices references, PR links, outcomes
   - Example addition to done.md:
     ```markdown
     ## 2025-10 (October 2025)

     ### Features
     - [x] User authentication with OAuth2 (2025-10-20)
       - Decisions: Updated in `memories/shared/project/decisions.md`
       - PR: #123
       - Notes: Implemented OAuth2 with Google and GitHub providers. Documented token refresh patterns and error handling. Key insight: token refresh logic at `src/auth/refresh.ts:45` needs monitoring in production.
     ```

5. **Update project.md - Architecture & Stack Changes**:
   - File: `memories/shared/project/project.md`
   - Updates only if there were significant changes:
     - Update Technical Stack section if new dependencies added
     - Update Architecture Overview if system design changed
     - Update Key Constraints if new constraints discovered
     - Update "Out of Scope" if scope decisions were made

6. **Update Readme.md if needed**:
   - File: `README.md` at project root
   - Update installation instructions, usage examples, or feature lists
   - Only if there were significant changes affecting users or developers


### Step 7: Summary

Present a short summary of what was done:

```
✓ Cleanup Complete

## Learnings Captured:
- decisions.md: [Updated via /reflect + /consolidate_memory, or already handled by sprint runner]

## Documentation Updated:
- CLAUDE.md: [N] patterns/conventions added
- todo.md: [N] completed items moved to done.md
- done.md: [N] items added with full traceability
- decisions.md: [Updated with implementation learnings]
- project.md: [Updated if architecture/stack changed]
- README.md: [Updated if user-facing changes]

Your implementation is now properly documented with clean, permanent knowledge.

Recommended next step: /pr to create PR description
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
- Track git commit range for implementation
- **Document uncommitted changes** - note what's committed vs uncommitted
- Use consistent YAML frontmatter

## Integration with Workflow

The complete workflow is:

```
1. /research_codebase → memories/shared/research/YYYY-MM-DD-topic.md
2. /create_plan → memories/shared/plans/YYYY-MM-DD-feature.md
3. /implement_plan → Code changes + commits + automated review
4. /cleanup <plan> <research> <review> → Document best practices + update CLAUDE.md + update project docs + commit + PR
```

Cleanup is **mandatory** - it ensures documentation stays current and future AI sessions have proper context.

## Output Locations
- **Learnings**: `memories/shared/project/decisions.md` (via `/reflect` + `/consolidate_memory`)
- **Updated CLAUDE.md**: `CLAUDE.md`
- **Updated project docs**: `memories/shared/project/*.md` (project.md, todo.md, done.md, decisions.md)


## Success Criteria

A cleanup is complete when:
- [ ] Implementation learnings captured in decisions.md (via /reflect + /consolidate_memory)
- [ ] New patterns/conventions are in CLAUDE.md
- [ ] Project documentation updated (todo.md items moved to done.md with full traceability, project.md updated if needed, decisions.md updated)
- [ ] README.md updated if needed (user-facing changes)

