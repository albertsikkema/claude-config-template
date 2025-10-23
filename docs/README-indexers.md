# Codebase Indexers

Generate comprehensive, searchable markdown documentation for Python, TypeScript/React, and Go codebases.

## Overview

These indexers automatically discover and document code structure across multiple languages:

- **`index_python.py`** - Python codebases (functions, classes, Pydantic models)
- **`index_js_ts.py`** - JavaScript/TypeScript/React codebases (components, functions, interfaces, types)
- **`index_go.py`** - Go codebases (packages, structs, interfaces, functions)

## Quick Start

### Use via Claude Code (Recommended)

```bash
/index_codebase
```

Claude will:
1. Auto-detect your project languages (Python, TypeScript, Go)
2. Find the right directories to scan (backend/, frontend/, etc.)
3. Run the appropriate indexers
4. Save documentation to `thoughts/codebase/`

### Manual Usage

```bash
# Python
python claude-helpers/index_python.py ./backend -o codebase_overview_backend_py.md

# JavaScript/TypeScript
python claude-helpers/index_js_ts.py ./frontend -o codebase_overview_frontend_js_ts.md

# Go
python claude-helpers/index_go.py ./server -o codebase_overview_server_go.md
```

## Features

### Python Indexer (`index_python.py`)

**Extracts:**
- ✅ Functions with signatures, parameters, return types, docstrings
- ✅ Classes with methods and docstrings
- ✅ Pydantic models with fields and types
- ✅ Global variables with type annotations
- ✅ Call tracking (shows where functions/classes are called from)

**Smart Detection:**
- Distinguishes Pydantic `BaseModel` from regular classes
- Tracks async functions
- Extracts type annotations
- AST-based parsing (accurate and fast)

**Skips:**
- `.venv`, `venv`, `env` - Virtual environments
- `__pycache__`, `.pytest_cache`, `.mypy_cache` - Cache directories
- `dist`, `build`, `.eggs` - Build outputs
- `node_modules` - JavaScript dependencies

**Example Output:**
```markdown
## Functions

### `calculate_total(items: List[Item], discount: float) -> Decimal`
> Calculate the total price with discount applied

**Called from:**
- `backend/app/services/order.py::OrderService.create_order`
- `backend/app/api/checkout.py::checkout_endpoint`
```

### JavaScript/TypeScript Indexer (`index_js_ts.py`)

**Extracts:**
- ✅ React components (function and class components)
- ✅ Regular functions with signatures
- ✅ Interfaces with fields
- ✅ Type aliases
- ✅ Classes with methods
- ✅ Export statements

**Smart Detection:**
- Distinguishes React components (capitalized) from regular functions
- Extracts component props types
- Tracks exported items
- Handles JSX/TSX syntax

**Skips:**
- `node_modules`, `jspm_packages`, `bower_components` - Dependencies
- `dist`, `build`, `out`, `.next`, `.nuxt` - Build outputs
- `.cache`, `.parcel-cache`, `.turbo` - Cache directories
- `coverage` - Test output

**Example Output:**
```markdown
## React Components

### `UserProfile` **[exported]**

- **Type:** function component
- **Line:** 42
- **Props:** `UserProfileProps`

## Interfaces

### `UserProfileProps` **[exported]**

- **Line:** 38
- **Fields:**
  - `userId`: `string`
  - `onUpdate`: `(user: User) => void`
```

### JavaScript Support

The TypeScript indexer **also indexes JavaScript files** (`.js`, `.jsx`):

**What gets extracted from JavaScript:**
- ✅ Functions and arrow functions
- ✅ Classes and methods
- ✅ React components (function and class-based)
- ✅ Export statements
- ❌ Interfaces (TypeScript-only)
- ❌ Type aliases (TypeScript-only)

**Use cases:**
- FastAPI static files (`static/js/app.js`)
- Built SPA files (`frontend/dist/main.js`)
- Mixed JavaScript/TypeScript codebases
- TypeScript migration projects

**Example:**
```bash
# Index both .js and .ts files in static directory
python claude-helpers/index_js_ts.py ./static -o codebase_overview_static_js_ts.md
```

**What you'll see in output:**

