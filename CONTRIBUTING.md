# Contributing to Claude Code Configuration Template

Thank you for your interest in contributing! This project welcomes contributions from individuals and companies alike. Whether you're fixing a bug, adding a new agent, or improving documentation, your help is appreciated.

## 🎯 Ways to Contribute

### 1. **Report Issues**
- Found a bug? [Open an issue](https://github.com/albertsikkema/claude-config-template/issues)
- Have a feature request? Let us know!
- Experiencing installation problems? We want to help!

### 2. **Improve Documentation**
- Fix typos or clarify instructions
- Add examples or use cases
- Improve README or command documentation
- Write tutorials or guides

### 3. **Create New Agents**
- Design specialized agents for specific tasks
- Share your custom agents with the community
- Improve existing agent prompts and capabilities

### 4. **Add Slash Commands**
- Create new workflow commands
- Enhance existing command functionality
- Share your productivity shortcuts

### 5. **Enhance Installation Scripts**
- Improve cross-platform compatibility
- Add new installation options
- Fix bugs in install/uninstall scripts

### 6. **Share Templates**
- Create new documentation templates
- Improve existing templates
- Add language-specific or domain-specific templates

## 🚀 Getting Started

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/claude-config-template.git
cd claude-config-template
```

### Make Your Changes

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the guidelines below

3. Test your changes thoroughly

### Submit a Pull Request

1. Commit your changes:
   ```bash
   git add .
   git commit -m "Add: brief description of your changes"
   ```

2. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Open a Pull Request on GitHub with:
   - Clear description of what you changed and why
   - Any relevant issue numbers
   - Screenshots or examples if applicable

## 📝 Contribution Guidelines

### Agents (.claude/agents/*.md)

**💡 Pro Tip: Use Claude Code to Create Agents**

The best way to create a new agent is to use the `/agent` command or ask Claude Code directly!

**Option 1: Use the `/agent` command (Easiest)**

```
You: /agent
```

Then follow the interactive instructions to create your agent. The command will guide you through the process step-by-step.

**Option 2: Ask Claude Code directly**

1. **Describe what you want the agent to do:**
   ```
   You: I want to create an agent that generates unit tests for Python functions.
        It should analyze the function, identify edge cases, and write pytest tests.
   ```

2. **Ask Claude Code to create the agent file:**
   ```
   You: Create a new agent file at .claude/agents/python-test-generator.md
        that implements this functionality.
   ```

3. **Claude Code will generate the agent with:**
   - Proper frontmatter structure
   - Comprehensive instructions
   - Examples and edge cases
   - Best practices built in

4. **Test and adapt:**
   - Use the agent in real scenarios
   - Iterate on the instructions based on results
   - Refine the prompts and examples
   - Ask Claude Code to help improve it

5. **Review existing agents for inspiration:**
   - Look at `.claude/agents/*.md` in this repository
   - Study the structure and style
   - Borrow patterns that work well

This meta-approach (using Claude Code to build Claude Code tools) is highly effective!

---

**Agent Guidelines:**

When creating or modifying agents:

- **Use clear, descriptive names** (e.g., `test-generator.md`, not `tester.md`)
- **Include frontmatter** with name, description, model, and color
- **Write comprehensive instructions** that Claude can follow independently
- **Provide examples** of when and how to use the agent
- **Test thoroughly** before submitting

Example agent structure:
```markdown
---
name: my-agent
description: Brief description of what this agent does
model: sonnet
color: blue
---

Agent instructions here...
```

### Slash Commands (.claude/commands/*.md)

**💡 Pro Tip: Use Claude Code to Create Commands Too!**

Just like with agents, ask Claude Code to help create slash commands:

```
You: Create a new slash command /format-json that reads JSON files,
     formats them with proper indentation, and validates the structure.
     Save it to .claude/commands/format-json.md
```

Claude Code will generate the command with proper step-by-step instructions. Then test it, refine it, and submit!

---

**Command Guidelines:**

When creating or modifying commands:

- **Use clear command names** that indicate the action (e.g., `/format`, `/analyze`)
- **Write step-by-step instructions** for Claude to follow
- **Include examples** of expected inputs and outputs
- **Document any dependencies** (e.g., specific tools or files needed)
- **Test the command** in multiple scenarios

### Documentation Templates (thoughts/templates/*.template)

When creating templates:

- **Use `.template` extension** so installer can process them
- **Include clear placeholder text** in `[brackets]`
- **Provide helpful comments** or sections
- **Make them generic** and broadly applicable
- **Test with actual projects** before submitting

### Installation Scripts

When modifying scripts:

- **Test on multiple platforms** (macOS, Linux, Windows with WSL)
- **Maintain backward compatibility** when possible
- **Update documentation** to reflect script changes
- **Add error handling** for edge cases
- **Include helpful error messages**

### Documentation

- **Keep it clear and concise**
- **Use proper Markdown formatting**
- **Add screenshots or examples** when helpful
- **Update the README** if you add major features
- **Check for broken links**

## 🧪 Testing Your Changes

Before submitting a PR:

1. **Test installation**:
   ```bash
   # In a test directory
   ./install-helper.sh --dry-run
   ./install-helper.sh
   ```

2. **Test your agents/commands**:
   - Actually use them in Claude Code
   - Try edge cases and error scenarios
   - Verify they work as documented

3. **Test uninstallation**:
   ```bash
   ./uninstall.sh --dry-run
   ```

4. **Check documentation**:
   - All links work
   - Examples are accurate
   - Formatting looks correct

## 💡 Contribution Ideas

Not sure what to contribute? Here are some ideas:

- **Language-specific agents** (e.g., Python formatter, Rust analyzer)
- **Framework-specific commands** (e.g., /django-model, /react-component)
- **Testing utilities** (e.g., test generation, coverage analysis)
- **Documentation agents** (e.g., API doc generator, README creator)
- **Code review agents** (e.g., security scanner, performance analyzer)
- **Project templates** (e.g., microservice project, mobile app project)
- **Integration guides** (e.g., CI/CD setup, deployment automation)

## 🤝 Community Guidelines

- **Be respectful** and constructive in discussions
- **Help others** who are learning or contributing
- **Give credit** where credit is due
- **Follow the MIT License** terms
- **Keep it professional** and **inclusive**

## 📧 Questions?

- **General questions**: [Open a discussion](https://github.com/albertsikkema/claude-config-template/discussions)
- **Bug reports**: [Open an issue](https://github.com/albertsikkema/claude-config-template/issues)
- **Private inquiries**: license@albertsikkema.com

## 🏢 Company Contributions

If your company uses and benefits from this project, consider:

- **Dedicating developer time** to contribute improvements
- **Sharing internal agents/commands** that could benefit others
- **Sponsoring feature development**
- **Providing feedback** from production use
- **Contributing documentation** or examples

Contact license@albertsikkema.com to discuss larger contributions or collaboration.

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for making this project better! 🚀
