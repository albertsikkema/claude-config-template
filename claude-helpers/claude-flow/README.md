# Claude Flow

A lightweight, local Kanban board for Claude Code workflow management.

**Open-source** · **Lightweight** · **Local-first** · **No internet required** · **Fast** · **Non-obtrusive** · **macOS only**

## Features

- **100% Local** - All data stays on your machine, no cloud services or accounts needed
- **Lightweight** - Uses system WebView (~10MB vs Electron's ~100MB)
- **Fast** - Native performance, instant startup
- **Non-obtrusive** - Runs quietly in the background, integrates with iTerm hooks
- **Easy to use** - One command to install, works out of the box
- **Per-repo isolation** - Each repository gets its own app instance

## Quick Start

```bash
# Desktop app (recommended)
make desktop

# Or build standalone executable
make build
open 'dist/Claude Flow.app'

# Build and install to /Applications
make install
```

## Architecture

- **PyWebView** - Uses macOS native WebView, no Electron bloat
- **FastAPI backend** - Serves API and pre-built React frontend
- **SQLite database** - Local storage in `~/Library/Application Support/claude-flow/`
- **Dynamic ports** - Automatically finds available port, saves to `.claude-flow.port`

## Commands

| Command | Description |
|---------|-------------|
| `make desktop` | Launch desktop app with full HMR |
| `make build` | Build complete app (clean + frontend + backend) |
| `make build-frontend` | Build React frontend only |
| `make build-backend` | Build Python backend with PyInstaller |
| `make install` | Build and install to /Applications |
| `make dev` | Backend + frontend in separate processes |
| `make test` | Run tests |
| `make lint` | Lint and format code |
| `make clean-build` | Remove build artifacts |

## Workflow Stages

1. **Backlog** - New ideas and tasks
2. **Research** - `/research_codebase`
3. **Planning** - `/create_plan`
4. **Implementation** - `/implement_plan`
5. **Review** - `/code_reviewer`
6. **Cleanup** - `/cleanup`
7. **Done** - Completed tasks

## Building for Distribution

```bash
make build      # Build to dist/
make install    # Build and install to /Applications
```

Output: `dist/Claude Flow.app`

The built app bundles Python runtime - no dependencies needed on target machines.

### macOS "App is Damaged" Fix
```bash
xattr -cr 'dist/Claude Flow.app'
```

## Development Mode

For development with hot reload:

```bash
# Terminal 1: Backend
make dev

# Terminal 2: Frontend
cd claude-flow-board && npm run dev
```

## Hook Integration

The desktop app saves its port to `.claude-flow.port`:

```bash
PORT=$(cat claude-helpers/claude-flow/.claude-flow.port)
curl "http://127.0.0.1:$PORT/api/tasks"
```
