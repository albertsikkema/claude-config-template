# CLAUDE.md

Guidance for Claude Code when working with this codebase.

## Project Overview

Claude Flow - FastAPI backend with React frontend for Kanban-style workflow management. Runs as a per-repo PyWebView desktop application.

## Commands

```bash
make desktop      # Launch desktop app with full HMR
make build-app    # Create standalone executable
make dev          # Backend + frontend in separate processes
make test         # Run tests
make lint         # Lint and format
```

## Key Files

| File | Purpose |
|------|---------|
| `desktop_app.py` | PyWebView launcher, port allocation, repo detection |
| `finder-env-wrapper.sh` | macOS Finder environment setup (baked into .app) |
| `claude-flow.spec` | PyInstaller build configuration |
| `src/kanban/main.py` | FastAPI app, routes, static file serving |
| `src/kanban/database.py` | SQLAlchemy models and DB path handling |

## Desktop App Patterns

**Frozen mode detection** - PyInstaller extracts to temp dir:
```python
if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)  # Extracted bundle
    project_root = Path.cwd()         # Set by wrapper script
```

**Pydantic plugins** - Must disable before imports in frozen mode:
```python
if getattr(sys, "frozen", False):
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
```

**Database path** - Global location shared across all repos:
- macOS: `~/Library/Application Support/claude-flow/kanban.db`
- Windows: `%LOCALAPPDATA%/claude-flow/kanban.db`
- Linux: `~/.local/share/claude-flow/kanban.db`

To query the database directly:
```bash
sqlite3 ~/Library/Application\ Support/claude-flow/kanban.db "SELECT * FROM tasks;"
sqlite3 ~/Library/Application\ Support/claude-flow/kanban.db "SELECT * FROM settings;"
```

## Codebase Indexes

Generated overviews in parent `thoughts/codebase/`:
- `codebase_overview_claude-flow_py.md` - Python backend
- `codebase_overview_claude-flow-board_js_ts.md` - React frontend

Regenerate with `/index_codebase`.
