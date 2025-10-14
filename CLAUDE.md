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

# Force overwrite existing files
./install-helper.sh --force

# Install into a specific directory
./install-helper.sh /path/to/project
```

**Important**: The installer automatically updates `.gitignore` to exclude:
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
├── commands/        # 8 slash commands for common workflows
└── settings.local.json  # Pre-approved tool permissions

thoughts/
├── templates/       # Project documentation templates
│   ├── epics.md.template
│   ├── musthaves.md.template
│   ├── project.md.template
│   ├── shouldhaves.md.template
│   └── todo.md.template
├── shared/
│   ├── plans/       # Implementation plans (dated: YYYY-MM-DD-*.md)
│   ├── research/    # Research documents (dated: YYYY-MM-DD-*.md)
│   └── project/     # Project documentation (created by /project)
│       └── epics/   # Epic documents
└── technical_docs/  # Technical documentation storage

claude-helpers/      # Utility scripts for workflows
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
- `/implement_plan <path>` - Execute an approved plan file
- `/validate_plan <path>` - Validate a plan before implementation

**Research:**
- `/research_codebase` - Comprehensive codebase investigation (saves to `thoughts/shared/research/`)

**Git Workflows:**
- `/commit` - Create well-formatted git commits
- `/describe_pr` - Generate comprehensive PR descriptions

**Code Quality:**
- `/code_reviewer` - Review code quality and suggest improvements

## Key Workflows

### Documentation Setup

Use the `/project` command to create project documentation:

1. **Describe your need**: Run `/project <what you want>` in Claude Code
   - Examples: "Create full docs", "Document MVP features", "Create authentication epic"
2. **Answer questions**: Provide project details based on context
3. **Review**: Claude creates customized documentation in `thoughts/shared/project/`
4. **Maintain**: Update documentation as your project evolves

The command creates documentation such as:
- `thoughts/shared/project/project-overview.md` - Project overview
- `thoughts/shared/project/mvp-requirements.md` - MVP requirements
- `thoughts/shared/project/post-mvp-features.md` - Post-MVP features
- `thoughts/shared/project/technical-todos.md` - Technical TODOs
- `thoughts/shared/project/epics/epic-[name].md` - Epic planning (in epics subdirectory)

Templates are stored in `thoughts/templates/` and remain unchanged.

### Research → Plan → Implement Pattern

This is the primary workflow pattern:

1. **Research**: Use `/research_codebase <topic>` to investigate
   - Spawns parallel agents to analyze codebase
   - Saves findings to `thoughts/shared/research/YYYY-MM-DD-<topic>.md`

2. **Plan**: Use `/create_plan` with research findings
   - Interactive planning with user input
   - Saves plan to `thoughts/shared/plans/YYYY-MM-DD-<feature>.md`

3. **Implement**: Use `/implement_plan thoughts/shared/plans/YYYY-MM-DD-<feature>.md`
   - Executes the approved plan step-by-step
   - Can resume if interrupted

### File Naming Conventions

**Plans and Research:**
- Format: `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`
- Examples:
  - `2025-10-14-oauth-support.md`
  - `2025-10-14-ENG-1478-parent-tracking.md`

**Project Documentation:**
- Use descriptive names: `project-overview.md`, `mvp-requirements.md`, etc.
- Or use template names: `project.md`, `musthaves.md`, `shouldhaves.md`, `todo.md`

**Epics:**
- Saved in `thoughts/shared/project/epics/`
- Format: `epic-[name].md`
- Examples: `epic-authentication.md`, `epic-payment-processing.md`

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
