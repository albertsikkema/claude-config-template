# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **configuration template repository** for Claude Code. It provides:
- Reusable custom agents for specialized tasks
- Slash commands for common workflows
- A structured `thoughts/` directory system for documentation and planning
- Pre-configured permissions for development tools

This repository is meant to be installed into other projects using the `install.sh` script.

## Installation and Setup Commands

### Installing This Template Into Projects

**Quick Remote Install (Easiest)**:
```bash
# One-line install - downloads, installs, and cleans up automatically
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash

# Install from a specific branch (e.g., for testing new features)
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch improved_indexing

# Install from a specific branch with other options
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch improved_indexing --force
```

**Manual Install**:
```bash
# Install everything into current directory
./install-helper.sh

# Install only Claude configuration (.claude/)
./install-helper.sh --claude-only

# Install only thoughts structure
./install-helper.sh --thoughts-only

# Preview what will be installed without making changes
./install-helper.sh --dry-run

# Clean reinstall (⚠️ removes all thoughts/ content)
./install-helper.sh --force

# Install into a specific directory
./install-helper.sh /path/to/project
```

**Important**:
- **Default behavior**: `.claude/` is always updated, `thoughts/` preserves existing content and adds missing directories
- **With `--force`**: Completely replaces `thoughts/` directory, removing all plans, research, and project docs
- The installer automatically updates `.gitignore` to exclude:
  - `.claude/` - Claude configuration
  - `thoughts/` - Documentation and plans
  - `claude-helpers/` - Helper scripts

If `.gitignore` doesn't exist, it will be created. Existing entries are preserved.

### Uninstalling From Projects

```bash
# Remove everything
./uninstall.sh

# Remove only Claude configuration
./uninstall.sh --claude-only

# Preview what will be removed
./uninstall.sh --dry-run
```

### Helper Scripts

```bash
# Generate metadata for research/plan documents
./claude-helpers/spec_metadata.sh
```

### Orchestrator Agent

```bash
# Create .env.claude file with API key
echo "OPENAI_API_KEY=sk-..." > .env.claude

# Run orchestrator (uv auto-installs dependencies)
uv run claude-helpers/orchestrator.py "Add user authentication"
uv run claude-helpers/orchestrator.py --json "Refactor database"
```

The orchestrator automates the full workflow:
1. Indexes codebase (`/index_codebase`)
2. Researches topic (`/research_codebase`)
3. Creates plan (`/create_plan`)
4. Implements plan (`/implement_plan`)
5. Reviews code (`/code_reviewer`)

Use `--no-implement` to stop after creating the plan. Streams progress to stderr, outputs results to stdout. Supports both OpenAI and Azure OpenAI (auto-detected from `.env`).

**Tip**: Add an alias to your `~/.zshrc` or `~/.bashrc` for easy access:
```bash
alias orchestrate='uv run /path/to/claude-helpers/orchestrator.py'
```
Then use: `orchestrate "Add user authentication"`

## Architecture

### Directory Structure

```
.claude/
├── agents/          # 12 specialized agents for different tasks
├── commands/        # 14 slash commands for common workflows
└── settings.local.json  # Pre-approved tool permissions

docs/                    # Helper script documentation
├── README-fetch-docs.md     # Documentation fetcher guide
├── README-indexers.md       # Codebase indexers guide
├── README-c4-diagrams.md    # C4 architecture diagrams guide
├── README-fetch-openapi.md  # OpenAPI fetcher guide
└── README-spec-metadata.md  # Metadata generator guide

thoughts/
├── templates/       # Project documentation templates
│   ├── project.md.template  # Project context template
│   ├── todo.md.template     # Active work tracking template
│   ├── done.md.template     # Completed work template
│   ├── adr.md.template      # Architecture Decision Records template
│   └── changelog.md.template # Changelog template
├── best_practices/  # Best practices documentation from implementations
├── technical_docs/  # Technical documentation storage
├── security_rules/  # Project Codeguard security rules (108 rules)
│   ├── core/        # 22 Cisco-curated core security rules
│   └── owasp/       # 86 OWASP-based security rules
└── shared/
    ├── plans/       # Implementation plans (dated: YYYY-MM-DD-*.md, deleted after cleanup)
    ├── research/    # Research documents (dated: YYYY-MM-DD-*.md, deleted after cleanup)
    ├── reviews/     # Security and code reviews (dated: security-analysis-YYYY-MM-DD.md)
    ├── rationalization/  # Ephemeral working docs (deleted after cleanup)
    └── project/     # Project documentation (created by /project)
        ├── project.md  # Project context (what/why/stack/constraints)
        ├── todo.md     # Active work (Must Haves / Should Haves)
        └── done.md     # Completed work with traceability

claude-helpers/      # Utility scripts for workflows
├── index_python.py  # Python codebase indexer
├── index_js_ts.py   # JavaScript/TypeScript codebase indexer
├── index_go.py      # Go codebase indexer
├── build_c4_diagrams.py  # C4 PlantUML diagram builder
└── fetch-docs.py    # Documentation fetcher
```

