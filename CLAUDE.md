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

## Architecture

### Directory Structure

```
.claude/
├── agents/          # 11 specialized agents for different tasks
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
├── shared/
│   ├── plans/       # Implementation plans (dated: YYYY-MM-DD-*.md)
│   ├── research/    # Research documents (dated: YYYY-MM-DD-*.md)
│   ├── reviews/     # Security and code reviews (dated: security-analysis-YYYY-MM-DD.md)
│   ├── adrs/        # Architecture Decision Records (NNN-title.md)
│   ├── rationalization/  # Ephemeral working docs (deleted after rationalization)
│   └── project/     # Project documentation (created by /project)
│       ├── project.md  # Project context (what/why/stack/constraints)
│       ├── todo.md     # Active work (Must Haves / Should Haves)
│       └── done.md     # Completed work with traceability
└── technical_docs/  # Technical documentation storage

claude-helpers/      # Utility scripts for workflows
├── index_python.py  # Python codebase indexer
├── index_ts.py      # TypeScript codebase indexer
├── index_go.py      # Go codebase indexer
├── build_c4_diagrams.py  # C4 PlantUML diagram builder
└── fetch-docs.py    # Documentation fetcher
```

### Agent System

The repository includes 11 specialized agents that are automatically invoked by Claude Code or can be explicitly requested:

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
- `technical-docs-researcher` - Searches `thoughts/technical_docs/` for best practices
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
- `/rationalize <path>` - Rationalize implementation and update documentation

**Architecture Documentation:**
- `/build_c4_docs` - Generate C4 architecture diagrams (System Context, Container, Component levels in Mermaid and PlantUML formats)

**Research:**
- `/research_codebase` - Comprehensive codebase investigation (saves to `thoughts/shared/research/`)

**Git Workflows:**
- `/commit` - Create well-formatted git commits
- `/describe_pr` - Generate comprehensive PR descriptions

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

### Research → Plan → Implement → Rationalize Pattern

This is the primary workflow pattern, based on "Faking a Rational Design Process in the AI Era":

1. **Research**: Use `/research_codebase <topic>` to investigate
   - Spawns parallel agents to analyze codebase
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

4. **Rationalize** (MANDATORY): Use `/rationalize thoughts/shared/plans/YYYY-MM-DD-<feature>.md`
   - Analyzes what actually happened vs. what was planned
   - Updates plan to show final approach as if it was always intended
   - Creates ADRs for significant decisions
   - Updates CLAUDE.md with new patterns/conventions
   - Updates project documentation (project.md, todo.md, done.md as appropriate)
   - Documents rejected alternatives
   - **Key principle**: Present clean narrative, not messy discovery process

5. **Commit & PR**: Use `/commit` and `/describe_pr`
   - Create well-formatted commits
   - Generate comprehensive PR description

#### Why Rationalization Matters

From Parnas & Clements (1986): Documentation should show the cleaned-up, rationalized version of what happened, not the messy discovery process.

**For AI-assisted development:**
- AI assistants have no memory between sessions
- Documentation becomes the "single source of truth"
- Without rationalized docs, design decisions get lost
- Prevents the codebase from becoming a patchwork of different "styles"

**Rationalization ensures:**
- Plans reflect reality (what was actually built)
- Decisions are documented (ADRs with rationale)
- Patterns are captured (CLAUDE.md updates)
- Project documentation stays in sync (project.md, todo.md, done.md)
- Completed work moved to done.md with references
- Rejected alternatives are recorded (prevents re-exploration)
- Future AI sessions have proper context

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

**ADRs (Architecture Decision Records):**
- Saved in `thoughts/shared/adrs/`
- Format: `NNN-decision-title.md` (sequential numbering)
- Examples: `001-use-optimistic-locking.md`, `002-cache-invalidation-strategy.md`
- Created during `/rationalize` workflow

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
