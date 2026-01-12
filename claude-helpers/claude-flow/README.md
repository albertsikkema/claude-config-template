# Claude Flow

Kanban board for Claude Code workflow management. Runs as a per-repo desktop application.

## Quick Start

```bash
# Desktop app (recommended)
make desktop

# Or build standalone executable
make build-app
open 'dist/Claude Flow.app'
```

## Architecture

- **Per-Repo**: Each repository gets its own app instance with isolated data
- **PyWebView**: Uses system WebView (~10MB vs Electron's ~100MB)
- **Dynamic Ports**: Automatically finds available port, saves to `.claude-flow.port`
- **No Node Runtime**: Frontend pre-built, served by FastAPI

## Commands

| Command | Description |
|---------|-------------|
| `make desktop` | Launch desktop app with full HMR |
| `make build-app` | Create standalone `.app` bundle |
| `make dev` | Backend + frontend in separate processes |
| `make test` | Run tests |
| `make lint` | Lint and format code |

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
make build-app
```

Output: `dist/Claude Flow.app` (macOS) or `dist/claude-flow` (Linux/Windows)

The built app includes Python runtime - no installation needed on target machines.

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
