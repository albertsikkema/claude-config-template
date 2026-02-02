You are tasked with indexing a codebase and generating comprehensive Markdown documentation.

## Available Indexers

The repository has four indexer scripts in `./.claude/helpers/`:
1. **.claude/helpers/index_python.py** - For Python codebases
2. **.claude/helpers/index_js_ts.py** - For JavaScript/TypeScript/React codebases
3. **.claude/helpers/index_go.py** - For Go codebases
4. **.claude/helpers/index_cpp.py** - For C/C++ codebases

## Your Task

**IMPORTANT: Do NOT ask the user questions. Automatically detect and index based on the project structure.**

1. **Detect the project type** by checking for common files/directories:
   - Python: Look for `.py` files, `requirements.txt`, `pyproject.toml`, `setup.py`, etc.
   - JavaScript/TypeScript: Look for `.js/.jsx/.ts/.tsx` files, `package.json`, `tsconfig.json`, etc.
   - Go: Look for `.go` files, `go.mod`, `go.sum`, etc.
   - C/C++: Look for `.cpp/.cxx/.cc/.c/.hpp/.h` files, `CMakeLists.txt`, `Makefile`, `*.vcxproj`, etc.

2. **Automatically determine paths**:
   - For Python:
     - First check for common backend directory names with Python files:
       - `backend/`, `server/`, `api/`, `service/`, `app/`, `src/`
     - Search in both root and nested structures (e.g., `./backend`, `./project/backend`)
     - If found, index the parent directory (e.g., `backend/` not `backend/app/`)
     - This captures root-level files like `pyproject.toml`, `requirements.txt`, tests, etc.
     - Fall back to `./` if no specific structure found
   - For JavaScript/TypeScript:
     - First check for common frontend directory names with JavaScript/TypeScript files:
       - `frontend/`, `client/`, `web/`, `ui/`, `app/`, `src/`, `static/`
     - Search in both root and nested structures (e.g., `./frontend`, `./project/frontend`)
     - If found, index the parent directory (e.g., `frontend/` not `frontend/src/`)
     - This captures config files like `package.json`, `tsconfig.json`, `vite.config.ts`, etc.
     - Also check for static file directories (e.g., `static/js/`) commonly used in FastAPI projects
     - Fall back to `./` if no specific structure found
   - For Go:
     - First check for common Go directory names with Go files:
       - `backend/`, `server/`, `cmd/`, `pkg/`, `internal/`, `api/`, `src/`
     - Search in both root and nested structures (e.g., `./backend`, `./project/backend`)
     - If found, index the parent directory to capture `go.mod`, `go.sum`, etc.
     - Fall back to `./` if no specific structure found
   - For C/C++:
     - First check for common C/C++ directory names with source files:
       - `src/`, `source/`, `Source/`, `lib/`, `include/`, `app/`
     - Search in both root and nested structures (e.g., `./src`, `./project/src`)
     - If found, index the parent directory to capture `CMakeLists.txt`, headers, etc.
     - Check for build system files: `CMakeLists.txt`, `Makefile`, `*.vcxproj`
     - Fall back to `./` if no specific structure found
   - If user provides a path in their message, use that path exactly

3. **Determine output filenames** based on the directory being scanned:
   - Extract the directory name (e.g., `backend` from `./cc_wrapper/backend`)
   - For root directory (`./`), use `root` as the name
   - Format: `codebase_overview_<dirname>_py.md` for Python
   - Format: `codebase_overview_<dirname>_js_ts.md` for JavaScript/TypeScript
   - Format: `codebase_overview_<dirname>_go.md` for Go
   - Format: `codebase_overview_<dirname>_cpp.md` for C/C++

4. **Run the appropriate indexer(s)** automatically:
   ```bash
   # For Python
   python ./.claude/helpers/index_python.py <directory> -o memories/codebase/codebase_overview_<dirname>_py.md

   # For JavaScript/TypeScript
   python ./.claude/helpers/index_js_ts.py <directory> -o memories/codebase/codebase_overview_<dirname>_js_ts.md

   # For Go
   python ./.claude/helpers/index_go.py <directory> -o memories/codebase/codebase_overview_<dirname>_go.md

   # For C/C++
   python ./.claude/helpers/index_cpp.py <directory> -o memories/codebase/codebase_overview_<dirname>_cpp.md
   ```

   **Important**: All output files must be saved to `memories/codebase/` directory.

