# Claude Code Configuration Template

A reusable configuration template for [Claude Code](https://claude.com/code) that includes custom agents, slash commands, and a structured thoughts directory for documentation and planning.

## 📦 What's Included

### `.claude/` Configuration

**Agents** (10 custom agents):
- `codebase-analyzer.md` - Analyzes HOW code works with detailed implementation flow
- `codebase-locator.md` - Finds WHERE code and features live in the codebase
- `codebase-pattern-finder.md` - Discovers similar implementations and usage patterns
- `codebase-researcher.md` - Comprehensive codebase investigations
- `plan-implementer.md` - Executes approved technical plans
- `system-architect.md` - Designs system architectures and evaluates patterns
- `technical-docs-researcher.md` - Researches technical documentation
- `thoughts-analyzer.md` - Deep dives into thoughts directory content
- `thoughts-locator.md` - Discovers relevant documents in thoughts/
- `web-search-researcher.md` - Researches information from the web

**Commands** (17 slash commands):
- `/code_reviewer` - Reviews code quality and suggests improvements
- `/commit` - Creates well-formatted git commits
- `/create_plan` - Interactive implementation plan creation
- `/create_plan_generic` - Generic planning workflow
- `/create_worktree` - Creates git worktrees for parallel development
- `/debug` - Debugging assistance
- `/describe_pr` - Generates comprehensive PR descriptions
- `/founder_mode` - High-level strategic thinking
- `/implement_plan` - Executes implementation plans
- `/linear` - Linear ticket integration
- `/local_review` - Local code review workflow
- `/ralph_impl`, `/ralph_plan`, `/ralph_research` - Ralph-specific workflows
- `/research_codebase`, `/research_codebase_generic` - Codebase investigation
- `/validate_plan` - Validates implementation plans

**Settings**:
- `settings.local.json` - Pre-configured permissions for common tools and domains

### `thoughts/` Structure

A structured directory for documentation and planning:

```
thoughts/
├── docs/                      # Project documentation
│   ├── epics.md.template     # Epic planning template
│   ├── musthaves.md.template # Must-have features
│   ├── project.md.template   # Project overview
│   ├── shouldhaves.md.template # Should-have features
│   └── todo.md.template      # Todo tracking
└── shared/
    ├── plans/                # Implementation plans (dated)
    └── research/             # Research documents (dated)
```

## 🚀 Installation

### Quick Install

Install in your current project directory:

```bash
# Clone or download this repository first
git clone <your-repo-url> /path/to/claude-config-template

# Navigate to your project
cd /path/to/your-project

# Run the installer
/path/to/claude-config-template/install.sh
```

### Installation Options

```bash
# Install everything (default)
./install.sh

# Install only Claude configuration (.claude/)
./install.sh --claude-only

# Install only thoughts structure
./install.sh --thoughts-only

# Preview what will be installed (dry run)
./install.sh --dry-run

# Force overwrite existing files
./install.sh --force

# Install in a specific directory
./install.sh /path/to/project
```

### One-Line Remote Install

If hosted on GitHub, you can install directly:

```bash
# Install from GitHub (replace with your repo URL)
curl -fsSL https://raw.githubusercontent.com/username/repo/main/install.sh | bash

# Or with options
curl -fsSL https://raw.githubusercontent.com/username/repo/main/install.sh | bash -s -- --claude-only
```

## 🗑️ Uninstallation

Remove the configuration from your project:

```bash
# Remove everything
./uninstall.sh

# Remove only Claude configuration
./uninstall.sh --claude-only

# Remove only thoughts structure
./uninstall.sh --thoughts-only

# Preview what will be removed
./uninstall.sh --dry-run

# Force removal without prompts
./uninstall.sh --force
```

**Warning**: Uninstalling will permanently delete the `.claude/` and/or `thoughts/` directories. Use `--dry-run` first to preview changes!

## 📖 Usage Guide

### After Installation

1. **Review settings**:
   ```bash
   cat .claude/settings.local.json
   ```
   Adjust permissions as needed for your project.

2. **Explore agents**:
   ```bash
   ls .claude/agents/
   ```
   Each agent is a specialized tool for different tasks.

3. **Try slash commands**:
   Open Claude Code and type `/` to see available commands.

4. **Customize documentation**:
   ```bash
   cd thoughts/docs
   # Edit the template files for your project
   ```

### Using Agents

Agents are invoked automatically by Claude Code when appropriate. You can also explicitly request them:

```
"Use the codebase-locator agent to find authentication code"
"Research this with the web-search-researcher agent"
```

### Using Slash Commands

Type `/` in Claude Code to see all available commands:

- `/create_plan` - Start planning a new feature
- `/implement_plan thoughts/shared/plans/2025-10-14-my-feature.md` - Implement a plan
- `/research_codebase` - Deep dive into codebase
- `/commit` - Create a well-formatted commit

### Thoughts Directory Workflow

**Planning workflow**:
1. Research: `/research_codebase` → saves to `thoughts/shared/research/`
2. Plan: `/create_plan` → saves to `thoughts/shared/plans/`
3. Implement: `/implement_plan` → executes the plan
4. Document: Update `thoughts/docs/` with learnings

**File naming conventions**:
- Plans: `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`
- Research: Same format as plans
- Templates: Remove `.template` suffix when customizing

## 🎨 Customization

### Adding Your Own Agents

Create a new file in `.claude/agents/`:

```markdown
---
name: my-custom-agent
description: What this agent does
model: sonnet
color: blue
---

Your agent instructions here...
```

### Adding Custom Commands

Create a new file in `.claude/commands/`:

```markdown
# My Custom Command

Your command instructions here...
```

### Modifying Settings

Edit `.claude/settings.local.json` to add/remove permissions:

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

## 🔄 Updating

To update your installation with the latest configuration:

1. Pull the latest changes from this repository
2. Re-run the installer with `--force`:
   ```bash
   ./install.sh --force
   ```

**Note**: This will overwrite your customizations. Consider backing up your changes first.

## 📚 Examples

### Example 1: Research then Plan

```bash
# Research authentication in your codebase
You: "/research_codebase authentication system"

# Create a plan to improve it
You: "/create_plan based on the research, let's add OAuth support"

# Implement the plan
You: "/implement_plan thoughts/shared/plans/2025-10-14-oauth-support.md"
```

### Example 2: Using Agents Directly

```
You: "Use codebase-locator to find all database models"

You: "Use codebase-pattern-finder to show me how we handle errors"

You: "Use system-architect to design a caching layer"
```

### Example 3: Documentation Workflow

```bash
# Start with project template
cp thoughts/docs/project.md.template thoughts/docs/project.md

# Fill in your project details
vim thoughts/docs/project.md

# Track features
cp thoughts/docs/musthaves.md.template thoughts/docs/musthaves.md
vim thoughts/docs/musthaves.md
```

## 🤝 Contributing

Contributions are welcome! To add new agents or commands:

1. Fork this repository
2. Add your agent/command files
3. Update this README
4. Submit a pull request

## 📝 License

[Add your license here]

## 🆘 Support

Issues and questions:
- Open an issue on GitHub
- Check [Claude Code documentation](https://docs.claude.com)

## 🎯 Best Practices

1. **Don't commit secrets**: Never add API keys or passwords to configuration files
2. **Customize for your project**: The templates are starting points - adapt them
3. **Use version control**: Commit your customized configuration
4. **Document your changes**: Update thoughts/docs/ as your project evolves
5. **Review permissions**: Regularly audit settings.local.json for security

## 📊 Version

Current version: 1.0.0

## 🗺️ Roadmap

- [ ] Add more agent templates
- [ ] Create interactive configuration wizard
- [ ] Add language-specific command packs
- [ ] Integration with Linear/JIRA
- [ ] Automated updates via git

---

Made with ❤️ for the Claude Code community
