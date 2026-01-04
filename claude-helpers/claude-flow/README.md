# Claude Workflow Kanban

Kanban board backend for Claude Code workflow management.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn kanban.main:app --reload --port 9118

# API docs at http://localhost:9118/docs
```

## Workflow Stages

1. **Backlog** - New ideas and tasks
2. **Research** - `/research_codebase`
3. **Planning** - `/create_plan`
4. **Implementation** - `/implement_plan`
5. **Review** - `/code_reviewer`
6. **Cleanup** - `/cleanup`
7. **Done** - Completed tasks