*JavaScript function:*
```javascript
// In: static/js/app.js
export function handleClick(event) {
    console.log(event);
}
```
*Appears as:*
```
Function: handleClick
  Signature: (event)
  File: static/js/app.js:42
```

*TypeScript function:*
```typescript
// In: src/utils.ts
export function handleClick(event: MouseEvent): void {
    console.log(event);
}
```
*Appears as:*
```
Function: handleClick
  Signature: (event: MouseEvent): void
  File: src/utils.ts:42
```

The indexer gracefully handles both - JavaScript shows parameters without types, TypeScript shows full type signatures.

### Go Indexer (`index_go.py`)

**Extracts:**
- ✅ Package declarations
- ✅ Import statements
- ✅ Structs with fields and tags
- ✅ Interfaces with method signatures
- ✅ Functions with signatures
- ✅ Methods with receiver types (pointer vs value)
- ✅ Constants and variables

**Smart Detection:**
- Distinguishes pointer receivers from value receivers
- Extracts struct field tags (JSON, XML, etc.)
- Groups methods by receiver type
- Handles multi-line declarations

**Skips:**
- `vendor`, `third_party` - Dependencies
- `bin`, `pkg` - Build outputs
- `testdata` - Test data
- `*_test.go` - Test files
- `node_modules` - JavaScript dependencies

**Example Output:**
```markdown
## Structs

### `User`

- **Line:** 23
- **Fields:**
  - `ID` `uuid.UUID` `json:"id" db:"id"`
  - `Email` `string` `json:"email" validate:"email"`
  - `CreatedAt` `time.Time` `json:"created_at"`

## Methods

### `User` Methods

#### `Save`

- **Line:** 45
- **Receiver:** `(*User)`
- **Signature:** `func (*User) Save(ctx context.Context) error`
```

## Output Format

All indexers generate markdown files with:

1. **File Tree** - Visual directory structure
2. **Table of Contents** - Quick navigation
3. **Per-File Documentation** - Detailed breakdown of each file

**Structure:**
```markdown
# [Language] Codebase Overview

## File Tree
[ASCII tree diagram]

## Table of Contents
- [path/to/file.ext](#path-to-file-ext)

## File: `path/to/file.ext`

### Overview
**Functions:** 5 | **Classes:** 2 | **Interfaces:** 3

### [Sections by construct type]
...
```

## Common Options

All indexers support the same command-line interface:

```bash
python claude-helpers/index_[python|ts|go].py [OPTIONS] [DIRECTORY]

Arguments:
  DIRECTORY         Directory to scan (default: ./)
                   Supports relative (./dir) and absolute (/path/to/dir) paths

Options:
  -o, --output FILE Output markdown file
                   Default: codebase_overview[_language].md
  --help            Show help message
```

## Examples

### Scan Current Directory

```bash
# Auto-detect and use defaults
python claude-helpers/index_python.py
# → Output: codebase_overview.md

python claude-helpers/index_js_ts.py
# → Output: codebase_overview_js_ts.md

python claude-helpers/index_go.py
# → Output: codebase_overview_go.md
```

### Scan Specific Directory

```bash
# Backend Python code
python claude-helpers/index_python.py ./backend -o backend_docs.md

# Frontend JavaScript/TypeScript code
python claude-helpers/index_js_ts.py ./frontend/src -o frontend_docs.md

# Go microservice
python claude-helpers/index_go.py ./services/api -o api_docs.md
```

### Nested Project Structure

```bash
# Full-stack project
python claude-helpers/index_python.py ./myapp/backend -o thoughts/codebase/backend_py.md
python claude-helpers/index_js_ts.py ./myapp/frontend -o thoughts/codebase/frontend_js_ts.md
python claude-helpers/index_go.py ./myapp/services -o thoughts/codebase/services_go.md
```

## Integration with `/index_codebase`

The `/index_codebase` slash command uses these scripts intelligently:

1. **Auto-Detection**
   - Scans for `.py`, `.ts/.tsx`, `.go` files
   - Identifies language-specific directories
   - Determines appropriate indexer(s)

