You are tasked with indexing a codebase and generating comprehensive Markdown documentation.

## Available Indexers

The repository has two indexer scripts in `./claude-helpers/`:
1. **claude-helpers/index_python.py** - For Python codebases
2. **claude-helpers/index_ts.py** - For TypeScript/React codebases

## Your Task

**IMPORTANT: Do NOT ask the user questions. Automatically detect and index based on the project structure.**

1. **Detect the project type** by checking for common files/directories:
   - Python: Look for `.py` files, `requirements.txt`, `pyproject.toml`, `setup.py`, etc.
   - TypeScript: Look for `.ts/.tsx` files, `package.json`, `tsconfig.json`, etc.

2. **Automatically determine paths**:
   - For Python:
     - First check for common backend directory names with Python files:
       - `backend/`, `server/`, `api/`, `service/`, `app/`, `src/`
     - Search in both root and nested structures (e.g., `./backend`, `./project/backend`)
     - If found, index the parent directory (e.g., `backend/` not `backend/app/`)
     - This captures root-level files like `pyproject.toml`, `requirements.txt`, tests, etc.
     - Fall back to `./` if no specific structure found
   - For TypeScript:
     - First check for common frontend directory names with TypeScript files:
       - `frontend/`, `client/`, `web/`, `ui/`, `app/`, `src/`
     - Search in both root and nested structures (e.g., `./frontend`, `./project/frontend`)
     - If found, index the parent directory (e.g., `frontend/` not `frontend/src/`)
     - This captures config files like `package.json`, `tsconfig.json`, `vite.config.ts`, etc.
     - Fall back to `./` if no specific structure found
   - If user provides a path in their message, use that path exactly

3. **Determine output filenames** based on the directory being scanned:
   - Extract the directory name (e.g., `backend` from `./cc_wrapper/backend`)
   - For root directory (`./`), use `root` as the name
   - Format: `codebase_overview_<dirname>_py.md` for Python
   - Format: `codebase_overview_<dirname>_ts.md` for TypeScript

4. **Run the appropriate indexer(s)** automatically:
   ```bash
   # For Python
   python ./claude-helpers/index_python.py <directory> -o thoughts/codebase/codebase_overview_<dirname>_py.md

   # For TypeScript
   python ./claude-helpers/index_ts.py <directory> -o thoughts/codebase/codebase_overview_<dirname>_ts.md
   ```

   **Important**: All output files must be saved to `thoughts/codebase/` directory.

5. **Report the results** concisely:
   - Show what was indexed
   - Show output file locations
   - Brief summary of findings

## Detection Strategy

1. Check if user specified a path in their message (e.g., "/index_codebase ./src")
2. If not, scan current directory structure
3. Index Python if `.py` files are found
4. Index TypeScript if `.ts/.tsx` files are found
5. Index both if both are present
6. **Smart Directory Detection for Python**:
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
7. **Smart Directory Detection for TypeScript**:
   - Look for common frontend directory names with TypeScript files:
     - `frontend/`, `client/`, `web/`, `ui/`, `app/`, `src/`
   - Search in both root (e.g., `./frontend`) and nested (e.g., `./project/frontend`) structures
   - Check for root-level indicators: `package.json`, `tsconfig.json`, `vite.config.ts`, `public/`
   - Index the parent directory to capture complete structure
   - Common patterns:
     - `frontend/` (with `src/`, `public/`, config files) → Index `frontend/`
     - `client/` (with React/Vue app) → Index `client/`
     - `web/` (with web app structure) → Index `web/`
     - `src/` (standalone with TypeScript) → Index `src/`
8. **FastAPI Detection**: If Python code is detected, check for FastAPI usage:
   - Look for `from fastapi import` or `import fastapi` in Python files
   - If FastAPI is detected, attempt to fetch OpenAPI schema using `./claude-helpers/fetch_openapi.sh`
   - Only run if a server might be running (non-intrusive check)

## Examples

### Auto-detect and index everything (root directory)
```bash
python ./claude-helpers/index_python.py ./ -o thoughts/codebase/codebase_overview_root_py.md
python ./claude-helpers/index_ts.py ./ -o thoughts/codebase/codebase_overview_root_ts.md
```

### Index specific directory (backend)
```bash
# Directory: ./cc_wrapper/backend -> filename includes "backend"
# Indexes entire backend structure (app/, tests/, pyproject.toml, etc.)
python ./claude-helpers/index_python.py ./cc_wrapper/backend -o thoughts/codebase/codebase_overview_backend_py.md
```

### Index specific directory (frontend)
```bash
# Directory: ./cc_wrapper/frontend -> filename includes "frontend"
# Indexes entire frontend structure (src/, public/, config files)
python ./claude-helpers/index_ts.py ./cc_wrapper/frontend -o thoughts/codebase/codebase_overview_frontend_ts.md
```

### Fetch FastAPI OpenAPI schema (if FastAPI detected)
```bash
# Check for FastAPI imports in Python files
# If found, run:
bash ./claude-helpers/fetch_openapi.sh http://localhost:8000 thoughts/codebase/openapi.json
```

## Notes

- DO NOT use AskUserQuestion tool
- Be autonomous and intelligent about detection
- Both scripts automatically skip `node_modules`, `.venv`, `.git`, etc.
- Output files are created in the current working directory
- Work silently and efficiently

## FastAPI Schema Fetching

When FastAPI is detected:
1. Use Grep to search for `from fastapi import|import fastapi` in `.py` files
2. If found, inform user that FastAPI was detected
3. Run `bash ./claude-helpers/fetch_openapi.sh http://localhost:8000 thoughts/codebase/openapi.json`
4. The script will:
   - Check if server is running at `/health` endpoint
   - Fetch OpenAPI schema from `/openapi.json`
   - Save to `thoughts/codebase/openapi.json`
   - Display schema information if available
5. **IMPORTANT - User Feedback**:
   - If the script succeeds, inform user: "✅ OpenAPI schema fetched successfully"
   - If the script fails (server not running), inform user: "⚠️ FastAPI server not running - OpenAPI schema not fetched. Start server and re-run if needed."
   - Show the output from the fetch script to provide full context
6. Continue with normal Python indexing regardless of OpenAPI fetch result

## Output Directory

**IMPORTANT**: Before running any indexer, ensure `thoughts/codebase/` directory exists:
- If it doesn't exist, create it with `mkdir -p thoughts/codebase/`
- All output files go to `thoughts/codebase/` with directory-based naming:
  - `codebase_overview_<dirname>_py.md` - Python documentation
  - `codebase_overview_<dirname>_ts.md` - TypeScript documentation
  - `openapi.json` - FastAPI OpenAPI schema (if applicable)

**Filename Examples:**
- Scanning `./` (Python) → `codebase_overview_root_py.md`
- Scanning `./` (TypeScript) → `codebase_overview_root_ts.md`
- Scanning `./backend` → `codebase_overview_backend_py.md`
- Scanning `./server` → `codebase_overview_server_py.md`
- Scanning `./api` → `codebase_overview_api_py.md`
- Scanning `./cc_wrapper/backend` → `codebase_overview_backend_py.md`
- Scanning `./frontend` → `codebase_overview_frontend_ts.md`
- Scanning `./client` → `codebase_overview_client_ts.md`
- Scanning `./web` → `codebase_overview_web_ts.md`
- Scanning `./cc_wrapper/frontend` → `codebase_overview_frontend_ts.md`
- Scanning `./src` (standalone) → `codebase_overview_src_ts.md`
