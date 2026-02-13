# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.



## Codebase Index

**IMPORTANT**: Before searching the codebase with Grep, Glob, or Explore, first read the codebase index:

**`memories/codebase/codebase_overview_claude_helpers_py.md`**

This index contains:
- **Most Used Symbols**: Top functions/classes by usage count
- **Library Files**: All exports with descriptions and "used by" references
- **API Endpoints**: All REST API routes
- **Dependency Graph**: Which files are most imported

Reading the index first saves tokens and improves accuracy.


## Repository Purpose

This is a **configuration template repository** for Claude Code. It installs into other projects via the `install.sh` script, providing:
- 16 specialized agents for code analysis, planning, and research
- 16 slash commands for common workflows
- A `memories/` directory system for documentation and plans
- Pre-configured tool permissions

## Quick Commands

### Installation (into target projects)

```bash
# One-line remote install (most common)
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash

# From specific branch
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch <branch-name>

# Preview changes
./install-helper.sh --dry-run

# Force reinstall (removes existing memories/)
./install-helper.sh --force
```

### Orchestrator (automated workflow)

```bash
# Full automated flow (non-interactive except commit)
uv run .claude/helpers/orchestrator.py "Add user authentication"

# Plan phase only (interactive)
uv run .claude/helpers/orchestrator.py --phase plan "Add user authentication"

# Plan phase, skip query refinement
uv run .claude/helpers/orchestrator.py --phase plan --no-refine "Add user authentication"

# Implement phase (interactive review)
uv run .claude/helpers/orchestrator.py --phase implement memories/shared/plans/YYYY-MM-DD-feature.md

# Cleanup phase (interactive commit)
uv run .claude/helpers/orchestrator.py --phase cleanup memories/shared/plans/YYYY-MM-DD-feature.md
```

**Aliases (add to ~/.zshrc):**
```bash
alias orch='uv run .claude/helpers/orchestrator.py'
alias orch-plan='uv run .claude/helpers/orchestrator.py --phase plan'
alias orch-impl='uv run .claude/helpers/orchestrator.py --phase implement'
alias orch-clean='uv run .claude/helpers/orchestrator.py --phase cleanup'
```

### Ralph Orchestrator (autonomous implementation)

```bash
# Step 1: Plan (existing orchestrator, interactive)
orch --phase plan "Add user authentication"

# Step 2: Convert plan to Ralph prompt
uv run .claude/helpers/ralph_orchestrator.py --convert memories/shared/plans/2026-02-08-feature.md

# Step 3: Run Ralph loop (autonomous build → review → fix)
uv run .claude/helpers/ralph_orchestrator.py --implement memories/shared/ralph/2026-02-08-feature-prompt.md

# Step 4: Human review of output + cleanup (existing orchestrator)
orch --phase cleanup memories/shared/plans/2026-02-08-feature.md

# Or steps 2+3 combined:
uv run .claude/helpers/ralph_orchestrator.py --convert-and-implement memories/shared/plans/2026-02-08-feature.md

# With options:
uv run .claude/helpers/ralph_orchestrator.py --implement --max-iterations 20 --max-turns 30 prompt.md
uv run .claude/helpers/ralph_orchestrator.py --implement --max-review-cycles 5 prompt.md
```

**Alias (add to ~/.zshrc):**
```bash
alias orch-ralph='uv run .claude/helpers/ralph_orchestrator.py'
```

### PR Reviewer (automated PR review)

```bash
# Review PR by number
uv run .claude/helpers/pr_reviewer.py 123

# Review PR by URL
uv run .claude/helpers/pr_reviewer.py https://github.com/owner/repo/pull/123

# Skip tests (not recommended)
uv run .claude/helpers/pr_reviewer.py --skip-tests 123

# Skip documentation fetch (faster)
uv run .claude/helpers/pr_reviewer.py --skip-docs 123

# Skip codebase indexing (faster)
uv run .claude/helpers/pr_reviewer.py --skip-index 123
```

**Workflow:**
1. Validates clean git status (aborts if dirty)
2. Fetches PR details and comments via `gh` CLI
3. Checks out PR branch
4. Installs dependencies (uv sync, npm install, etc.)
5. Runs tests (aborts if tests fail)
6. Indexes codebase (`/index_codebase`)
7. Fetches technical docs for packages in changed files
8. Runs interactive `/review_pr` with test results in context
9. Restores original branch after review
10. Prompts to save review as markdown

## Directory Structure

