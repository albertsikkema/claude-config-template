# CLAUDE.md

This file provides guidance to Claude Code when working with this codebase.

## Project Overview

Claude Workflow Kanban - A FastAPI backend with React frontend for managing Claude Code workflow tasks through a Kanban board interface.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn kanban.main:app --reload --port 8000

# API docs at http://localhost:8000/docs
```

## Codebase Overview Files

This project maintains automatically generated codebase overview files in `thoughts/codebase/`:

### Available Index Files
- `codebase_overview_src_py.md` - Python backend overview (FastAPI, routers, models)
- `codebase_overview_claude-flow-board_js_ts.md` - TypeScript/React frontend overview
- `openapi.json` - FastAPI OpenAPI schema

### What These Files Contain
Each overview file provides a comprehensive map of the codebase including:
- **Complete file tree** of the scanned directory
- **All classes and functions** with descriptions
- **Full function signatures**: input parameters, return types, and expected outputs
- **Call relationships**: where each function/class is called from (caller information)

### Why These Files Matter
These files are essential for:
- **Fast navigation**: Instantly find where code lives without extensive searching
- **Understanding structure**: See the complete architecture and organization
- **Analyzing relationships**: Understand how components interact and depend on each other
- **Code analysis**: Get function signatures and contracts without reading implementation

### Regenerating Indexes
To regenerate the codebase overview files, run:
```bash
/index_codebase
```

The indexer will automatically detect your project type and generate appropriate overview files.
