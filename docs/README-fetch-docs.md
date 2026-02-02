# Scripts

Utility scripts for the WorkflowManager project.

## fetch-docs.py

**Simple, LLM-driven documentation fetcher from [context7.com](https://context7.com)**

A lightweight Python script that discovers packages and fetches documentation. Designed to work with the `/fetch_technical_docs` slash command where Claude makes intelligent decisions about which documentation to download.

### Quick Start

Use the Claude Code slash command (recommended):

```
/fetch_technical_docs
```

Claude will:
1. Discover all packages in your project
2. Identify core frameworks
3. Search context7 for each package
4. Intelligently select the best documentation
5. Download and save to `memories/technical_docs/`

### Script Commands

The script has three simple commands, all outputting JSON for easy parsing:

#### 1. Discover Packages

Find all packages from project configuration files:

```bash
python3 scripts/fetch-docs.py discover
```

**Scans:**
- `frontend/package.json` - JavaScript/TypeScript packages
- `go.mod` - Go packages
- `pyproject.toml` - Python packages (Poetry/setuptools)

**Output:**
```json
{
  "total": 57,
  "packages": {
    "svelte": {
      "version": "^5.0.0",
      "source": "package.json",
      "original": "svelte"
    },
    "wails": {
      "version": "v2.10.2",
      "source": "go.mod",
      "original": "github.com/wailsapp/wails/v2"
    }
  }
}
```

#### 2. Search for Package

Search context7 and return top 5 results:

```bash
python3 scripts/fetch-docs.py search <query>
```

**Examples:**
```bash
# Search for Svelte (returns top 5)
python3 scripts/fetch-docs.py search svelte

# Search with custom limit
python3 scripts/fetch-docs.py search vite 10
```

**Output:**
```json
{
  "query": "svelte",
  "count": 5,
  "results": [
    {
      "rank": 1,
      "project": "/sveltejs/svelte",
      "title": "Svelte",
      "description": "Svelte is a compiler that transforms...",
      "stars": 82465,
      "trustScore": 8.1,
      "vip": true,
      "type": "repo",
      "url": "https://context7.com/sveltejs/svelte/llms.txt"
    }
  ]
}
```

**Result fields:**
- `rank` - Position (1-5)
- `project` - Context7 project path (e.g., `/sveltejs/svelte`)
- `title` - Project title
- `description` - Project description
- `stars` - GitHub stars (-1 if N/A)
- `trustScore` - Quality score 0-10 (-1 if not scored)
- `vip` - Official/VIP status (boolean)
- `type` - `repo`, `website`, or `llmstxt`
- `url` - Direct URL to llms.txt file

#### 3. Get Documentation

Fetch documentation for a specific context7 project:

```bash
python3 scripts/fetch-docs.py get <project-path> <package-name>
```

**Examples:**
```bash
# Get Svelte documentation
python3 scripts/fetch-docs.py get /sveltejs/svelte svelte

# Overwrite existing file
python3 scripts/fetch-docs.py get /sveltejs/kit sveltekit --overwrite
```

**Output on success:**
```json
{
  "success": true,
  "project": "/sveltejs/svelte",
  "package": "svelte",
  "file": "memories/technical_docs/svelte.md"
}
```

**Output on failure:**
```json
{
  "success": false,
  "project": "/sveltejs/svelte",
  "package": "svelte"
}
```

### Output Format

Documentation is saved to `memories/technical_docs/{package-name}.md`:

```markdown
# {package-name}

**Source**: context7.com{project-path}
**Last Updated**: 2025-10-18
**URL**: https://context7.com{project-path}/llms.txt

---

{LLM-optimized documentation content}
```

### How the /fetch_technical_docs Workflow Works

When you run `/fetch_technical_docs`, Claude follows this intelligent workflow:

1. **Discover** all packages using `discover` command
2. **Identify** core frameworks (Svelte, Vite, Wails, etc.)
3. For each package:
   - **Search** using `search` command
   - **Analyze** top 5 results
   - **Select** best match based on:
     - VIP status (official repos)
     - Type (repo > website > llmstxt)
     - Trust score (higher is better)
     - GitHub stars (popularity)
     - Official organization match
   - **Fetch** using `get` command
   - **Confirm** success
4. **Report** summary of all downloads

### Multi-Language Support

The script automatically detects and parses:

**JavaScript/TypeScript** (`package.json`):
```json
{
  "dependencies": {
    "svelte": "^5.0.0",
    "@sveltejs/kit": "^2.22.0"
  }
}
```

**Go** (`go.mod`):
```go
require (
    github.com/wailsapp/wails/v2 v2.10.2
    github.com/google/uuid v1.6.0
)
```

**Python** (`pyproject.toml`):
```toml
[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.104.0"
```

### Selection Criteria (for LLM)

When Claude analyzes search results, it prioritizes:

1. **VIP Status** - Official repositories marked as VIP
2. **Type**:
   - `repo` - Source code repository (preferred)
   - `website` - Documentation website (good)
   - `llmstxt` - Custom llms.txt (last resort)
3. **Trust Score**:
   - 8.0-10.0: Excellent
   - 6.0-7.9: Good
   - 4.0-5.9: Moderate
   - < 4.0: Low quality
4. **Stars** - GitHub popularity (higher is better)
5. **Organization**:
   - `/sveltejs/` for Svelte
   - `/tailwindlabs/` for Tailwind
   - `/vitejs/` for Vite
   - `/wailsapp/` for Wails
   - `/golang/` for Go

### Prerequisites

- **Python 3.6+** (uses standard library only)
- No external dependencies required

### Error Handling

**If package not found:**
- Try different search term
- Check original package name
- Skip if not critical

**If fetch fails:**
- llms.txt might not exist for that project
- Try next best search result
- Report to user

**If file exists:**
- Use `--overwrite` flag to replace
- Or skip and keep existing file

### Design Philosophy

This script is intentionally simple:

✅ **JSON output** - Easy to parse programmatically
✅ **No opinions** - Just fetch what you ask for
✅ **LLM-friendly** - Claude makes the smart decisions
✅ **Multi-language** - Supports JS/TS, Go, Python
✅ **No dependencies** - Python stdlib only

The intelligence lives in the `/fetch_technical_docs` slash command, where Claude analyzes results and makes context-aware decisions.

### Example Usage in Scripts

The script outputs JSON, making it easy to use in automation:

```bash
# Get all packages
packages=$(python3 scripts/fetch-docs.py discover | jq -r '.packages | keys[]')

# Search for each core package
for pkg in $packages; do
    python3 scripts/fetch-docs.py search "$pkg" | jq '.results[0]'
done

# Fetch specific documentation
python3 scripts/fetch-docs.py get /sveltejs/svelte svelte
```

### API Reference

**Context7 Search API:**
```
GET https://context7.com/api/search?query={package-name}
```

**Context7 Documentation:**
```
GET https://context7.com{project-path}/llms.txt
```

Returns LLM-optimized markdown documentation.

### Why context7?

[context7.com](https://context7.com) provides curated, LLM-optimized documentation:

- ✅ Up-to-date from official sources
- ✅ Optimized format for AI assistants
- ✅ Comprehensive API coverage
- ✅ Trust scores and verification
- ✅ Multiple source types
- ✅ Free and open access

The `llms.txt` format is specifically designed for consumption by LLMs like Claude.
