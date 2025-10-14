# Sample Thoughts Document

This is an example of how to use the thoughts/ directory structure.

## Purpose

The thoughts/ directory is a structured knowledge base for your project that includes:

1. **Documentation** (`thoughts/docs/`)
   - Project overview and architecture
   - Feature epics and planning
   - Must-haves and should-haves
   - Todo tracking

2. **Plans** (`thoughts/shared/plans/`)
   - Implementation plans for features
   - Dated and versioned
   - Format: `YYYY-MM-DD-description.md` or `YYYY-MM-DD-TICKET-123-description.md`

3. **Research** (`thoughts/shared/research/`)
   - Codebase investigations
   - Technical research
   - Architectural decisions
   - Same naming format as plans

## Example Workflow

### 1. Research Phase

```bash
You: "/research_codebase authentication system"
```

Claude will investigate your codebase and create:
`thoughts/shared/research/2025-10-14-authentication-system.md`

### 2. Planning Phase

```bash
You: "/create_plan let's add OAuth support based on the research"
```

Claude will create an interactive plan:
`thoughts/shared/plans/2025-10-14-oauth-support.md`

### 3. Implementation Phase

```bash
You: "/implement_plan thoughts/shared/plans/2025-10-14-oauth-support.md"
```

Claude will execute the plan step by step.

### 4. Documentation Phase

Update your project documentation in `thoughts/docs/` to reflect what you learned.

## File Naming Conventions

### Plans and Research

**Without ticket reference**:
```
2025-10-14-add-caching-layer.md
2025-10-14-database-optimization.md
2025-10-14-error-handling-improvements.md
```

**With ticket reference**:
```
2025-10-14-JIRA-123-user-authentication.md
2025-10-14-GH-456-api-rate-limiting.md
2025-10-14-ENG-789-performance-optimization.md
```

### Documentation Templates

When you first install, documentation files have `.template` suffix:
```
epics.md.template
musthaves.md.template
project.md.template
shouldhaves.md.template
todo.md.template
```

Remove the `.template` suffix and customize for your project:
```bash
cd thoughts/docs
mv project.md.template project.md
# Edit project.md with your project details
```

## Tips

1. **Use descriptive names**: File names should be clear and searchable
2. **Keep dates accurate**: Use the date when the work started
3. **Link between documents**: Reference related research in plans and vice versa
4. **Update regularly**: Keep documentation current as the project evolves
5. **Git commit thoughts/**: Your thoughts directory is valuable - commit it!

## Example Research Document

```markdown
---
date: 2025-10-14T10:30:00Z
researcher: Claude
git_commit: abc123def
branch: main
topic: "Authentication System Analysis"
tags: [research, authentication, security]
status: complete
---

# Research: Authentication System Analysis

## Summary
[High-level findings]

## Current Implementation
- Found in `app/auth/handler.py:45`
- Uses JWT tokens with 24h expiration
- No refresh token mechanism

## Recommendations
1. Add refresh tokens
2. Implement token rotation
3. Add rate limiting

## Related Plans
- `thoughts/shared/plans/2025-10-14-oauth-support.md`
```

## Example Implementation Plan

```markdown
# OAuth 2.0 Support Implementation Plan

## Overview
Add OAuth 2.0 support for GitHub and Google login.

## Current State Analysis
Based on research in `thoughts/shared/research/2025-10-14-authentication-system.md`:
- Current JWT-only authentication
- No social login support
- Auth handler in `app/auth/handler.py`

## Phase 1: OAuth Infrastructure
- [ ] Install oauth library: `pip install authlib`
- [ ] Create OAuth client configuration
- [ ] Add OAuth routes

## Phase 2: Provider Integration
- [ ] Implement GitHub OAuth
- [ ] Implement Google OAuth
- [ ] Add user account linking

## Testing Strategy
- [ ] Unit tests for OAuth flow
- [ ] Integration tests with mock providers
- [ ] Manual testing with real accounts
```

---

This is just a starting point - customize the structure for your team's needs!
