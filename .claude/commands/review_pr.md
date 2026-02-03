# PR Review

You are the orchestrator for a comprehensive PR review. You will spawn 4 focused agents in parallel, each handling a specific aspect of the review, then consolidate their findings.

## Why Multiple Agents?

A single-pass review tries to do too much at once, leading to shallow analysis. By splitting into focused agents:
- **Code Quality agent** (opus): Does meticulous line-by-line analysis
- **Security agent**: Applies security rules without distraction
- **Best Practices agent**: Checks project-specific patterns
- **Test Coverage agent**: Focuses on test adequacy

## Step 1: Gather Context

First, collect the information you'll pass to agents:

1. **Get the PR diff**:
   ```bash
   gh pr diff {number}
   ```

2. **List changed files** from the PR context provided

3. **Identify languages** in changed files (Python, TypeScript, Go, etc.)

## Step 2: Launch 4 Agents in Parallel

Use the Task tool to launch ALL 4 agents in a SINGLE message (parallel execution):

### Agent 1: Code Quality (pr-code-quality)

```
subagent_type: pr-code-quality
prompt: |
  Review this PR for code quality issues.

  ## PR Info
  - PR Number: #{number}
  - Changed Files: [list]

  ## PR Diff
  [paste the diff]

  Follow your instructions: read the codebase index first, then go line-by-line through each function using your checklist.
```

### Agent 2: Security (pr-security)

```
subagent_type: pr-security
prompt: |
  Review this PR for security vulnerabilities.

  ## PR Info
  - PR Number: #{number}
  - Changed Files: [list]
  - Languages: [detected languages]
  - Security Areas: [based on what the code does: input handling, auth, data, files, etc.]

  ## PR Diff
  [paste the diff]

  Follow your instructions: read the codebase index first, then apply relevant security rules.
```

### Agent 3: Best Practices (pr-best-practices)

```
subagent_type: pr-best-practices
prompt: |
  Review this PR for best practices compliance.

  ## PR Info
  - PR Number: #{number}
  - Changed Files: [list]

  ## PR Diff
  [paste the diff]

  Follow your instructions: read the codebase index first, then check against best practices.
```

### Agent 4: Test Coverage (pr-test-coverage)

```
subagent_type: pr-test-coverage
prompt: |
  Review this PR for test coverage.

  ## PR Info
  - PR Number: #{number}
  - Changed Files: [list]
  - Test Files: [list any test files in the diff or related to changed files]

  ## PR Diff
  [paste the diff]

  Follow your instructions: read the codebase index first, then check test coverage.
```

## Step 3: Wait for Results

All 4 agents will run in parallel. Wait for all to complete.

## Step 4: Consolidate Findings

Combine the agent outputs into a unified report:

```markdown
# PR Review: #{number} - {title}

**Author**: {author}
**Branch**: {head} → {base}
**Files Changed**: {count}

---

## Summary

[2-3 sentence overall assessment based on all agent findings]

**Recommendation**: [Approve / Request Changes / Comment]

---

## Critical Issues (MUST FIX)

[Combine CRITICAL findings from all agents - these block merge]

### From Code Quality Review
[Critical issues from pr-code-quality agent]

### From Security Review
[Critical vulnerabilities from pr-security agent]

---

## High Priority Issues

### Code Quality
[High severity code issues]

### Security
[High severity security issues]

### Best Practices
[Pattern violations]

### Test Coverage
[Missing critical tests]

---

## Medium/Low Priority

### Improvements
[Non-blocking suggestions from all agents]

### Test Suggestions
[Nice-to-have test additions]

---

## Well Done

[Positive findings from agents - acknowledge good work]

---

## Agent Reports

<details>
<summary>Full Code Quality Report</summary>

[Paste full output from pr-code-quality agent]

</details>

<details>
<summary>Full Security Report</summary>

[Paste full output from pr-security agent]

</details>

<details>
<summary>Full Best Practices Report</summary>

[Paste full output from pr-best-practices agent]

</details>

<details>
<summary>Full Test Coverage Report</summary>

[Paste full output from pr-test-coverage agent]

</details>
```

## Step 5: Interactive Discussion

After presenting the consolidated report:

1. **Answer questions**: User may want details on specific findings
2. **Deep-dive**: Offer to investigate specific issues further
3. **Discuss fixes**: Help evaluate approaches to fixing issues
4. **Re-run agents**: If user provides context that changes assessment

## Step 6: Save Review (Optional)

At the end, ask:

> "Would you like me to save this review? I'll save it to `memories/shared/reviews/pr-review-YYYY-MM-DD-PR-{number}.md`"

If confirmed:
1. Run `.claude/helpers/spec_metadata.sh` for metadata
2. Use `memories/templates/pr_review.md.template`
3. Fill in all sections from the consolidated report
4. Save the file

## Remember

- **Launch all 4 agents in ONE message** (parallel, not sequential)
- **Each agent has narrow focus** - don't ask them to do other agents' work
- **Consolidate thoughtfully** - prioritize by severity across all findings
- **Acknowledge good work** - don't only report problems
- **Be interactive** - engage with user after presenting report