2. **Smart Paths**
   - Python: Looks for `backend/`, `server/`, `api/`, `app/`
   - TypeScript: Looks for `frontend/`, `client/`, `web/`, `src/`
   - Go: Looks for `cmd/`, `pkg/`, `internal/`, `api/`

3. **Organized Output**
   - All docs saved to `thoughts/codebase/`
   - Naming: `codebase_overview_<dirname>_<lang>.md`
   - Examples: `codebase_overview_backend_py.md`, `codebase_overview_frontend_ts.md`

## Prerequisites

- **Python 3.6+** - All scripts use Python standard library only
- **No external dependencies** - Works out of the box

## Best Practices

### When to Index

✅ **Good times to index:**
- Before starting research (`/research_codebase`)
- After major refactoring
- When onboarding new team members
- Before creating implementation plans

❌ **Don't index:**
- After every small change (unnecessary)
- In CI/CD pipelines (generates large files)

### Directory Selection

**Index at the right level:**
```bash
# ✅ Good - captures whole structure
python claude-helpers/index_python.py ./backend

# ❌ Too narrow - misses context
python claude-helpers/index_python.py ./backend/app/services

# ✅ Good - specific bounded context
python claude-helpers/index_go.py ./services/payment
```

### Output Organization

**Keep it organized:**
```bash
# ✅ Recommended - save to thoughts/codebase/
python claude-helpers/index_python.py ./backend -o thoughts/codebase/backend_py.md

# ❌ Avoid - clutters project root
python claude-helpers/index_python.py ./backend -o backend_docs.md
```

## Troubleshooting

### "No Python files found"

**Cause:** Wrong directory or no matching files

**Solution:**
```bash
# Check for files first
ls **/*.py

# Try parent directory
python claude-helpers/index_python.py ../
```

### "Permission denied"

**Cause:** No read access to directory

**Solution:**
```bash
# Check permissions
ls -la /path/to/directory

# Run with appropriate permissions
chmod +r -R /path/to/directory
```

### Large output file

**Cause:** Very large codebase

**Solution:**
- Index specific subdirectories instead
- Exclude large generated files manually
- Consider splitting into multiple indexes

### Missing type information

**Cause:** Code lacks type annotations (Python/TypeScript)

**Solution:**
- Indexers show what's in the code
- Add type hints to improve documentation
- Use TypeScript strict mode for better types

## Performance

**Typical indexing speed:**
- Python: ~1000 files/second
- TypeScript: ~800 files/second
- Go: ~1200 files/second

**Large codebases:**
- 10,000 Python files: ~10 seconds
- 5,000 TypeScript files: ~6 seconds
- 8,000 Go files: ~7 seconds

## Technical Details

### Python Indexer

- **Parsing:** Python `ast` module (Abstract Syntax Tree)
- **Type extraction:** Analyzes type annotations via AST
- **Call tracking:** Two-pass analysis with indexed lookups
- **Pydantic detection:** Checks for `BaseModel` inheritance

### TypeScript Indexer

- **Parsing:** Regex-based pattern matching
- **Component detection:** Checks for capitalized function names + JSX
- **Props extraction:** Analyzes function signatures for type annotations
- **Export tracking:** Monitors `export` statements

### Go Indexer

- **Parsing:** Regex-based pattern matching
- **Package detection:** Analyzes `package` declarations
- **Struct tags:** Extracts backtick-quoted field tags
- **Receiver analysis:** Distinguishes `*Type` from `Type` receivers

## Why Use These Indexers?

**For Humans:**
- 📖 Comprehensive codebase overview
- 🔍 Searchable documentation
- 🗺️ Navigate unfamiliar code
- 📊 Understand project structure

**For AI (Claude):**
- 🤖 Faster research and analysis
- 🎯 Precise file:line references
- 🔗 Call graph understanding
- 💡 Better implementation suggestions

## Related Commands

- `/index_codebase` - Auto-detect and index entire project
- `/research_codebase` - Research using indexed documentation
- `/create_plan` - Create plans with codebase context

## See Also

- [fetch-docs.py](../docs/fetch-docs.md) - Fetch external documentation
- [/index_codebase command](./.claude/commands/index_codebase.md) - Auto indexing workflow
- [WORKFLOW.md](../WORKFLOW.md) - Complete development workflow
