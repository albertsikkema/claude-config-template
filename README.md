# Claude Code Configuration Template

A powerful, reusable configuration system for [Claude Code](https://claude.com/code) that supercharges your development workflow with custom agents, intelligent slash commands, and structured project documentation.

## ⚡ Quick Install

**First time installation or update (preserves your work):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash
```

**Install from a specific branch:**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch improved_indexing
```

**Clean reinstall (⚠️ overwrites important stuff):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --force
```

**Clean reinstall from a specific branch:**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch improved_indexing --force
```

**Optional: Start monitoring dashboard** (requires [Bun](https://bun.sh)):
```bash
./start-monitoring.sh
```
See the [Multi-Agent Observability Dashboard](#-multi-agent-observability-dashboard) section for details.

## 🗑️ Quick Uninstall

**Remove configuration (preserves thoughts/):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/uninstall.sh | bash
```

**Remove everything including thoughts/ (⚠️ overwrites important stuff):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/uninstall.sh | bash -s -- --force
```

---

## 🎯 What's This?

This is a **configuration template** that you install into your projects. It provides:

- **Complete development workflow** - Research → Plan → Implement → Rationalize → Deploy ([see WORKFLOW.md](WORKFLOW.md))
- **11 specialized AI agents** - Automated research, code analysis, and architecture design
- **13 slash commands** - Streamlined workflows for common tasks (including C4 architecture diagrams and deployment automation)
- **Multi-agent observability** - Real-time monitoring dashboard with AI-powered event summaries
- **Structured documentation system** - Templates and organization for project docs
- **Pre-configured permissions** - Ready-to-use tool access for development

Think of it as a **productivity multiplier** for Claude Code - install once, benefit forever.

**📖 New to this template? Start with [WORKFLOW.md](WORKFLOW.md) for the complete development workflow guide.**

Partly based on/ inspired by:
- https://github.com/humanlayer/humanlayer
- https://github.com/Wirasm/PRPs-agentic-eng

Monitoring dashboard:
- https://github.com/disler/claude-code-hooks-multi-agent-observability


## 📦 What You Get

### 🤖 Intelligent Agents

**Codebase Intelligence:**
- `codebase-locator` - Find WHERE code lives
- `codebase-analyzer` - Understand HOW code works
- `codebase-pattern-finder` - Discover similar implementations
- `codebase-researcher` - Orchestrate comprehensive research

**Architecture & Planning:**
- `system-architect` - Design systems and evaluate patterns
- `plan-implementer` - Execute approved technical plans

**Documentation Research:**
- `project-context-analyzer` - Extract and synthesize project documentation context
- `technical-docs-researcher` - Search technical documentation
- `thoughts-analyzer` - Deep dive into your thoughts directory
- `thoughts-locator` - Find relevant documents

**External Research:**
- `web-search-researcher` - Research from the web

### ⚡ Slash Commands

| Command | Purpose |
|---------|---------|
| `/project` | Create project documentation from templates |
| `/research_codebase` | Deep codebase investigation |
| `/create_plan` | Interactive implementation planning |
| `/implement_plan` | Execute approved plans |
| `/validate_plan` | Validate implementation correctness |
| `/rationalize` | Rationalize implementation and update docs |
| `/build_c4_docs` | Generate C4 architecture diagrams (System Context, Container, Component) |
| `/commit` | Create well-formatted git commits |
| `/describe_pr` | Generate comprehensive PR descriptions |
| `/code_reviewer` | Review code quality |
| `/deploy` | Automated deployment preparation (version, changelog, build, release) |
| `/fetch_technical_docs` | Fetch LLM-optimized documentation from context7.com |
| `/index_codebase` | Index Python/TypeScript/Go codebases |

### 📁 Directory Structure

After installation, you'll have:

```
your-project/
├── .claude/
│   ├── agents/              # 11 specialized agents
│   ├── commands/            # 13 slash commands
│   ├── hooks/               # Observability hooks (if monitoring enabled)
│   └── settings.json        # Configuration and hooks
│
├── docs/                    # Helper script documentation
│   ├── README-fetch-docs.md     # Documentation fetcher guide
│   ├── README-indexers.md       # Codebase indexers guide
│   ├── README-c4-diagrams.md    # C4 architecture diagrams guide
│   ├── README-fetch-openapi.md  # OpenAPI fetcher guide
│   └── README-spec-metadata.md  # Metadata generator guide
│
├── claude-helpers/          # Utility scripts
│   ├── README.md            # Scripts overview
│   ├── index_python.py      # Python codebase indexer
│   ├── index_ts.py          # TypeScript codebase indexer
│   ├── index_go.py          # Go codebase indexer
│   ├── build_c4_diagrams.py # C4 PlantUML diagram builder
│   ├── fetch-docs.py        # Documentation fetcher
│   ├── fetch_openapi.sh     # OpenAPI schema fetcher
│   └── spec_metadata.sh     # Metadata generator
│
└── thoughts/
    ├── templates/           # Documentation templates
    │   ├── project.md.template  # Project context template
    │   ├── todo.md.template     # Active work tracking template
    │   ├── done.md.template     # Completed work template
    │   ├── adr.md.template      # Architecture Decision Records template
    │   └── changelog.md.template # Changelog template
    │
    ├── technical_docs/      # Technical documentation storage
    │
    └── shared/
        ├── plans/           # Implementation plans
        ├── research/        # Research documents
        ├── adrs/            # Architecture Decision Records
        ├── rationalization/ # Ephemeral working docs (auto-deleted)
        └── project/         # Project documentation (3-file structure)
```

## 🔍 Multi-Agent Observability Dashboard

Gain real-time visibility into Claude Code's decision-making process with the monitoring dashboard. Watch agents spawn, tools execute, and see AI-generated summaries of all activities. Basically uses this repo: [https://github.com/disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)

### What You Get

- **Real-time event streaming** - See every tool use, agent spawn, and notification as it happens
- **AI-powered summaries** - Automatically generated summaries of complex events
- **Session tracking** - Follow complete conversation flows and agent orchestration
- **Event filtering** - Focus on specific event types or sessions
- **WebSocket updates** - Live dashboard updates with no refresh needed

### Quick Start

**Prerequisites**: [Bun](https://bun.sh) must be installed
```bash
# Install Bun (macOS/Linux)
curl -fsSL https://bun.sh/install | bash
```

**Option 1: One-Line Setup** (Easiest)
```bash
./start-monitoring.sh
```

This will:
1. Clone the monitoring dashboard repository
2. Install all dependencies using Bun
3. Set up observability hooks in `.claude/hooks/`
4. Configure hooks in `.claude/settings.json`
5. Start the monitoring server and dashboard

**Option 2: Skip Hooks Setup** (if you have custom hooks)
```bash
./start-monitoring.sh --skip-hooks
```

**Option 3: Force Clean Reinstall**
```bash
./start-monitoring.sh --force-install
```

### Accessing the Dashboard

Once started, access:
- **Dashboard UI**: http://localhost:5173
- **Server API**: http://localhost:4000

### What Gets Tracked

The monitoring system captures:
- **PreToolUse** - Before any tool executes
- **PostToolUse** - After tool execution completes
- **Notification** - User input requests (with optional TTS)
- **Stop** - Conversation stop events
- **SubagentStop** - When spawned agents complete
- **PreCompact** - Before context window compaction
- **UserPromptSubmit** - User message submissions
- **SessionStart/End** - Session lifecycle events

### Helper Scripts

After starting, you can:
```bash
# Stop the monitoring system
./claude-code-hooks-multi-agent-observability/scripts/reset-system.sh

# Test the monitoring system
./claude-code-hooks-multi-agent-observability/scripts/test-system.sh
```

### How It Works

1. **Hooks** in `.claude/hooks/` intercept Claude Code events
2. **Events** are sent to the server at `http://localhost:4000`
3. **AI summaries** are generated for complex events (optional)
4. **Dashboard** displays everything in real-time via WebSocket

### Customization

The hooks configuration is in `.claude/settings.json`. You can:
- Disable specific hooks
- Adjust which events get AI summaries
- Change the server URL
- Add custom event processing

## 🚀 Installation Options

### Option 1: Use as GitHub Template 

1. Click **"Use this template"** on [GitHub](https://github.com/albertsikkema/claude-config-template)
2. Create your template repository
3. Clone and use in your projects

### Option 2: Direct Installation

```bash
# Clone the template
git clone https://github.com/albertsikkema/claude-config-template.git

# Navigate to your project
cd /path/to/your-project

# Install
/path/to/claude-config-template/install-helper.sh
```

### Option 3: One-Line Remote Install ⚡ (Recommended)

The easiest way! Downloads, installs, and cleans up automatically:

```bash
# Install everything (recommended)
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash

# Install only Claude configuration
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --claude-only

# Install only thoughts structure
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --thoughts-only

# Preview what will be installed (dry run)
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --dry-run

# Install to specific directory
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- /path/to/project

# Combine options
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --force --claude-only
```

**How it works**: The remote installer downloads the repository, runs the installation with your options, and automatically cleans up temporary files.

## 🎮 Installation Options

```bash
# Install everything (default)
./install-helper.sh

# Install only Claude configuration
./install-helper.sh --claude-only

# Install only thoughts structure
./install-helper.sh --thoughts-only

# Preview what will be installed
./install-helper.sh --dry-run

# Clean reinstall (⚠️ removes all thoughts/ content)
./install-helper.sh --force

# Install to specific directory
./install-helper.sh /path/to/project
```

**Note**:
- The remote installer (`install.sh`) downloads the repository, installs to your current directory, and cleans up automatically
- For manual installation from a cloned repository, use `install-helper.sh`
- The installer automatically updates your project's `.gitignore` to exclude `.claude/`, `thoughts/`, and `claude-helpers/`
- **Default behavior**: `.claude/` is always updated, `thoughts/` preserves existing content and adds missing directories
- **With `--force`**: Completely replaces `thoughts/` directory, removing all plans, research, and project docs

## 📚 Helper Scripts & Documentation

This template includes several utility scripts in the `claude-helpers/` directory:

- **Codebase Indexers**: Generate searchable markdown documentation
  - `index_python.py` - Index Python codebases (functions, classes, models)
  - `index_ts.py` - Index TypeScript/React codebases (components, functions, interfaces)
  - `index_go.py` - Index Go codebases (structs, interfaces, functions)
  - Use via `/index_codebase` slash command
  - **📖 See [docs/README-indexers.md](docs/README-indexers.md) for detailed guide**

- **Documentation Fetcher**: Download LLM-optimized documentation
  - `fetch-docs.py` - Fetch documentation from context7.com
  - Use via `/fetch_technical_docs` slash command
  - **📖 See [docs/README-fetch-docs.md](docs/README-fetch-docs.md) for detailed guide**

- **OpenAPI Fetcher**: Extract API schemas from FastAPI
  - `fetch_openapi.sh` - Fetch OpenAPI/Swagger schemas
  - Auto-invoked via `/index_codebase` when FastAPI detected
  - **📖 See [docs/README-fetch-openapi.md](docs/README-fetch-openapi.md) for detailed guide**

- **Metadata Generator**: Capture development context
  - `spec_metadata.sh` - Generate comprehensive metadata
  - Used in plans, research, and ADRs
  - **📖 See [docs/README-spec-metadata.md](docs/README-spec-metadata.md) for detailed guide**

**📖 Full scripts overview: [claude-helpers/README.md](claude-helpers/README.md)**

## 📚 Complete Development Workflow

This template provides a systematic **Research → Plan → Implement → Rationalize** workflow based on "Faking a Rational Design Process in the AI Era".

**📖 See [WORKFLOW.md](WORKFLOW.md) for the complete guide** covering:

- **Phase 0**: Index Codebase (optional but recommended)
- **Phase 1**: Project Setup (one-time)
- **Phase 2**: Research
- **Phase 3**: Plan
- **Phase 4**: Implement
- **Phase 5**: Validate
- **Phase 6**: Rationalize (MANDATORY)
- **Phase 7**: Commit & PR

### Quick Start Example

```bash
# 1. Index your codebase (optional but makes research faster)
You: /index_codebase

# 2. Document your project (one-time setup)
You: /project Create full docs for my e-commerce platform

# 3. Research before building
You: /research_codebase payment processing flow

# 4. Create implementation plan
You: /create_plan add Stripe payment integration

# 5. Implement the plan
You: /implement_plan thoughts/shared/plans/2025-10-14-stripe-integration.md

# 6. Validate implementation
You: /validate_plan thoughts/shared/plans/2025-10-14-stripe-integration.md

# 7. Rationalize (MANDATORY - updates docs with clean narrative)
You: /rationalize thoughts/shared/plans/2025-10-14-stripe-integration.md

# 8. Commit and create PR
You: /commit
You: /describe_pr
```

**👉 Read [WORKFLOW.md](WORKFLOW.md) for detailed explanations, examples, and best practices.**

## 📝 File Naming Conventions

**Plans & Research**: `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`
```
2025-10-14-oauth-support.md
2025-10-14-ENG-1478-user-tracking.md
```

**Project Documentation**: Ultra-lean 3-file structure
```
thoughts/shared/project/project.md    # Project context (what/why/stack)
thoughts/shared/project/todo.md       # Active work (Must Haves/Should Haves)
thoughts/shared/project/done.md       # Completed work history
```

**ADRs**: Sequential numbering as `NNN-decision-title.md`
```
thoughts/shared/adrs/001-use-optimistic-locking.md
thoughts/shared/adrs/002-cache-invalidation-strategy.md
```

## 🎨 Customization

### Add Your Own Agent

Create `.claude/agents/my-agent.md`:

```markdown
---
name: my-custom-agent
description: What this agent does
model: sonnet
color: blue
---

Your agent instructions here...
```

### Add Custom Command

Create `.claude/commands/my-command.md`:

```markdown
# My Custom Command

Your command instructions here...
```

### Adjust Permissions

Edit `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(command:*)",
      "WebFetch(domain:example.com)"
    ],
    "deny": []
  }
}
```

## 🗑️ Uninstallation

```bash
# Remove configuration (preserves thoughts/)
./uninstall.sh

# Remove only Claude config
./uninstall.sh --claude-only

# Preview what will be removed
./uninstall.sh --dry-run

# Remove everything including thoughts/ (⚠️ deletes your work)
./uninstall.sh --force
```

**Default behavior**: Removes `.claude/` and `claude-helpers/` but **preserves** `thoughts/` directory with your plans, research, and project docs.

**With `--force`**: Removes **everything** including all your work in `thoughts/`.


## 🌟 Key Features Explained

### Research → Plan → Implement → Rationalize Pattern

The core workflow ensures quality and preserves knowledge:

1. **Research**: Understand before building
2. **Plan**: Design before coding
3. **Implement**: Execute with clarity
4. **Rationalize**: Clean up the narrative (see [WORKFLOW.md](WORKFLOW.md))

### Intelligent Agents

Agents work autonomously and can be:
- **Invoked automatically** by Claude Code when needed
- **Requested explicitly** by you
- **Run in parallel** for faster results

### Structured Documentation

Ultra-lean 3-file structure:
- **project.md** - Project context (what/why/stack/constraints)
- **todo.md** - Active work with MoSCoW prioritization (Must Haves/Should Haves)
- **done.md** - Completed work history with full traceability
- **ADRs** - Architecture Decision Records

See the "Ultra-Lean 3-File Documentation Method" section in [WORKFLOW.md](WORKFLOW.md) for methodology details.

## 📖 Real-World Examples

### Example 1: New Feature Development

```
You: /research_codebase I need to add two-factor authentication

Claude uses agents to:
1. Research existing auth code (codebase-analyzer)
2. Find similar implementations (codebase-pattern-finder)
3. Check technical docs (technical-docs-researcher)

Then read and use the created research file to create a plan, implement etc.
```

### Example 2: Understanding Legacy Code

```
You: /research_codebase How does the caching layer work?

Claude spawns parallel agents to:
- Locate cache-related files
- Analyze implementation details
- Document the architecture

Result: Comprehensive research document with file:line references
```

### Example 3: Project Setup

```
You: /project Create complete project documentation

Claude asks about:
- Tech stack
- Team size
- Development phase
- Core features

Result: Full project documentation customized for your needs
```

## 🤝 Contributing

Contributions are welcome from individuals and companies alike! We'd love to see:

- New agents and slash commands
- Improved documentation and examples
- Bug fixes and enhancements
- Installation script improvements
- Templates and workflow ideas

**See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:**
- How to submit contributions
- Agent and command development best practices
- Testing requirements
- Pull request process

For questions or larger contributions, contact: license@albertsikkema.com

## 💡 Tips & Best Practices

1. **Follow the workflow** - See [WORKFLOW.md](WORKFLOW.md) for the complete process
2. **Index first** - Run `/index_codebase` before research for faster results
3. **Research before planning** - Always understand before building
4. **Never skip rationalization** - It preserves knowledge for future AI sessions
5. **Create meaningful ADRs** - Document significant decisions, not everything
6. **Review permissions** - Audit `settings.local.json` regularly

## 📊 Version

Current version: **1.1.0**

## 🆘 Support & Troubleshooting

### Common Issues

**"Unknown slash command: project"**

If the `/project` command isn't recognized after installation:

1. **Restart Claude Code** - Close and reopen the application
2. **Check installation** - Verify `.claude/commands/project.md` exists
3. **Reload configuration** - Use the `/clear` command in Claude Code
4. **Re-install** - Run `./install-helper.sh --force` to ensure files are correct

**Agent not found**

If agents aren't being recognized:
- Verify `.claude/agents/` contains all 11 agent files
- Restart Claude Code
- Check file permissions (files should be readable)

**Git tracking configuration files**

The installer automatically adds `.claude/`, `thoughts/`, and `claude-helpers/` to your `.gitignore`. If you want to track these:
- Edit `.gitignore` and remove the entries you want to track
- Or use `git add -f` to force-add specific files

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/albertsikkema/claude-config-template/issues)
- **Documentation**: [Claude Code Docs](https://docs.claude.com)
- **Template Updates**: Re-run the installer to update `.claude/` and add any new `thoughts/` directories

## 📄 License

MIT License - See LICENSE file for details

## 🎯 What Makes This Special?

Unlike basic Claude Code configurations, this template provides:

✅ **Complete workflow system** - Not just tools, but processes
✅ **Intelligent automation** - Agents that think and research
✅ **Structured knowledge** - Organized documentation system
✅ **Battle-tested patterns** - Proven workflows that work
✅ **Easy to customize** - Extend and adapt to your needs

## 🚦 Getting Started Checklist

After installation:

- [ ] **Restart Claude Code** to load new configuration
- [ ] Verify installation: Check `.claude/` and `thoughts/` directories exist
- [ ] Review `.claude/settings.json` permissions
- [ ] **(Optional)** Start monitoring dashboard: `./start-monitoring.sh`
- [ ] **Read [WORKFLOW.md](WORKFLOW.md)** to understand the complete process
- [ ] Run `/index_codebase` to create searchable indexes (optional but recommended)
- [ ] Run `/project` to document your project (if command not found, see troubleshooting)
- [ ] Follow the workflow: Research → Plan → Implement → Validate → Rationalize → PR
- [ ] Add project-specific agents if needed
- [ ] Share with your team!

---

**Ready to supercharge your development workflow?**

Install now and experience the future of AI-assisted development! 🚀

Made with ❤️ for the Claude Code community