### Agent System

The repository includes 12 specialized agents that are automatically invoked by Claude Code or can be explicitly requested:

**Codebase Analysis:**
- `codebase-locator` - Finds WHERE files and features exist
- `codebase-analyzer` - Analyzes HOW code works (implementation details)
- `codebase-pattern-finder` - Discovers similar implementations and patterns
- `codebase-researcher` - Comprehensive codebase investigations (orchestrates other agents)

**Planning & Architecture:**
- `plan-implementer` - Executes approved technical plans from `thoughts/shared/plans/`
- `system-architect` - Designs architectures and evaluates patterns

**Documentation Research:**
- `project-context-analyzer` - Extracts and synthesizes project documentation context
- `best-practices-researcher` - Searches `thoughts/best_practices/` for documented patterns and lessons learned
- `technical-docs-researcher` - Searches `thoughts/technical_docs/` for library and framework documentation
- `thoughts-locator` - Finds relevant documents in `thoughts/` directory
- `thoughts-analyzer` - Deep analysis of thoughts directory content

**External Research:**
- `web-search-researcher` - Researches information from the web

### Slash Commands

Available commands (use `/` prefix in Claude Code):

**Documentation:**
- `/project` - Create project documentation from templates

**Planning & Implementation:**
- `/create_plan` - Interactive implementation plan creation (saves to `thoughts/shared/plans/`)
- `/implement_plan <path>` - Execute an approved plan file (includes automatic validation at end)
- `/validate_plan <path>` - Validate implementation correctness (standalone, optional if using `/implement_plan`)
- `/cleanup <path>` - Document best practices and clean up ephemeral artifacts (plan, research)

**Architecture Documentation:**
- `/build_c4_docs` - Generate C4 architecture diagrams (System Context, Container, Component levels in Mermaid and PlantUML formats)

**Research:**
- `/research_codebase` - Comprehensive codebase investigation (saves to `thoughts/shared/research/`)

**Git Workflows:**
- `/commit` - Create well-formatted git commits
- `/pr` - Generate comprehensive PR descriptions

**Code Quality:**
- `/code_reviewer` - Review code quality and suggest improvements
- `/security` - Comprehensive security analysis and code review (18 security areas, language-agnostic)

**Deployment:**
- `/deploy` - Automated deployment preparation workflow (analyze changes, version bump, build, release)

## Key Workflows

### Documentation Setup

Use the `/project` command to create project documentation using the **ultra-lean 3-file structure**:

1. **Describe your need**: Run `/project <what you want>` in Claude Code
   - Examples: "Create full docs", "Set up project documentation", "Document my MVP"
2. **Answer questions**: Provide project details based on context
3. **Review**: Claude creates customized documentation in `thoughts/shared/project/`
4. **Maintain**: Update documentation as your project evolves

The command creates **3 essential files**:

**1. project.md** - Project context (stable, rarely changes)
- What you're building and why
- Technical stack (backend, frontend, infrastructure)
- Success metrics and constraints
- Architecture overview
- What's explicitly out of scope

**2. todo.md** - Active work tracking (living document, constantly updated)
- **Must Haves** - Critical work for MVP/current release
- **Should Haves** - Important but not blocking work
- Inline blocking: `[BLOCKED]` prefix with blocker description
- Dependencies: Ordering (top-to-bottom) + explicit `(requires:)` mentions
- Categories: Features, Bugs & Fixes, Improvements, Technical & Infrastructure

**3. done.md** - Completed work history (append-only)
- Organized by month/year (2025-10, 2025-09, etc.)
- Links to implementation plans, research, ADRs, PRs
- Tracks outcomes and learnings
- Provides traceability and velocity tracking

