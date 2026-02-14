   # Cleanup Implementation

You are tasked with cleaning up after a completed implementation by analyzing what actually happened and creating documentation for significant decisions.

This implements the "Review & Rationalization Phase" from the blog post "Faking a Rational Design Process in the AI Era", completing the Research → Plan → Implement → Cleanup workflow.

## Philosophy

From Parnas and Clements (1986): Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process. This doesn't mean lying—it means presenting the refined, polished version of our work.

**What cleanup does:**
- Captures what was tried (rejected alternatives in best practices)
- Documents best practices discovered during implementation, so we can learn and improve in the future
- Learns from the process (updates to CLAUDE.md)
- Keeps project documentation in sync (project.md, todo.md, done.md)
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

1. **Code comments**: Review comments in changed files. They should explain the *purpose* of the code, not the history of changes. Remove any comments that reference the implementation journey (e.g., "changed from X to Y", "originally this was..."). Comments should answer "why does this code exist?" not "why was this changed?".

2. **README.md**: Update if the implementation changed user-facing behavior, installation steps, configuration, or API usage. Describe the current state as the intended design.

3. **CLAUDE.md**: Update architecture sections, conventions, and patterns to match the final implementation. If a pattern was added or changed, document it as established practice — not as a recent change.

4. **Other project docs** (e.g., API docs, configuration docs): Rewrite any sections affected by the implementation to describe the current state cleanly.

**The rule**: A reader encountering any documentation for the first time should see a coherent, intentional design — not a trail of changes.

### Step 4: Document Best Practices (HIGH THRESHOLD)

**CRITICAL**: Most things you learned are NOT best practices. Be very selective.

**1. Filter out non-novel patterns first:**

Before documenting anything, check if it's already known:

```bash
# Search existing best practices
grep -r -i "[pattern-name]" memories/best_practices/ 2>/dev/null

# Search technical docs
grep -r -i "[pattern-name]" memories/technical_docs/ 2>/dev/null
```

**If you find anything** check if this pattern is already documented:   
- If yes → Skip documenting, just reference existing docs
- If no → Continue to qualification check

**2. Qualify: Does this meet the threshold?**

A practice is ONLY worth documenting if it meets **at least 2** of these criteria:

✅ **Novel for this project** - First time we've done this pattern here
✅ **Non-obvious** - Wouldn't be found in standard documentation
✅ **Project-specific decision** - Tailored to our architecture/constraints
✅ **Rejected alternatives** - We tried other approaches that failed
✅ **Trade-offs made** - Significant benefits vs costs to document
✅ **Counter-intuitive** - Goes against common wisdom for good reason

**NOT best practices:**
❌ Applying code review feedback (that's normal iteration)
❌ Standard industry patterns (REST endpoints, error handling basics)
❌ Minor test improvements (adding validation is expected)
❌ Following existing conventions (that's just consistency)
❌ Obvious improvements (better variable names, etc.)

**3. Examples of what QUALIFIES:**

✅ **"Fire-and-Forget API Pattern for Claude Integration"**
- Novel: First time integrating background Claude execution
- Non-obvious: Specific threading + event loop pattern
- Rejected alternatives: Tried database tracking, too heavy
- Trade-offs: Can't track progress, but much simpler

✅ **"Defense-in-Depth Validation for Path Inputs"**
- Project-specific: Multiple validation layers for our security model
- Rejected alternatives: Single validation failed in production
- Trade-offs: More code, but prevents entire class of vulnerabilities

❌ **"Version Endpoint Pattern"**
- Standard: Every API has version endpoints
- Obvious: Read from pyproject.toml is common
- No alternatives: This is the default approach

❌ **"Improved Exception Handling"**
- Standard: Using specific exceptions is basic Python
- Normal iteration: Code review feedback isn't a pattern

**4. For qualified patterns only:**

Read existing best practices to avoid duplication:
```bash
ls -la memories/best_practices/*.md 2>/dev/null
```
- Avoid duplicating content that already exists
- Consider updating existing files if related

**5. Determine filename and category** (for qualified patterns only):
   - Use descriptive, topic-based names: `[category]-[topic].md`
   - Examples of GOOD best practice names:
     - `api-fire-and-forget-claude-integration.md` (novel pattern)
     - `security-defense-in-depth-validation.md` (project-specific)
     - `error-handling-batch-operations.md` (rejected alternatives documented)
   - NOT:
     - `api-error-handling.md` (too generic, already documented)
     - `testing-validation.md` (too standard)

**6. Create best practice file** at `memories/best_practices/[category]-[topic].md`:

Use the template from `memories/templates/best-practice.md`

**IMPORTANT**:
- Document WHY this is special/different for this project
- Document what alternatives were tried and failed
- Keep it SHORT but substantive

**7. Final check before creating file:**

Ask yourself:
- "Would a competent developer find this in standard docs?" → If yes, DON'T document
- "Is this specific to our codebase's unique constraints?" → If no, DON'T document
- "Did we make a non-obvious decision here?" → If no, DON'T document

**If still yes to documenting**, ensure directory exists:
```bash
mkdir -p memories/best_practices
```

**Expected result**: Most cleanups should create 0-2 best practices, not 5-10.

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
       - Best Practices: `memories/best_practices/authentication-oauth-patterns.md`
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

## Documentation Created:
- [N] Best Practices in memories/best_practices/
  - [category]-[topic].md: [Best Practice Title]
  - [category]-[topic].md: [Another Best Practice]

## Documentation Updated:
- CLAUDE.md: [N] patterns/conventions added
- todo.md: [N] completed items moved to done.md
- done.md: [N] items added with full traceability
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
- **Best Practices**: `memories/best_practices/[category]-[topic].md`
- **Updated CLAUDE.md**: `CLAUDE.md`
- **Updated project docs**: `memories/shared/project/*.md` (project.md, todo.md, done.md)


## Success Criteria

A cleanup is complete when:
- [ ] All significant decisions and best practices are documented in memories/best_practices/
- [ ] New patterns/conventions are in CLAUDE.md
- [ ] Project documentation updated (todo.md items moved to done.md with full traceability, project.md updated if needed)
- [ ] README.md updated if needed (user-facing changes)

