# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [1.2.0] - 2025-10-20

### Added

**Architecture Documentation:**
- `/build_c4_docs` command for automated C4 architecture diagram generation
- C4 model support at 3 levels: System Context, Container, Component
- Dual diagram format support: Mermaid (GitHub-native) + PlantUML (enhanced aesthetics)
- `build_c4_diagrams.py` helper script for rendering PlantUML diagrams to PNG/SVG
- Automatic PlantUML detection with Docker fallback support
- Comprehensive C4 diagrams documentation (791 lines) covering usage, installation, and methodology
- New directory: `thoughts/shared/research/c4-diagrams-plantuml/` for PlantUML diagram output
- New directory: `thoughts/shared/rationalization/` for ephemeral working documents during rationalization

### Changed

**Documentation:**
- Updated slash command count from 13 to 14 in README.md and CLAUDE.md
- Enhanced directory structure documentation with C4 diagram paths
- Added C4 diagram references to helper scripts documentation

---

## [1.1.0] - 2025-10-20

### Added

**Codebase Intelligence & Documentation:**
- Automated codebase indexing system for Python, TypeScript, and Go with LLM-optimized output
- `/fetch_technical_docs` command for intelligent documentation fetching from context7.com
- Comprehensive helper script documentation (40KB+) covering all utilities
- `technical-docs-researcher` agent for searching stored technical documentation
- `thoughts-locator` and `thoughts-analyzer` agents for document discovery and deep analysis

**Quality Assurance & Validation:**
- `plan-validator` agent for automated implementation verification against plans
- Automatic validation integrated into `/implement_plan` workflow
- `/security` command with comprehensive 18-category security analysis (language-agnostic)
- Security analysis covers: injection, auth, crypto, dependencies, data, APIs, and more

**Project Documentation (Ultra-Lean 3-File Structure):**
- New streamlined documentation approach: `project.md`, `todo.md`, `done.md`
- `project.md`: Project context, stack, metrics, constraints, architecture
- `todo.md`: Active work with Must Haves/Should Haves, blocking/dependency tracking
- `done.md`: Completed work history with traceability to plans/ADRs/PRs
- Inline blocking syntax: `[BLOCKED]` prefix with blocker descriptions
- Dependency management via ordering and `(requires:)` mentions
- Architecture Decision Records (ADR) template with sequential numbering

**Deployment & Operations:**
- `/deploy` command for automated deployment workflow (7-step process)
- CHANGELOG template following Keep a Changelog standard
- Version bump automation with multi-language support
- Build/test automation with project type detection
- Release preparation with platform-specific instructions

**Implementation & Rationalization:**
- `/rationalize` command following Parnas & Clements methodology
- Updates plans to reflect actual implementation (not discovery process)
- Creates ADRs for significant decisions during rationalization
- Updates CLAUDE.md with new patterns and conventions
- Synchronizes project documentation (project.md, todo.md, done.md)
- Documents rejected alternatives to prevent re-exploration

**Development Workflow:**
- `/code_reviewer` command for code quality analysis
- Enhanced `/create_plan` with better interactive planning
- Improved `/research_codebase` with parallel agent orchestration
- Research → Plan → Implement → Rationalize workflow pattern

### Changed

**Architecture & Organization:**
- Transitioned from 4-file to 3-file project documentation structure
- Redistributed `codebase-researcher` functionality to specialized agents
- Enhanced agent system with better task delegation and parallelism
- Improved file naming conventions (YYYY-MM-DD format for plans/research)

**Workflow Integration:**
- `/implement_plan` now includes automatic validation at completion
- Validation findings addressed before plan completion (implementation or documentation)
- `/validate_plan` simplified to standalone thin wrapper for plan-validator agent
- Rationalization made mandatory step in implementation workflow

**Documentation & Instructions:**
- Expanded CLAUDE.md with complete workflow patterns and examples
- Updated WORKFLOW.md with ultra-lean documentation methodology
- Enhanced README.md with better command descriptions and examples
- Added comprehensive usage guides for all helper scripts

### Removed

**Agents:**
- `codebase-researcher` agent (functionality distributed to `codebase-locator`, `codebase-analyzer`, `codebase-pattern-finder`)

**Documentation Structure:**
- Old 4-file project documentation approach (epics.md, musthaves.md, shouldhaves.md, todo.md)
- Replaced with streamlined 3-file structure for better maintainability

### Fixed
- Improved error handling in indexing scripts
- Enhanced documentation fetching reliability
- Better validation reporting in plan-validator
- More robust file detection in deployment workflow

---

## [1.0.0] - 2025-10-14

### Added
- Initial release of Claude Code configuration template
- 11 specialized agents for different tasks
- 13 slash commands for common workflows
- Pre-configured permissions for development tools
- Thoughts directory structure for documentation and planning
- Installation and uninstallation scripts

[Unreleased]: https://github.com/albertsikkema/claude-config-template/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/albertsikkema/claude-config-template/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/albertsikkema/claude-config-template/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/albertsikkema/claude-config-template/releases/tag/v1.0.0