**Workflow**:
- New work → todo.md (Must Have or Should Have)
- Gets blocked → Add `[BLOCKED]` prefix with blocker info
- Unblocked → Remove `[BLOCKED]` prefix
- Completed → Move to done.md with references

Templates are stored in `thoughts/templates/` and remain unchanged.

**For complete methodology details**, see the "Ultra-Lean 3-File Documentation Method" section in [WORKFLOW.md](WORKFLOW.md).

### Research → Plan → Implement → Cleanup Pattern

This is the primary workflow pattern, based on "Faking a Rational Design Process in the AI Era":

1. **Research**: Use `/research_codebase <topic>` to investigate
   - Spawns parallel agents to analyze codebase and documented best practices
   - Saves findings to `thoughts/shared/research/YYYY-MM-DD-<topic>.md`

2. **Plan**: Use `/create_plan` with research findings
   - Interactive planning with user input
   - Saves plan to `thoughts/shared/plans/YYYY-MM-DD-<feature>.md`

3. **Implement**: Use `/implement_plan thoughts/shared/plans/YYYY-MM-DD-<feature>.md`
   - Executes the approved plan step-by-step
   - Can resume if interrupted
   - **Automatically runs validation at the end** to verify correctness
   - Addresses validation findings (implements missing items or documents exceptions)
   - Appends validation report to the plan file
   - Only completes when validation passes

4. **Cleanup** (MANDATORY): Use `/cleanup thoughts/shared/plans/YYYY-MM-DD-<feature>.md`
   - Analyzes what actually happened vs. what was planned
   - Documents best practices with lessons learned, trade-offs, and examples
   - Updates CLAUDE.md with new patterns/conventions
   - Updates project documentation (project.md, todo.md, done.md as appropriate)
   - Deletes ephemeral artifacts (plan, research, rationalization documents)
   - **Key principle**: Extract knowledge, remove clutter

5. **Commit & PR**: Use `/commit` and `/pr`
   - Create well-formatted commits
   - Generate comprehensive PR description

#### Why Cleanup Matters

From Parnas & Clements (1986): Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process.

**For AI-assisted development:**
- AI assistants have no memory between sessions
- Documentation becomes the "single source of truth"
- Without documented best practices, lessons learned get lost
- Ephemeral artifacts clutter the repository without providing value

**Cleanup ensures:**
- Best practices are documented with real examples (thoughts/best_practices/)
- Lessons learned and trade-offs are captured for future work
- Patterns are captured (CLAUDE.md updates)
- Project documentation stays in sync (project.md, todo.md, done.md)
- Completed work moved to done.md with references to best practices
- Rejected alternatives are documented (prevents re-exploration)
- Ephemeral artifacts (plans, research) are removed after knowledge extraction
- Future AI sessions have clean, actionable context

### Deployment Workflow

Use the `/deploy` command to automate deployment preparation:

**What it does:**
0. **Initializes CHANGELOG** (creates from template if missing, validates format)
1. **Analyzes changes** since last release (git commits, code changes)
2. **Updates version** (auto-detects package.json, pyproject.toml, Cargo.toml, etc.)
3. **Generates CHANGELOG** following Keep a Changelog standard
4. **Runs build & tests** (detects project type and runs appropriate commands)
5. **Prepares deployment** (git commands, platform-specific instructions)
6. **Creates release** (optional GitHub/GitLab release with notes)

**Customization:**
The `/deploy` command is **generic and language-agnostic**. Customize for your project:
- **Step 0**: Update CHANGELOG template with your repository URLs
- **Step 4**: Add project-specific build commands, test suites, cache invalidation
- **Step 5**: Configure deployment platform (Heroku, Vercel, AWS, Docker, etc.)
- **Step 6**: Customize release asset generation and notifications

**Usage:**
```bash
/deploy
```

The command uses parallel subagents to execute each step efficiently and provides clear deployment instructions at the end.

### Security Analysis with Codeguard Rules

The `/security` command now integrates **Project Codeguard** security rules for language-specific secure coding guidance.

**What are Codeguard Rules?**
- **108 comprehensive security rules** (22 core + 86 OWASP-based)
- Curated by Cisco and aligned with OWASP best practices
- Language-specific secure coding patterns (Python, JavaScript, Go, Java, C, etc.)
- Framework-specific security guidance
- Code examples demonstrating safe implementations

