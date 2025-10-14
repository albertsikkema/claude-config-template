# Claude Code Configuration Template

A powerful, reusable configuration system for [Claude Code](https://claude.com/code) that supercharges your development workflow with custom agents, intelligent slash commands, and structured project documentation.

## 🎯 What's This?

This is a **configuration template** that you install into your projects. It provides:

- **11 specialized AI agents** - Automated research, code analysis, and architecture design
- **8 slash commands** - Streamlined workflows for common tasks
- **Structured documentation system** - Templates and organization for project docs
- **Pre-configured permissions** - Ready-to-use tool access for development

Think of it as a **productivity multiplier** for Claude Code - install once, benefit forever.

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
| `/validate_plan` | Validate implementation plans |
| `/commit` | Create well-formatted git commits |
| `/describe_pr` | Generate comprehensive PR descriptions |
| `/code_reviewer` | Review code quality |

### 📁 Directory Structure

After installation, you'll have:

```
your-project/
├── .claude/
│   ├── agents/              # 11 specialized agents
│   ├── commands/            # 8 slash commands
│   └── settings.local.json  # Pre-configured permissions
│
└── thoughts/
    ├── templates/           # Documentation templates
    │   ├── project.md.template
    │   ├── musthaves.md.template
    │   ├── shouldhaves.md.template
    │   ├── todo.md.template
    │   └── epics.md.template
    │
    └── shared/
        ├── plans/           # Implementation plans
        ├── research/        # Research documents
        └── project/         # Project documentation
            └── epics/       # Epic planning
```

## 🚀 Quick Start

### Option 1: Use as GitHub Template (Recommended)

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
/path/to/claude-config-template/install.sh
```

### Option 3: One-Line Remote Install

```bash
# Install everything
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash

# Install with options
curl -fsSL https://raw.githubusercontent.com/albertsikkema/claude-config-template/main/install.sh | bash -s -- --claude-only
```

## 🎮 Installation Options

```bash
# Install everything (default)
./install.sh

# Install only Claude configuration
./install.sh --claude-only

# Install only thoughts structure
./install.sh --thoughts-only

# Preview what will be installed
./install.sh --dry-run

# Force overwrite existing files
./install.sh --force

# Install to specific directory
./install.sh /path/to/project
```

**Note**: The installer automatically updates your project's `.gitignore` to exclude:
- `.claude/` - Claude Code configuration
- `thoughts/` - Documentation and planning files
- `claude-helpers/` - Helper scripts

If `.gitignore` doesn't exist, it will be created. Existing entries are preserved.

## 📚 How to Use

### 1. Create Project Documentation

Start by documenting your project:

```bash
# Create complete documentation
You: /project Create full documentation for my task management SaaS

# Or create specific docs
You: /project Document my MVP requirements
You: /project Create an epic for user authentication
```

**Result**: Customized documentation in `thoughts/shared/project/`

### 2. Research Your Codebase

Deep dive into your code:

```bash
You: /research_codebase how does authentication work?
```

**Result**: Comprehensive research saved to `thoughts/shared/research/YYYY-MM-DD-topic.md`

### 3. Plan Implementation

Create detailed implementation plans:

```bash
You: /create_plan add OAuth support based on the authentication research
```

**Result**: Interactive planning session → plan saved to `thoughts/shared/plans/YYYY-MM-DD-feature.md`

### 4. Execute the Plan

Implement your approved plan:

```bash
You: /implement_plan thoughts/shared/plans/2025-10-14-oauth-support.md
```

**Result**: Step-by-step implementation with progress tracking

### 5. Commit & Review

Create quality commits and PRs:

```bash
# Create a commit
You: /commit

# Generate PR description
You: /describe_pr

# Review code quality
You: /code_reviewer
```

## 🔄 Complete Workflow Example

Here's a real-world workflow from idea to implementation:

```bash
# 1. Document your project (one-time setup)
You: /project Create full docs for my e-commerce platform

# 2. Research existing implementation
You: /research_codebase payment processing flow

# 3. Create implementation plan
You: /create_plan add Stripe payment integration

# 4. Implement the plan
You: /implement_plan thoughts/shared/plans/2025-10-14-stripe-integration.md

# 5. Review the changes
You: /code_reviewer

# 6. Create commit
You: /commit

# 7. Generate PR description
You: /describe_pr
```

## 📝 File Naming Conventions

**Plans & Research**: `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`
```
2025-10-14-oauth-support.md
2025-10-14-ENG-1478-user-tracking.md
```

**Project Documentation**: Descriptive names
```
thoughts/shared/project/project-overview.md
thoughts/shared/project/mvp-requirements.md
thoughts/shared/project/technical-todos.md
```

**Epics**: Saved in subdirectory as `epic-[name].md`
```
thoughts/shared/project/epics/epic-authentication.md
thoughts/shared/project/epics/epic-payment-processing.md
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

Edit `.claude/settings.local.json`:

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
# Remove everything
./uninstall.sh

# Remove only Claude config
./uninstall.sh --claude-only

# Preview what will be removed
./uninstall.sh --dry-run

# Force removal without prompts
./uninstall.sh --force
```

**⚠️ Warning**: Uninstalling permanently deletes directories. The script will warn you if it finds user-created content (plans, research, project docs).

## 🔧 Pre-Configured Permissions

The template includes pre-approved permissions for:

**Development Tools:**
- pytest (unit, integration tests)
- git operations
- docker & docker-compose
- make & pre-commit hooks
- Python execution

**Documentation Domains:**
- docs.astral.sh
- fastapi.tiangolo.com
- docs.sqlalchemy.org
- github.com
- localhost (testing)
- And more...

**Plus**: Unrestricted WebSearch

## 🌟 Key Features Explained

### Research → Plan → Implement Pattern

The core workflow that ensures quality:

1. **Research**: Understand before building
2. **Plan**: Design before coding
3. **Implement**: Execute with clarity

### Intelligent Agents

Agents work autonomously and can be:
- **Invoked automatically** by Claude Code when needed
- **Requested explicitly** by you
- **Run in parallel** for faster results

### Structured Documentation

Templates help you maintain:
- **Project overview** - Big picture understanding
- **Requirements** - Must-haves vs. should-haves
- **Technical TODOs** - Track technical debt
- **Epics** - Plan major features

## 📖 Real-World Examples

### Example 1: New Feature Development

```
You: I need to add two-factor authentication

Claude uses agents to:
1. Research existing auth code (codebase-analyzer)
2. Find similar implementations (codebase-pattern-finder)
3. Check technical docs (technical-docs-researcher)

Then guides you through:
1. Creating a plan
2. Implementing step-by-step
3. Reviewing the code
4. Committing changes
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

Contributions welcome! To add agents or commands:

1. Fork this repository
2. Add your agent/command files
3. Update documentation
4. Submit a pull request

## 💡 Tips & Best Practices

1. **Start with documentation** - Use `/project` to document your project first
2. **Research before planning** - Always understand before building
3. **Use agents explicitly** - Don't wait for automatic invocation
4. **Keep docs updated** - Update project docs as you evolve
5. **Review permissions** - Audit `settings.local.json` regularly

## 📊 Version

Current version: **1.0.0**

## 🆘 Support & Troubleshooting

### Common Issues

**"Unknown slash command: project"**

If the `/project` command isn't recognized after installation:

1. **Restart Claude Code** - Close and reopen the application
2. **Check installation** - Verify `.claude/commands/project.md` exists
3. **Reload configuration** - Use the `/clear` command in Claude Code
4. **Re-install** - Run `./install.sh --force` to ensure files are correct

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
- **Template Updates**: Pull latest changes and re-run installer with `--force`

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
- [ ] Review `.claude/settings.local.json` permissions
- [ ] Run `/project` to document your project (if command not found, see troubleshooting)
- [ ] Try `/research_codebase` on a feature
- [ ] Explore available agents (agents are invoked automatically or explicitly)
- [ ] Create your first plan with `/create_plan`
- [ ] Add project-specific agents if needed
- [ ] Share with your team!

---

**Ready to supercharge your development workflow?**

Install now and experience the future of AI-assisted development! 🚀

Made with ❤️ for the Claude Code community