5. **Update CLAUDE.md** with codebase overview documentation:
   - Check if CLAUDE.md exists and search for existing codebase section
   - If no mention exists, add a new "Codebase Overview Files" section
   - If mention exists, update it with current information
   - Document the location, content, and how to regenerate indexes
   - See "Update CLAUDE.md Documentation" section below for detailed instructions

6. **Report the results** concisely:
   - Show what was indexed
   - Show output file locations
   - Brief summary of findings
   - Confirm CLAUDE.md has been updated

## Detection Strategy

1. Check if user specified a path in their message (e.g., "/index_codebase ./src")
2. If not, scan current directory structure
3. Index Python if `.py` files are found
4. Index JavaScript/TypeScript if `.js/.jsx/.ts/.tsx` files are found
5. Index Go if `.go` files are found
6. Index C/C++ if `.cpp/.cxx/.cc/.c/.hpp/.h` files are found
7. Index multiple languages if multiple are present
7. **Smart Directory Detection for Python**:
   - Look for common backend directory names with Python files:
     - `backend/`, `server/`, `api/`, `service/`, `app/`, `src/`
   - Search in both root (e.g., `./backend`) and nested (e.g., `./project/backend`) structures
   - Check for root-level indicators: `pyproject.toml`, `requirements.txt`, `setup.py`, `tests/`
   - Index the parent directory to capture complete structure
   - Common patterns:
     - `backend/` (with `app/`, `tests/`, `pyproject.toml`) → Index `backend/`
     - `server/` (with FastAPI/Flask app) → Index `server/`
     - `api/` (with REST API structure) → Index `api/`
     - `app/` (standalone FastAPI app) → Index `app/`
8. **Smart Directory Detection for JavaScript/TypeScript**:
   - Look for common frontend directory names with JavaScript/TypeScript files:
     - `frontend/`, `client/`, `web/`, `ui/`, `app/`, `src/`, `static/`
   - Search in both root (e.g., `./frontend`) and nested (e.g., `./project/frontend`) structures
   - Check for root-level indicators: `package.json`, `tsconfig.json`, `vite.config.ts`, `public/`
   - Also detect FastAPI static file directories (`static/js/`, `static/scripts/`)
   - Index the parent directory to capture complete structure
   - Common patterns:
     - `frontend/` (with `src/`, `public/`, config files) → Index `frontend/`
     - `client/` (with React/Vue app) → Index `client/`
     - `web/` (with web app structure) → Index `web/`
     - `src/` (standalone with JavaScript/TypeScript) → Index `src/`
     - `static/` (FastAPI static files) → Index `static/`
9. **Smart Directory Detection for Go**:
   - Look for common Go directory names with Go files:
     - `backend/`, `server/`, `cmd/`, `pkg/`, `internal/`, `api/`, `src/`
   - Search in both root (e.g., `./backend`) and nested (e.g., `./project/backend`) structures
   - Check for root-level indicators: `go.mod`, `go.sum`, `Makefile`, `cmd/`
   - Index the parent directory to capture complete structure
   - Common patterns:
     - `backend/` (with `cmd/`, `pkg/`, `internal/`, `go.mod`) → Index `backend/`
     - `server/` (with Go microservice) → Index `server/`
     - `cmd/` (with main packages) → Index `cmd/`
     - `internal/` (with internal packages) → Index `internal/`
10. **Smart Directory Detection for C/C++**:
    - Look for common C/C++ directory names with source files:
      - `src/`, `source/`, `Source/`, `lib/`, `include/`, `app/`
    - Search in both root (e.g., `./src`) and nested (e.g., `./project/src`) structures
    - Check for build system indicators: `CMakeLists.txt`, `Makefile`, `*.vcxproj`, `meson.build`
    - Index the parent directory to capture complete structure
    - Common patterns:
      - `src/` or `Source/` (with `.cpp/.h` files) → Index `src/` or `Source/`
      - Root with `CMakeLists.txt` and source files → Index `./`
      - `include/` (with headers) + `src/` (with sources) → Index parent
    - **Note**: The C/C++ indexer automatically skips common library directories like `JUCE`, `tracktion_engine`, `third_party`, `vendor`, `external`, etc.