**How it works:**
1. **Phase 0**: `/security` detects your technology stack (languages, frameworks)
2. **Phase 0 (continued)**: Loads relevant Codeguard rules from `thoughts/security_rules/`
   - Filters by language using YAML frontmatter
   - Loads 3-5 most relevant rules based on stack and security topics
   - Extracts secure coding patterns, checklists, and code examples
3. **Phases 1-3**: Security analysis references Codeguard rules alongside framework-specific checks
4. **Report**: Includes Codeguard rule references with file paths

**Rule Structure:**
```
thoughts/security_rules/
├── core/      # 22 core rules (authentication, input validation, authorization, etc.)
└── owasp/     # 86 OWASP rules (SQL injection, XSS, CSRF, session management, etc.)
```

**Example rules:**
- `codeguard-0-authentication-mfa.md` - Authentication & MFA best practices
- `codeguard-0-input-validation-injection.md` - Input validation & injection defense
- `codeguard-0-sql-injection-prevention.md` - SQL injection prevention
- `codeguard-0-authorization-access-control.md` - Authorization & access control

**Usage:**
```bash
/security
```

The command automatically loads relevant rules based on your project's technology stack.

**Source:**
Project Codeguard: https://github.com/project-codeguard/rules

### File Naming Conventions

**Plans and Research:**
- Format: `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`
- Examples:
  - `2025-10-14-oauth-support.md`
  - `2025-10-14-ENG-1478-parent-tracking.md`

**Project Documentation:**
- 3 essential files in `thoughts/shared/project/`:
  - `project.md` - Project context
  - `todo.md` - Active work (Must Haves / Should Haves)
  - `done.md` - Completed work with traceability

**Best Practices:**
- Saved in `thoughts/best_practices/`
- Format: `[category]-[topic].md` (category-based naming)
- Examples: `authentication-oauth-patterns.md`, `database-transaction-handling.md`, `api-error-handling.md`
- Created during `/cleanup` workflow
- Include implementation examples, trade-offs, and lessons learned

**Documentation Templates:**
- Stored in `thoughts/templates/` with `.template` extension
- Install script removes `.template` suffix during installation

## Pre-Approved Permissions

The `settings.local.json` includes pre-approved permissions for:

**Development Tools:**
- `pytest` commands (unit, integration, collection)
- `git` operations (checkout, push, show, log)
- `docker` and `docker-compose` commands
- `make` and `pre-commit` hooks
- Python execution and venv activation
- GitHub CLI (`gh pr view`)
- File operations (`ls`, `find`, `mkdir`, `tree`)
- Network tools (`curl`)

**Documentation Domains:**
- docs.astral.sh
- fastapi.tiangolo.com
- docs.sqlalchemy.org
- fastapi-users.github.io
- ai.pydantic.dev
- learn.microsoft.com
- github.com
- betterstack.com
- testdriven.io
- cheatsheetseries.owasp.org
- localhost (for testing)

**General:**
- WebSearch (unrestricted)

## Customization for Projects

When installing this template into a project:

1. **Review and adjust permissions** in `.claude/settings.local.json`
2. **Create project documentation** using `/project` command
3. **Add project-specific agents** in `.claude/agents/` if needed
4. **Add project-specific commands** in `.claude/commands/` if needed
5. **Store technical documentation** in `thoughts/technical_docs/` for the `technical-docs-researcher` agent
6. **Document best practices** as you implement features - the `/cleanup` command will help structure them

## Development on This Template

When modifying this template repository itself:

**Key Files:**
- `install.sh` - Installation script with dry-run and force options
- `uninstall.sh` - Uninstallation script with safety checks
- `README.md` - User-facing documentation
- `.gitignore` - Excludes OS files, editor configs, and test directories

**Testing Changes:**
- Use `--dry-run` flag to preview installation changes
- Test in isolated directory before deploying to projects
- Verify uninstall removes only intended files

**Agent/Command Files:**
- Agents use frontmatter metadata (name, description, model, color)
- Commands are plain markdown with instructions
- Both are read by Claude Code at runtime

## Codebase Overview Files

This project maintains automatically generated codebase overview files in `thoughts/codebase/`:

### Available Index Files
- `codebase_overview_claude-helpers_py.md` - Python helper scripts overview
- `codebase_overview_hooks_py.md` - Claude Code hooks overview

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
