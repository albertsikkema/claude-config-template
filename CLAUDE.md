# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Codebase Index

**IMPORTANT**: Before searching the codebase with Grep, Glob, or Explore, first read the codebase index:

**`thoughts/codebase/codebase_overview_claude_flow_board_js_ts.md`**

This index contains:
- **Most Used Symbols**: Top functions/components by usage count
- **Library Files**: All exports with descriptions and "used by" references
- **API Endpoints**: All REST API routes
- **Dependency Graph**: Which files are most imported

Reading the index first saves tokens and improves accuracy.


## Repository Purpose

This is a **configuration template repository** for Claude Code. It installs into other projects via the `install.sh` script, providing:
- 12 specialized agents for code analysis, planning, and research
- 14 slash commands for common workflows
- A `thoughts/` directory system for documentation and plans
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

# Force reinstall (removes existing thoughts/)
./install-helper.sh --force
```

### Orchestrator (automated workflow)

```bash
# Requires .env.claude with OPENAI_API_KEY
uv run claude-helpers/orchestrator.py "Add user authentication"
uv run claude-helpers/orchestrator.py --no-implement "Refactor database"  # Stop after planning
```

### Claude-Flow (subproject)

```bash
cd claude-helpers/claude-flow

# Desktop app (recommended - single window, no ports to manage)
make desktop   # Launch desktop app with full HMR

# Build for distribution
make build     # Build complete app (clean + frontend + backend)
make install   # Build and install to /Applications

# Development mode (split terminal setup)
make dev       # Start development server (backend only)
make test      # Run tests
make lint      # Run linting
```

See [claude-helpers/claude-flow/README.md](claude-helpers/claude-flow/README.md) for details.

## Directory Structure

```
.claude/
├── agents/           # 12 specialized agents
├── commands/         # 14 slash commands
└── settings.json     # Permissions and hooks

claude-helpers/
├── index_python.py   # Python codebase indexer
├── index_js_ts.py    # JavaScript/TypeScript indexer
├── index_go.py       # Go indexer
├── build_c4_diagrams.py  # C4 diagram generator
├── fetch-docs.py     # Documentation fetcher
├── orchestrator.py   # Full workflow automation
└── claude-flow/      # FastAPI backend for task management (subproject)

thoughts/
├── templates/        # Documentation templates (project.md, todo.md, done.md)
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
| `/security` | Security analysis with Codeguard rules |
| `/deploy` | Deployment preparation |
| `/fetch_technical_docs` | Fetch documentation from context7.com |
| `/index_codebase` | Index Python/TypeScript/Go codebases |

## Agent Types

**Codebase Analysis:**
- `codebase-locator` - Find WHERE files/features exist
- `codebase-analyzer` - Analyze HOW code works
- `codebase-pattern-finder` - Find similar implementations

**Planning & Architecture:**
- `plan-implementer` - Execute technical plans
- `system-architect` - Design architectures

**Documentation Research:**
- `best-practices-researcher` - Search `thoughts/best_practices/`
- `technical-docs-researcher` - Search `thoughts/technical_docs/`
- `project-context-analyzer` - Extract project documentation context

**External Research:**
- `web-search-researcher` - Web research

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

## Claude-Flow Architecture

The `claude-helpers/claude-flow/` subproject implements these patterns:

### Desktop App (Per-Repo PyWebView)
Claude-Flow runs as a **per-repo desktop application** using PyWebView:
- **Lightweight**: Uses system WebView (~10MB vs Electron's ~100MB)
- **Per-Repo Isolation**: Each repo gets its own app instance with dedicated port
- **Dynamic Port Allocation**: Automatically finds available port, saves to `.claude-flow.port`
- **Integrated Stack**: FastAPI serves both API routes and built React frontend
- **No Node Runtime**: Frontend pre-built to `claude-flow-board/dist/`, served as static files

**Launch**: `cd claude-helpers/claude-flow && make desktop`

Architecture benefits:
- Clean hook integration (each instance scoped to one repo)
- No port conflicts across multiple repos
- Simpler state management (no global state)
- Single window UX instead of split terminal setup

### Database Path
Global location shared across all repos:
- macOS: `~/Library/Application Support/claude-flow/kanban.db`
- Windows: `%LOCALAPPDATA%/claude-flow/kanban.db`
- Linux: `~/.local/share/claude-flow/kanban.db`

To query the database directly:
```bash
sqlite3 ~/Library/Application\ Support/claude-flow/kanban.db "SELECT * FROM tasks;"
sqlite3 ~/Library/Application\ Support/claude-flow/kanban.db "SELECT * FROM settings;"
```

### Fire-and-Forget API Pattern
For background operations without progress tracking:
- Sync HTTP handler spawns daemon thread
- Thread creates isolated asyncio event loop
- Returns immediately (<1s) while task runs in background
- Use for: batch exports, background cleanup, doc fetching, security checks

### Security Check UI Feature
The Claude-Flow frontend provides a Security Check panel that triggers the `/security` command:
- Click "Security Check" button in the header
- Click "Run Security Check" to start comprehensive analysis
- Reports are saved to `thoughts/shared/reviews/security-analysis-*.md`
- Previous reports are listed with timestamps and file sizes
- Click any report to view its markdown content

**API Endpoints**:
- `POST /api/security/check` - Start new security analysis (fire-and-forget)
- `GET /api/security/checks` - List all security reports (most recent first)
- `GET /api/security/report/{filename}` - Get report content

**Security Features**:
- 30-minute subprocess timeout prevents runaway processes
- Path traversal protection with defense-in-depth validation
- Filename pattern validation (only `security-analysis-*.md` allowed)

### Slash Command Integration from Backend
Read commands from `.claude/commands/`, strip frontmatter, inject context:
```python
# Read and strip YAML frontmatter
cmd_content = read_slash_command("fetch_technical_docs")

# Build prompt with context and constraints
prompt = f"""{cmd_content}

## Context
{packages_list}

**Important**: Skip discovery. Begin immediately.
"""

# Spawn Claude Code
process = await asyncio.create_subprocess_exec(
    CLAUDE_PATH, "--dangerously-skip-permissions",
    "--model", "haiku", "-p", prompt,
    cwd=str(PROJECT_ROOT)
)
```

**Key aspects**:
- Strip YAML frontmatter (metadata, not prompt content)
- Add constraints to prevent Claude asking questions
- Set HOME env var and cwd for path resolution
- Use `--dangerously-skip-permissions` for automation

Model selection: `haiku` (simple), `sonnet` (moderate), `opus` (complex)

See: `thoughts/best_practices/backend-slash-command-integration.md`

### Defense-in-Depth Validation
Multiple independent layers for security-sensitive input:
1. Pydantic constraints (types, bounds)
2. Character whitelist
3. Explicit security checks (path traversal)
4. Downstream sanitization

### Batch Operation Error Handling
Per-item try/except with logging, continue processing on failure.

## Best Practices Reference

Documented patterns in `thoughts/best_practices/`:

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

This project maintains automatically generated codebase overview files in `thoughts/codebase/`:

### Available Index Files
- `codebase_overview_claude_helpers_py.md` - Helper utilities and CLI scripts (24 Python files)
- `codebase_overview_claude_flow_py.md` - Claude-Flow FastAPI backend (16 Python files)
- `codebase_overview_claude_flow_board_js_ts.md` - Claude-Flow React frontend (99 TypeScript files)

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