11. **FastAPI Detection**: If Python code is detected, check for FastAPI usage:
   - Look for `from fastapi import` or `import fastapi` in Python files
   - If FastAPI is detected, attempt to fetch OpenAPI schema using `./.claude/helpers/fetch_openapi.sh`
   - Only run if a server might be running (non-intrusive check)

## Examples

### Auto-detect and index everything (root directory)
```bash
python ./.claude/helpers/index_python.py ./ -o memories/codebase/codebase_overview_root_py.md
python ./.claude/helpers/index_js_ts.py ./ -o memories/codebase/codebase_overview_root_js_ts.md
python ./.claude/helpers/index_go.py ./ -o memories/codebase/codebase_overview_root_go.md
python ./.claude/helpers/index_cpp.py ./ -o memories/codebase/codebase_overview_root_cpp.md
```

### Index specific directory (backend)
```bash
# Directory: ./cc_wrapper/backend -> filename includes "backend"
# Indexes entire backend structure (app/, tests/, pyproject.toml, etc.)
python ./.claude/helpers/index_python.py ./cc_wrapper/backend -o memories/codebase/codebase_overview_backend_py.md
```

### Index specific directory (frontend)
```bash
# Directory: ./cc_wrapper/frontend -> filename includes "frontend"
# Indexes entire frontend structure (src/, public/, config files)
# Includes both .js and .ts files
python ./.claude/helpers/index_js_ts.py ./cc_wrapper/frontend -o memories/codebase/codebase_overview_frontend_js_ts.md
```

### Index specific directory (Go backend)
```bash
# Directory: ./backend -> filename includes "backend"
# Indexes entire Go backend structure (cmd/, pkg/, internal/, go.mod)
python ./.claude/helpers/index_go.py ./backend -o memories/codebase/codebase_overview_backend_go.md
```

### Index specific directory (C/C++ source)
```bash
# Directory: ./Source -> filename includes "Source"
# Indexes C/C++ source files (classes, structs, functions, enums)
# Automatically skips library directories (JUCE, tracktion_engine, etc.)
python ./.claude/helpers/index_cpp.py ./Source -o memories/codebase/codebase_overview_Source_cpp.md

# Or index from root (will skip build/, third_party/, etc.)
python ./.claude/helpers/index_cpp.py ./ -o memories/codebase/codebase_overview_root_cpp.md
```

### Fetch FastAPI OpenAPI schema (if FastAPI detected)
```bash
# Check for FastAPI imports in Python files
# If found, run with auto-detection:
bash ./.claude/helpers/fetch_openapi.sh auto memories/codebase/openapi.json

# Or specify port explicitly:
bash ./.claude/helpers/fetch_openapi.sh http://localhost:8001 memories/codebase/openapi.json
```

## Notes

- DO NOT use AskUserQuestion tool
- Be autonomous and intelligent about detection
- Both scripts automatically skip `node_modules`, `.venv`, `.git`, etc.
- Output files are created in `memories/codebase/` directory
- After indexing, always update CLAUDE.md to document the codebase overview files
- Work silently and efficiently

## FastAPI Schema Fetching

When FastAPI is detected:
1. Use Grep to search for `from fastapi import|import fastapi` in `.py` files
2. If found, inform user that FastAPI was detected
3. Run `bash ./.claude/helpers/fetch_openapi.sh auto memories/codebase/openapi.json`
   - The script will auto-detect ports 8000-8010 for running FastAPI servers
   - Or user can specify explicit URL: `bash ./.claude/helpers/fetch_openapi.sh http://localhost:8001 memories/codebase/openapi.json`
4. The script will:
   - Auto-detect running FastAPI server on common ports (8000-8010) if "auto" is specified
   - Check if server is running at `/health` or `/docs` endpoint
   - Fetch OpenAPI schema from `/openapi.json`
   - Save to `memories/codebase/openapi.json`
   - Display schema information if available