```
.claude/
├── agents/           # 16 specialized agents
├── commands/         # 16 slash commands
├── helpers/          # Utility scripts
│   ├── index_python.py   # Python codebase indexer
│   ├── index_js_ts.py    # JavaScript/TypeScript indexer
│   ├── index_go.py       # Go indexer
│   ├── index_cpp.py      # C/C++ indexer
│   ├── build_c4_diagrams.py  # C4 diagram generator
│   ├── fetch-docs.py     # Documentation fetcher
│   ├── orchestrator.py   # Full workflow automation
│   ├── ralph_orchestrator.py  # Autonomous implementation (build → review → fix)
│   ├── pr_reviewer.py    # PR review automation
│   └── vulnerability-check/ # Vulnerability scanning (OSV, GitHub, CISA, NCSC)
└── settings.json     # Permissions and hooks

memories/
├── templates/        # Documentation templates (project.md, todo.md, done.md, pr_review.md)
├── best_practices/   # Documented patterns from implementations
├── technical_docs/   # Library/framework documentation
├── security_rules/   # 108 Codeguard rules (core/ + owasp/)
└── shared/
    ├── plans/        # Implementation plans (ephemeral)
    ├── research/     # Research documents (ephemeral)
    └── project/      # Project docs (project.md, todo.md, done.md)
```

## Core Workflow

The primary pattern: **Research → Plan → Implement → Cleanup**

1. `/research_codebase <topic>` - Investigate and document findings
2. `/create_plan` - Create implementation plan with user input
3. `/implement_plan <path>` - Execute plan (includes validation)
4. `/cleanup <path>` - **MANDATORY**: Document best practices, delete ephemeral artifacts
5. `/commit` and `/pr` - Create commits and PR

See [WORKFLOW.md](WORKFLOW.md) for complete details.

## Slash Commands Reference

| Command | Purpose |
|---------|---------|
| `/project` | Create project documentation |
| `/research_codebase` | Deep codebase investigation |
| `/create_plan` | Interactive implementation planning |
| `/implement_plan` | Execute approved plans |
| `/validate_plan` | Validate implementation |
| `/cleanup` | Document best practices, remove ephemeral artifacts |
| `/build_c4_docs` | Generate C4 architecture diagrams |
| `/commit` | Create git commits |
| `/pr` | Generate PR descriptions |
| `/code_reviewer` | Review code quality |
| `/review_pr` | Comprehensive PR review (reads all docs, best practices, 108 security rules) |
| `/security` | Security analysis with Codeguard rules |
| `/deploy` | Deployment preparation |
| `/fetch_technical_docs` | Fetch documentation from context7.com |
| `/index_codebase` | Index Python/TypeScript/Go/C++ codebases |
| `/vulnerability-check` | Scan dependencies for known vulnerabilities (OSV, GitHub, CISA KEV, NCSC) |

## Agent Types

**Codebase Analysis:**
- `codebase-locator` - Find WHERE files/features exist
- `codebase-analyzer` - Analyze HOW code works
- `codebase-pattern-finder` - Find similar implementations

**Planning & Architecture:**
- `plan-implementer` - Execute technical plans
- `system-architect` - Design architectures

**PR Review (used by `/review_pr`):**
- `pr-code-quality` - Line-by-line code analysis with explicit checklist (uses opus)
- `pr-security` - Security vulnerability analysis using Codeguard rules
- `pr-best-practices` - Project pattern compliance and helper reuse
- `pr-test-coverage` - Test adequacy and missing scenarios

**Documentation Research:**
- `best-practices-researcher` - Search `memories/best_practices/`
- `technical-docs-researcher` - Search `memories/technical_docs/`
- `project-context-analyzer` - Extract project documentation context

**External Research:**
- `web-researcher` - Web research

## File Naming Conventions

**Plans and Research:** `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`

**Best Practices:** `[category]-[topic].md` (e.g., `api-error-handling.md`)

## Development on This Template

### Key Files
- `install.sh` / `install-helper.sh` - Installation scripts
- `uninstall.sh` - Uninstallation script
- `.claude/settings.json` - Permissions configuration

### Testing Changes
- Use `--dry-run` to preview installation
- Test in isolated directory before deploying
- Verify uninstall removes only intended files

### Agent/Command Files
- Agents: frontmatter metadata (name, description, model, color)
- Commands: plain markdown with instructions
- Both read by Claude Code at runtime

## Best Practices Reference

Documented patterns in `memories/best_practices/`:

| Pattern | File | Use Case |
|---------|------|----------|
| Fire-and-Forget API | `api-fire-and-forget-claude-integration.md` | Background operations without progress tracking |
| Slash Command Integration | `backend-slash-command-integration.md` | Calling /commands from backend APIs |
| Shared Utilities | `code-organization-shared-utilities.md` | Extracting common code to utils.py |
| Defense-in-Depth | `security-defense-in-depth-validation.md` | Multi-layer input validation |
| Path Traversal Defense | `security-path-traversal-defense-in-depth.md` | Multiple independent validation layers for file paths |
| Subprocess Timeout | `subprocess-timeout-long-running-operations.md` | Timeout protection for long-running subprocesses |
| Batch Error Handling | `error-handling-batch-operations.md` | Per-item error handling with continue |
| Version Endpoints | `api-version-endpoints.md` | Dynamic version endpoints with fallback |

## Hooks Configuration

Security hooks in `.claude/hooks/` use a **three-layer defense architecture**:

| Layer | Mechanism | Speed | What it catches |
|-------|-----------|-------|-----------------|
| **Layer 1** | Regex patterns in `pre_tool_use.py` | ~0ms | Obvious dangerous commands (rm -rf, git push, fork bombs) |
| **Layer 2** | `settings.json` deny list via `settings_loader.py` | ~1ms | Single source of truth; enforced even in `--dangerously-skip-permissions` mode |
| **Layer 3** | LLM prompt hook (Haiku) in `settings.json` | ~1-2s | Intent-based threats regex can't see (e.g., `curl -o /tmp/x.sh && sh /tmp/x.sh`) |

**Decision modes:**
- `deny` — block the tool call entirely (dangerous patterns)
- `allow` — silently permit

**Audit logging:** All tool invocations are logged to `memories/logs/hook-audit.jsonl` with timestamp, session ID, tool, decision, and reason.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CONTAINER_MODE` | `0` | Set to `1` for relaxed security in containers (keeps git + sensitive file checks, allows `.ssh/` access, disables rm/fork/path checks) |
| `CLAUDE_AUDIO_ENABLED` | `0` | Set to `1` for audio notifications (session end, task completion, input needed) |
| `CLAUDE_HOOKS_DEBUG` | `0` | Set to `1` for debug logging (`[DEBUG]` messages in stderr) |

```bash
# Enable in your shell profile or .env
export CLAUDE_AUDIO_ENABLED=1
export CLAUDE_HOOKS_DEBUG=1

# For containerized/sandboxed environments (relaxed pre_tool_use checks)
# Still blocks: ALL git push, .env/.pem/credentials access, settings.json deny list
# Allows: .ssh/ access (only explicit keys mounted), rm -rf, path traversal, fork bombs (safe in container)
export CLAUDE_CONTAINER_MODE=1
```

### Operating Modes

| Mode | Hooks | Permissions | Environment |
|------|-------|-------------|-------------|
| **Host interactive** | Full (all checks) | `settings.json` + `settings.local.json` | Unrestricted |
| **Container interactive** | Relaxed (`CLAUDE_CONTAINER_MODE=1`) | `settings.json` + `settings.local.json` | Limited (container) |
| **Container non-interactive** | Relaxed (`CLAUDE_CONTAINER_MODE=1`) | Ignored (`--dangerously-skip-permissions`) | Limited (container) |

**Permissions files:**
- `settings.json` — global presets (read tools auto-allowed, write tools prompted). **Overwritten** on every install.
- `settings.local.json` — project-specific permission overrides. **Preserved** across installs. Use this to add allows/denies for your project. Merges with (not replaces) `settings.json`.

**Security:**
- Layer 2 (settings.json deny) is enforced in ALL modes, including `--dangerously-skip-permissions`
- Hooks always block ALL git push and sensitive file access, regardless of mode (except `.ssh/` in container mode — only explicit keys are mounted)
- Layer 3 (LLM prompt hook) only runs on Bash commands — file operations skip LLM evaluation
- `CLAUDE_CONTAINER_MODE=1` relaxes non-essential hook checks (rm, path traversal, fork bombs) that the container already constrains, and allows `.ssh/` access since only explicit keys are mounted
- Non-interactive uses `--dangerously-skip-permissions` — the only hard guarantee against hanging on a prompt with no TTY

## Common Pitfalls

- **Don't** use database tracking for fire-and-forget ops (use file/log output)
- **Don't** rely on single validation layer (use defense-in-depth)
- **Don't** validate file paths after construction (validate input first, then build path)
- **Don't** fail entire batch on first error (per-item error handling)
- **Don't** duplicate code across files (extract to `utils.py`)
- **Don't** skip `/cleanup` (best practices get lost, artifacts clutter repo)
- **Don't** pass YAML frontmatter to Claude prompts (strip it first)
- **Don't** hardcode versions in multiple places (read from pyproject.toml dynamically)
- **Don't** use broad exception handlers (catch specific exceptions only)
- **Don't** spawn subprocesses without timeouts (use asyncio.wait_for with cleanup)

## Codebase Overview Files

This project maintains automatically generated codebase overview files in `memories/codebase/`:

### Available Index Files
- `codebase_overview_claude_helpers_py.md` - Helper utilities and CLI scripts

These files are automatically generated and kept up-to-date by the `/index_codebase` command.

### What These Files Contain
Each overview file provides a comprehensive map of the codebase including:
- **Complete file tree** of the scanned directory
- **All classes and functions** with descriptions
- **Full function signatures**: input parameters, return types, and expected outputs
- **Call relationships**: where each function/class is called from (caller information)

### Why These Files Matter
These files are essential for:
- **Fast navigation**: Instantly find where code lives without extensive searching
- **Understanding structure**: See the complete architecture and organization
- **Analyzing relationships**: Understand how components interact and depend on each other
- **Code analysis**: Get function signatures and contracts without reading implementation

### Regenerating Indexes
To regenerate the codebase overview files, run:
```bash
/index_codebase
```

The indexer will automatically detect your project type and generate appropriate overview files.
