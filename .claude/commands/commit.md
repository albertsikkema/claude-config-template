# Commit Changes

You are tasked with creating git commits for the changes made during this session.

## Optional Arguments

- **Plan Path**: If provided, read the plan to understand what was implemented. Use this context to write better commit messages, but do NOT reference the plan file itself (it will be deleted after this task).

## Commit Message Format

Follow the Conventional Commits specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Purpose |
|------|---------|
| `feat` | Adds a new feature |
| `fix` | Fixes a bug |
| `refactor` | Restructures code without changing behavior |
| `docs` | Documentation changes (README, comments, etc.) |
| `style` | Formatting changes (whitespace, semicolons, etc.) |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks (dependencies, config, .gitignore) |
| `perf` | Performance improvements |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `revert` | Reverts a previous commit |

### Rules for Great Commit Messages

1. **Limit subject line to 50 characters**
2. **Capitalize the subject line** - e.g., "Add feature" not "add feature"
3. **No period at the end of the subject line**
4. **Use imperative mood** - "Add feature" not "Added feature" or "Adds feature"
5. **Separate subject from body with a blank line**
6. **Wrap body at 72 characters**
7. **Use body to explain what and why, not how**

### Examples

Good:
```
feat(auth): Add password reset functionality

Users can now reset their password via email link.
This addresses user feedback about account recovery.
```

```
fix: Resolve race condition in order processing

The previous implementation could process the same
order twice under high load conditions.

Fixes #234
```

Bad:
- "Tweaked a few things" (vague)
- "fixed bug" (no type, no description)
- "Added the new feature that allows users to do the thing" (too long)

## Process

1. **Understand the context:**
   - If a plan path was provided, read it to understand the implementation goals
   - Run `git status` to see current changes
   - Run `git diff` to understand the modifications
   - Consider whether changes should be one commit or multiple logical commits

2. **Plan your commit(s):**
   - Group related files together
   - Draft messages following the format above
   - Each commit should be atomic (one logical change)

3. **Present and get approval:**
   - Show a brief summary: files to commit and commit message(s)
   - Ask: "Ready to commit? (y/n)"
   - **NEVER commit without explicit user approval**
   - Wait for user to confirm before proceeding

4. **Execute after approval:**
   - Use `git add` with specific files (never use `-A` or `.`)
   - Create commits with your planned messages
   - Show the result with `git log --oneline -n [number]`

5. **Handle failures:**
   - If a commit fails (pre-commit hooks, conflicts, etc.):
     - Analyze what went wrong
     - Fix the issue if possible
     - Present a NEW commit plan
     - Ask for approval again before retrying
   - Never retry commits automatically without user approval

## Important

- **NEVER commit without user approval**
- **NEVER add co-author information or Claude attribution**
- Commits should be authored solely by the user
- Do not include any "Generated with Claude" messages
- Do not add "Co-Authored-By" lines
- Write commit messages as if the user wrote them

## Remember

- Use the plan to understand the purpose and scope of changes
- Group related changes together
- Keep commits focused and atomic
- The user trusts your judgment but must approve before execution