5. **IMPORTANT - User Feedback**:
   - If the script succeeds, inform user: "✅ OpenAPI schema fetched successfully from [URL]"
   - If the script fails (server not running), inform user: "⚠️ FastAPI server not detected on ports 8000-8010. Start server and re-run if needed, or specify explicit URL."
   - Show the output from the fetch script to provide full context
6. Continue with normal Python indexing regardless of OpenAPI fetch result

## Output Directory

**IMPORTANT**: Before running any indexer, ensure `memories/codebase/` directory exists:
- If it doesn't exist, create it with `mkdir -p memories/codebase/`
- All output files go to `memories/codebase/` with directory-based naming:
  - `codebase_overview_<dirname>_py.md` - Python documentation
  - `codebase_overview_<dirname>_js_ts.md` - JavaScript/TypeScript documentation
  - `codebase_overview_<dirname>_go.md` - Go documentation
  - `codebase_overview_<dirname>_cpp.md` - C/C++ documentation
  - `openapi.json` - FastAPI OpenAPI schema (if applicable)

**Filename Examples:**
- Scanning `./` (Python) → `codebase_overview_root_py.md`
- Scanning `./` (JavaScript/TypeScript) → `codebase_overview_root_js_ts.md`
- Scanning `./` (Go) → `codebase_overview_root_go.md`
- Scanning `./` (C/C++) → `codebase_overview_root_cpp.md`
- Scanning `./backend` (Python) → `codebase_overview_backend_py.md`
- Scanning `./backend` (Go) → `codebase_overview_backend_go.md`
- Scanning `./server` → `codebase_overview_server_py.md`
- Scanning `./api` → `codebase_overview_api_py.md`
- Scanning `./cc_wrapper/backend` → `codebase_overview_backend_py.md`
- Scanning `./frontend` → `codebase_overview_frontend_js_ts.md`
- Scanning `./client` → `codebase_overview_client_js_ts.md`
- Scanning `./web` → `codebase_overview_web_js_ts.md`
- Scanning `./static` → `codebase_overview_static_js_ts.md`
- Scanning `./cc_wrapper/frontend` → `codebase_overview_frontend_js_ts.md`
- Scanning `./src` (standalone JS/TS) → `codebase_overview_src_js_ts.md`
- Scanning `./cmd` (Go) → `codebase_overview_cmd_go.md`
- Scanning `./pkg` (Go) → `codebase_overview_pkg_go.md`
- Scanning `./Source` (C/C++) → `codebase_overview_Source_cpp.md`
- Scanning `./src` (C/C++) → `codebase_overview_src_cpp.md`
- Scanning `./lib` (C/C++) → `codebase_overview_lib_cpp.md`

## Update CLAUDE.md Documentation

**IMPORTANT**: After successfully creating index files, update CLAUDE.md to document the codebase overview files:

1. **Check if CLAUDE.md exists** in the project root
2. **Search for existing codebase documentation section**:
   - Look for mentions of `memories/codebase/` or "codebase overview files" or "index files"
3. **If no mention exists, add a new section** after the main documentation sections:

```markdown
## Codebase Overview Files

This project maintains automatically generated codebase overview files in `memories/codebase/`:

### Available Index Files
- `codebase_overview_*_py.md` - Python codebase overview
- `codebase_overview_*_js_ts.md` - JavaScript/TypeScript codebase overview
- `codebase_overview_*_go.md` - Go codebase overview
- `codebase_overview_*_cpp.md` - C/C++ codebase overview
- `openapi.json` - FastAPI OpenAPI schema (if applicable)

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
```

4. **If a mention already exists, update it** to match the format above, ensuring:
   - The location `memories/codebase/` is correct
   - All file types are mentioned (Python, JS/TS, Go, C/C++)
   - The content description includes: file tree, classes/functions, signatures (input params, return types), and call relationships
   - The regeneration command `/index_codebase` is documented

5. **Preserve any existing project-specific notes** about the codebase structure

6. **Report to the user** that CLAUDE.md has been updated with codebase overview documentation
