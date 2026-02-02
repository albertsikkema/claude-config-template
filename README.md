# Claude Code Configuration Template

> **⚠️ ALPHA STATUS**
>
> Features added since January 1st, 2026 are **highly experimental and in alpha stage**. They may contain bugs, have breaking changes, or be incomplete. Use at your own risk and expect instability.
>
> Feedback and bug reports are welcome!

---

A powerful, reusable configuration system for [Claude Code](https://claude.com/code) that supercharges your development workflow with custom agents, intelligent slash commands, and structured project documentation.

## ⚡ Quick Install

**First time installation or update (preserves your work):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash
```

**Install from a specific branch:**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch orchestrator-agent
```

**Clean reinstall (⚠️ overwrites important stuff):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --force
```

**Clean reinstall from a specific branch:**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --branch orchestrator-agent --force
```

> **Note**: Always use `/main/install.sh` in the URL. The `--branch` argument specifies which branch's content to actually install.

## 🗑️ Quick Uninstall

**Remove configuration (preserves memories/):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/uninstall.sh | bash
```

**Remove everything including memories/ (⚠️ overwrites important stuff):**
```bash
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/uninstall.sh | bash -s -- --force
```

---

## 🎯 What's This?

This is a **configuration template** that you install into your projects. It provides:

- **Complete development workflow** - Research → Plan → Implement → Cleanup → Deploy ([see WORKFLOW.md](WORKFLOW.md))
- **12 specialized AI agents** - Automated research, code analysis, and architecture design
- **14 slash commands** - Streamlined workflows for common tasks (including C4 architecture diagrams and deployment automation)
- **108 security rules** - Language-specific secure coding guidance from [Project Codeguard](https://github.com/project-codeguard/rules)
- **Structured documentation system** - Templates and organization for project docs
- **Pre-configured permissions** - Ready-to-use tool access for development

Think of it as a **productivity multiplier** for Claude Code - install once, benefit forever.

**📖 New to this template? Start with [WORKFLOW.md](WORKFLOW.md) for the complete development workflow guide.**

Partly based on/ inspired by:
- https://github.com/humanlayer/humanlayer
- https://github.com/Wirasm/PRPs-agentic-eng

Security rules integration:
- https://github.com/project-codeguard/rules (108 OWASP-aligned security rules)

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
- `best-practices-researcher` - Search documented best practices from previous implementations
- `technical-docs-researcher` - Search technical documentation for libraries and frameworks
- `memories-analyzer` - Deep dive into your memories directory
- `memories-locator` - Find relevant documents

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
| `/cleanup` | Document best practices and clean up ephemeral artifacts |
| `/build_c4_docs` | Generate C4 architecture diagrams (System Context, Container, Component) |
| `/commit` | Create well-formatted git commits |
| `/pr` | Generate comprehensive PR descriptions |
| `/code_reviewer` | Review code quality |
| `/security` | Comprehensive security analysis with Codeguard rules |
| `/deploy` | Automated deployment preparation (version, changelog, build, release) |
| `/fetch_technical_docs` | Fetch LLM-optimized documentation from context7.com |
| `/index_codebase` | Index Python/TypeScript/Go/C++ codebases |

### 📁 Directory Structure

After installation, you'll have:

```
your-project/
├── .claude/
│   ├── agents/              # 12 specialized agents
│   ├── commands/            # 14 slash commands
│   ├── helpers/             # Utility scripts
│   │   ├── README.md            # Scripts overview
│   │   ├── index_python.py      # Python codebase indexer
│   │   ├── index_js_ts.py       # JavaScript/TypeScript codebase indexer
│   │   ├── index_go.py          # Go codebase indexer
│   │   ├── build_c4_diagrams.py # C4 PlantUML diagram builder
│   │   ├── fetch-docs.py        # Documentation fetcher
│   │   ├── fetch_openapi.sh     # OpenAPI schema fetcher
│   │   └── spec_metadata.sh     # Metadata generator
│   └── settings.json        # Configuration and hooks
│
├── docs/                    # Helper script documentation
│   ├── README-fetch-docs.md     # Documentation fetcher guide
│   ├── README-indexers.md       # Codebase indexers guide
│   ├── README-c4-diagrams.md    # C4 architecture diagrams guide
│   ├── README-fetch-openapi.md  # OpenAPI fetcher guide
│   └── README-spec-metadata.md  # Metadata generator guide
│
└── memories/
    ├── templates/           # Documentation templates
    │   ├── project.md.template  # Project context template
    │   ├── todo.md.template     # Active work tracking template
    │   ├── done.md.template     # Completed work template
    │   ├── adr.md.template      # Architecture Decision Records template
    │   └── changelog.md.template # Changelog template
    │
    ├── best_practices/      # Best practices documentation from implementations
    ├── technical_docs/      # Technical documentation storage
    ├── security_rules/      # Project Codeguard security rules (108 rules)
    │   ├── core/            # 22 Cisco-curated core security rules
    │   └── owasp/           # 86 OWASP-based security rules
    │
    └── shared/
        ├── plans/           # Implementation plans (deleted after cleanup)
        ├── research/        # Research documents (deleted after cleanup)
        ├── rationalization/ # Ephemeral working docs (deleted after cleanup)
        └── project/         # Project documentation (3-file structure)
```

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

# Install only memories structure
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --memories-only

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

# Install only memories structure
./install-helper.sh --memories-only

# Preview what will be installed
./install-helper.sh --dry-run

# Clean reinstall (⚠️ removes all memories/ content)
./install-helper.sh --force

# Install to specific directory
./install-helper.sh /path/to/project
```

**Note**:
- The remote installer (`install.sh`) downloads the repository, installs to your current directory, and cleans up automatically
- For manual installation from a cloned repository, use `install-helper.sh`
- The installer automatically updates your project's `.gitignore` to exclude `.claude/` and `memories/`
- **Default behavior**: `.claude/` is always updated, `memories/` preserves existing content and adds missing directories
- **With `--force`**: Completely replaces `memories/` directory, removing all plans, research, and project docs

## 📚 Helper Scripts & Documentation

This template includes several utility scripts in the `.claude/helpers/` directory:

- **Codebase Indexers**: Generate searchable markdown documentation
  - `index_python.py` - Index Python codebases (functions, classes, models)
  - `index_js_ts.py` - Index JavaScript/TypeScript/React codebases (components, functions, interfaces)
  - `index_go.py` - Index Go codebases (structs, interfaces, functions)
  - `index_cpp.py` - Index C/C++ codebases (classes, structs, functions, enums)
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

- **Orchestrator Agent**: Automate the full Claude Code workflow
  - `orchestrator.py` - Runs index → refine → docs → research → plan → implement → review → cleanup
  - Single-file script with `uv run` support

  **Commands:**
  ```bash
  # Full automated flow (non-interactive except commit)
  uv run .claude/helpers/orchestrator.py "Add user authentication"

  # Plan phase only (interactive planning session)
  uv run .claude/helpers/orchestrator.py --phase plan "Add user authentication"

  # Plan phase, skip query refinement (interactive planning only)
  uv run .claude/helpers/orchestrator.py --phase plan --no-refine "Add user authentication"

  # Implement phase (interactive code review)
  uv run .claude/helpers/orchestrator.py --phase implement memories/shared/plans/2026-02-01-feature.md

  # Cleanup phase (interactive commit)
  uv run .claude/helpers/orchestrator.py --phase cleanup memories/shared/plans/2026-02-01-feature.md

  # Cleanup with research/review files
  uv run .claude/helpers/orchestrator.py --phase cleanup memories/shared/plans/2026-02-01-feature.md \
    --research memories/shared/research/2026-02-01-research.md \
    --review memories/shared/reviews/2026-02-01-review.md
  ```

  **Aliases (add to ~/.zshrc or ~/.bashrc):**
  ```bash
  alias orch='uv run .claude/helpers/orchestrator.py'
  alias orch-plan='uv run .claude/helpers/orchestrator.py --phase plan'
  alias orch-impl='uv run .claude/helpers/orchestrator.py --phase implement'
  alias orch-clean='uv run .claude/helpers/orchestrator.py --phase cleanup'
  ```

  Then use:
  ```bash
  orch "Add user authentication"           # Full flow (automated)
  orch-plan "Add user authentication"      # Plan only (interactive)
  orch-impl memories/shared/plans/xxx.md   # Implement (interactive review)
  orch-clean memories/shared/plans/xxx.md  # Cleanup (interactive commit)
  ```

**📖 Full scripts overview: [.claude/helpers/README.md](.claude/helpers/README.md)**

## 📚 Complete Development Workflow

This template provides a systematic **Research → Plan → Implement → Cleanup** workflow based on "Faking a Rational Design Process in the AI Era".

**📖 See [WORKFLOW.md](WORKFLOW.md) for the complete guide** covering:

- **Phase 0**: Index Codebase (optional but recommended)
- **Phase 1**: Project Setup (one-time)
- **Phase 2**: Research
- **Phase 3**: Plan
- **Phase 4**: Implement
- **Phase 5**: Validate
- **Phase 6**: Cleanup (MANDATORY - documents best practices, removes ephemeral artifacts)
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
You: /implement_plan memories/shared/plans/2025-10-14-stripe-integration.md

# 6. Validate implementation
You: /validate_plan memories/shared/plans/2025-10-14-stripe-integration.md

# 7. Cleanup (MANDATORY - documents best practices, removes artifacts)
You: /cleanup memories/shared/plans/2025-10-14-stripe-integration.md

# 8. Commit and create PR
You: /commit
You: /pr
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
memories/shared/project/project.md    # Project context (what/why/stack)
memories/shared/project/todo.md       # Active work (Must Haves/Should Haves)
memories/shared/project/done.md       # Completed work history
```

**Best Practices**: Category-based naming as `[category]-[topic].md`
```
memories/best_practices/authentication-oauth-patterns.md
memories/best_practices/database-transaction-handling.md
memories/best_practices/api-error-handling.md
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
# Remove configuration (preserves memories/)
./uninstall.sh

# Remove only Claude config
./uninstall.sh --claude-only

# Preview what will be removed
./uninstall.sh --dry-run

# Remove everything including memories/ (⚠️ deletes your work)
./uninstall.sh --force
```

**Default behavior**: Removes `.claude/` but **preserves** `memories/` directory with your plans, research, and project docs.

**With `--force`**: Removes **everything** including all your work in `memories/`.

## 🔄 Migration Notes

### Upgrading from versions with `claude-helpers/`

**What changed**: The `claude-helpers/` directory has been moved to `.claude/helpers/`.

**Why**: This change consolidates all Claude Code configuration into a single `.claude/` directory, creating a cleaner and more logical project structure. Previously, helper scripts lived in a separate top-level directory, but now everything related to Claude Code (agents, commands, helpers, and settings) is unified under `.claude/`.

**If you're upgrading from an older installation**:

1. **Remove the old directory** (if it still exists):
   ```bash
   rm -rf claude-helpers/
   ```

2. **Update your `.gitignore`** - remove the `claude-helpers/` entry if present (it's no longer needed since `.claude/` covers everything)

3. **Update any shell aliases** you may have created:
   ```bash
   # Old aliases (update these)
   alias orch='uv run claude-helpers/orchestrator.py'

   # New aliases
   alias orch='uv run .claude/helpers/orchestrator.py'
   ```

4. **Re-run the installer** to get the new structure:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash
   ```

## 🌟 Key Features Explained

### Project Codeguard Security Integration

The `/security` command integrates **108 comprehensive security rules** from [Project Codeguard](https://github.com/project-codeguard/rules):

- **22 core rules** - Authentication, input validation, authorization, cryptography, etc.
- **86 OWASP rules** - SQL injection, XSS, CSRF, session management, etc.
- **Language-specific guidance** - Python, JavaScript, Go, Java, C, and more
- **Code examples** - Safe implementations and secure coding patterns
- **Automatic loading** - Rules filtered by your project's detected technology stack

When you run `/security`, it automatically:
1. Detects your languages and frameworks
2. Loads relevant Codeguard rules from `memories/security_rules/`
3. Analyzes your code against 18 security areas + Codeguard patterns
4. Generates reports with rule references and recommendations

**Source**: Curated by Cisco and aligned with OWASP best practices.

### Security Hooks

The template includes pre-configured security hooks that protect against dangerous operations:

**UserPromptSubmit Hook** (`user_prompt_submit.py`)
Blocks user prompts containing sensitive data:
- AWS Access Keys (`AKIA...`)
- OpenAI/Anthropic API keys (`sk-...`)
- GitHub tokens (`ghp_`, `gho_`, `github_pat_`)
- Slack tokens (`xoxb-`, `xoxp-`)
- Private keys (RSA, SSH, PGP)

**PreToolUse Hook** (`pre_tool_use.py`)
Blocks dangerous tool operations:

| Category | Blocked Patterns |
|----------|------------------|
| **Destructive commands** | `rm -rf`, fork bombs, `dd` to devices |
| **Dangerous git** | All pushes to main (feature branches allowed), force push, `reset --hard`, `clean -fd` |
| **Sensitive files** | `.env`, `.pem`, `.key`, SSH keys, credentials |
| **Path traversal** | `..` in paths, escaping project directory |

**How it works:**
- Hooks run automatically before each operation
- Exit code `2` blocks the operation and shows error to Claude
- All paths are properly quoted to handle spaces
- Timeouts prevent hung operations

**Customizing security rules:**
Edit `.claude/hooks/pre_tool_use.py` to add/remove patterns:
```python
# Add custom sensitive file patterns
sensitive_patterns = [
    (r'\.pem$', 'PEM certificate/key file'),
    (r'my-custom-secrets', 'Custom secrets file'),  # Add your own
]
```

**Note**: Security hooks cannot be bypassed by Claude - they run at the system level before any tool executes.

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_AUDIO_ENABLED` | `0` | Set to `1` to enable audio notifications on session end, task completion, and when Claude needs input |
| `CLAUDE_HOOKS_DEBUG` | `0` | Set to `1` to enable debug logging for troubleshooting hooks |

```bash
# Enable audio notifications
export CLAUDE_AUDIO_ENABLED=1

# Enable debug logging (shows [DEBUG] messages in stderr)
export CLAUDE_HOOKS_DEBUG=1
```

### Research → Plan → Implement → Cleanup Pattern

The core workflow ensures quality and preserves knowledge:

1. **Research**: Understand before building (spawns parallel agents, documents findings)
2. **Plan**: Design before coding (interactive planning with user)
3. **Implement**: Execute with clarity (step-by-step with validation)
4. **Cleanup**: Document best practices and remove ephemeral artifacts (see [WORKFLOW.md](WORKFLOW.md))

### Intelligent Agents

Agents work autonomously and can be:
- **Invoked automatically** by Claude Code when needed
- **Requested explicitly** by you
- **Run in parallel** for faster results

### Structured Documentation

Ultra-lean 3-file structure + best practices:
- **project.md** - Project context (what/why/stack/constraints)
- **todo.md** - Active work with MoSCoW prioritization (Must Haves/Should Haves)
- **done.md** - Completed work history with full traceability
- **best_practices/** - Documented patterns, decisions, and lessons learned from implementations

See the "Ultra-Lean 3-File Documentation Method" section in [WORKFLOW.md](WORKFLOW.md) for methodology details.

## 📖 Real-World Examples

### Example 1: New Feature Development

```
You: /research_codebase I need to add two-factor authentication

Claude uses agents to:
1. Research existing auth code (codebase-analyzer)
2. Find similar implementations (codebase-pattern-finder)
3. Check best practices (best-practices-researcher)
4. Check technical docs (technical-docs-researcher)

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
4. **Never skip cleanup** - It documents best practices and removes clutter for future AI sessions
5. **Document best practices** - Capture lessons learned, not just decisions
6. **Review permissions** - Audit `settings.local.json` regularly

## 📊 Version

Current version: **1.4.0**

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

The installer automatically adds `.claude/`, `memories/`, and `.claude/helpers/` to your `.gitignore`. If you want to track these:
- Edit `.gitignore` and remove the entries you want to track
- Or use `git add -f` to force-add specific files

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/albertsikkema/claude-config-template/issues)
- **Documentation**: [Claude Code Docs](https://docs.claude.com)
- **Template Updates**: Re-run the installer to update `.claude/` and add any new `memories/` directories

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
- [ ] Verify installation: Check `.claude/` and `memories/` directories exist
- [ ] Review `.claude/settings.json` permissions
- [ ] **Read [WORKFLOW.md](WORKFLOW.md)** to understand the complete process
- [ ] Run `/index_codebase` to create searchable indexes (optional but recommended)
- [ ] Run `/project` to document your project (if command not found, see troubleshooting)
- [ ] Follow the workflow: Research → Plan → Implement → Validate → Cleanup → PR
- [ ] Add project-specific agents if needed
- [ ] Share with your team!

---

**Ready to supercharge your development workflow?**

Install now and experience the future of AI-assisted development! 🚀

Made with ❤️ for the Claude Code community
