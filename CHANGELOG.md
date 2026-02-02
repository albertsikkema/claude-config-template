# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [1.4.0] - 2025-11-05

### Added

**Security:**
- Project Codeguard integration with 108 comprehensive security rules (22 core + 86 OWASP-based)
- Language-specific secure coding guidance for Python, JavaScript, Go, Java, C, and more
- Framework-specific security patterns (Django, FastAPI, Node.js, Laravel, Ruby on Rails, etc.)
- Automatic rule loading in `/security` command based on detected technology stack
- Security analysis reports now include Codeguard rule references with file paths

**Documentation:**
- New directory: `memories/security_rules/` with `core/` and `owasp/` subdirectories
- Project Codeguard Security Integration section in README
- Security workflow documentation in CLAUDE.md
- Automatic CLAUDE.md updates after codebase indexing

### Changed

**Codebase Analysis:**
- `codebase-analyzer` is now truly language-agnostic (Python/JS/TS/Go support)
- All codebase agents now prioritize reading codebase overview files
- `best-practices-researcher` upgraded to Claude Opus model for higher quality output
- Enhanced agent documentation with better examples and output format guidelines

**Commands:**
- `/security` command now loads 3-5 relevant Codeguard rules during Phase 0
- `/index_codebase` command automatically updates CLAUDE.md after indexing
- `research_codebase` provides better information source prioritization

**Documentation:**
- README updated with security integration prominently featured
- CLAUDE.md enhanced with security rules workflow documentation
- Directory structure documentation updated to include security_rules/

### Technical Details

- Security rules include YAML frontmatter for language filtering
- Rules provide comprehensive guidance with code examples and implementation checklists
- Source: https://github.com/project-codeguard/rules (Cisco-curated, OWASP-aligned)

---

## [1.3.0] - 2025-11-04

### Breaking Changes

- **Command renamed**: `/describe_pr` → `/pr` for more concise usage
- **Command renamed**: `/rationalize` → `/cleanup` to better reflect the workflow phase (extract knowledge, clean up artifacts)
- **Workflow structure changed**: 8-phase workflow replaces previous approach with clearer separation of concerns (Research → Plan → Implement → Validate → Cleanup → Commit → PR → Deploy)
- **Cleanup behavior changed**: Ephemeral artifacts (plans, research, rationalization documents) are now automatically deleted after knowledge extraction during cleanup phase

### Added

**Command Enhancements:**
- New `/pr` command with enhanced PR description generation workflow
- Code review phase integrated into workflow (before commit)
- Enhanced interactive prompts for better PR descriptions

**JavaScript/TypeScript Indexing:**
- JavaScript indexing support: JavaScript/TypeScript indexer (`claude-helpers/index_js_ts.py`) now processes `.js` and `.jsx` files in addition to `.ts` and `.tsx` files
- Unified JavaScript/TypeScript documentation output with clear labeling
- Better support for FastAPI static file directories and hybrid codebases
- Documentation in `docs/README-indexers.md` explaining JavaScript support and showing comparison examples

**Best Practices System:**
- Comprehensive best practices documentation framework
- `/cleanup` command now creates structured best practices documentation with lessons learned and trade-offs
- Best practices stored with real implementation examples in `memories/best_practices/`

### Changed

**Workflow System:**
- 8-phase workflow with dedicated cleanup phase replacing rationalization
- Cleanup phase now documents best practices with category-based naming
- Ephemeral documents (plans, research) deleted after cleanup (knowledge extraction principle)
- Project documentation (project.md, todo.md, done.md) synchronized during cleanup

**Indexer:**
- **Indexer renamed**: `index_ts.py` → `index_js_ts.py` to accurately reflect JavaScript and TypeScript support
- Default output filename changed from `codebase_overview_typescript.md` to `codebase_overview_js_ts.md` to reflect mixed language support
- Output header now reads "JavaScript/TypeScript/React Codebase Overview"
- `/index_codebase` command now detects and indexes JavaScript files automatically

**Documentation & Instructions:**
- CLAUDE.md expanded with 8-phase workflow explanation and cleanup methodology
- WORKFLOW.md updated to reflect cleanup (not rationalization) workflow
- README.md command count updated (14 slash commands)

### Fixed

- PR template path corrected to `memories/templates/pr_description.md`
- Improved error handling in indexing scripts
- Enhanced documentation fetching reliability
- Better validation reporting in plan-validator
- More robust file detection in deployment workflow

### Technical Details

- File filter updated to include `.js` and `.jsx` extensions for JavaScript support
- All existing regex patterns already compatible with JavaScript syntax
- Command rename transparent to underlying functionality (backward compatible implementation)
- Script rename is a non-breaking change - users should update their references to `index_js_ts.py`

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
- New directory: `memories/shared/research/c4-diagrams-plantuml/` for PlantUML diagram output
- New directory: `memories/shared/rationalization/` for ephemeral working documents during rationalization

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
- `memories-locator` and `memories-analyzer` agents for document discovery and deep analysis

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

**Implementation & Cleanup:**
- `/cleanup` command following Parnas & Clements methodology
- Updates plans to reflect actual implementation (not discovery process)
- Creates ADRs for significant decisions during cleanup
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

[Unreleased]: https://github.com/albertsikkema/claude-config-template/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/albertsikkema/claude-config-template/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/albertsikkema/claude-config-template/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/albertsikkema/claude-config-template/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/albertsikkema/claude-config-template/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/albertsikkema/claude-config-template/releases/tag/v1.0.0
