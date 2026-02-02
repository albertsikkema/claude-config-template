# FastAPI OpenAPI Schema Fetcher

Automatically fetch OpenAPI/Swagger schemas from running FastAPI servers.

## Overview

`fetch_openapi.sh` is a simple bash script that:
- ✅ Checks if your FastAPI server is running
- ✅ Fetches the OpenAPI schema from `/openapi.json`
- ✅ Saves it to a file for documentation
- ✅ Displays schema information (title, version, endpoint count)

## Quick Start

### Basic Usage

```bash
# Auto-detect running server on ports 8000-8010 (RECOMMENDED)
bash .claude/helpers/fetch_openapi.sh auto

# Fetch from default localhost:8000
bash .claude/helpers/fetch_openapi.sh

# Fetch from custom URL
bash .claude/helpers/fetch_openapi.sh http://localhost:5000

# Custom output file
bash .claude/helpers/fetch_openapi.sh auto my-api-schema.json
bash .claude/helpers/fetch_openapi.sh http://localhost:8000 my-api-schema.json
```

### Via `/index_codebase` Command

The script is automatically invoked when Claude detects FastAPI in your Python code:

```bash
/index_codebase
```

Claude will:
1. Scan for FastAPI imports
2. Auto-detect running server on ports 8000-8010
3. Automatically fetch OpenAPI schema
4. Save to `memories/codebase/openapi.json`

## Usage

```bash
bash .claude/helpers/fetch_openapi.sh [BASE_URL] [OUTPUT_FILE]

Arguments:
  BASE_URL      Base URL of FastAPI server or "auto" to auto-detect (default: auto)
                When "auto", scans ports 8000-8010 for running FastAPI servers
  OUTPUT_FILE   Output JSON file (default: openapi.json)
```

## Examples

### Development Server

```bash
# Auto-detect (RECOMMENDED - works with any port 8000-8010)
bash .claude/helpers/fetch_openapi.sh auto
# → Scans ports 8000-8010
# → Automatically finds running server
# → Saves to openapi.json

# Default settings (assumes port 8000)
bash .claude/helpers/fetch_openapi.sh
# → Fetches from http://localhost:8000
# → Saves to openapi.json

# Custom port
bash .claude/helpers/fetch_openapi.sh http://localhost:5000
# → Fetches from http://localhost:5000
# → Saves to openapi.json
```

### Production Server

```bash
# Staging environment
bash .claude/helpers/fetch_openapi.sh https://staging-api.example.com staging-api.json

# Production environment
bash .claude/helpers/fetch_openapi.sh https://api.example.com production-api.json
```

### Save to Thoughts Directory

```bash
# Organized storage
bash .claude/helpers/fetch_openapi.sh http://localhost:8000 memories/codebase/openapi.json
```

## How It Works

### 1. Auto-Detection (when using "auto")

The script scans ports 8000-8010 to find a running FastAPI server:

```bash
# Tests each port with multiple endpoints
for port in 8000-8010:
  - Try /health
  - Try /docs
  - Try /openapi.json
```

**Benefits:**
- No need to specify port manually
- Works regardless of which port your server is on
- Faster development workflow

### 2. Server Health Check

The script checks if your server is running:

```bash
curl -s -f -o /dev/null --connect-timeout 2 "${BASE_URL}/health"
```

**Fallback checks:**
- If `/health` fails, tries `/docs`
- If `/docs` fails, tries `/openapi.json`

**If server is not running:**
```
❌ Error: No FastAPI server detected on ports 8000-8010

Please either:
   1. Start your FastAPI server, or
   2. Specify the URL explicitly:
      bash ./.claude/helpers/fetch_openapi.sh http://localhost:YOUR_PORT
```

### 3. Fetch OpenAPI Schema

If server is running, fetches the schema:

```bash
curl -s -f "${BASE_URL}/openapi.json" -o "${OUTPUT_FILE}"
```

### 4. Display Schema Info

Uses `jq` (if available) to show schema details:

```
✅ OpenAPI schema saved to: openapi.json

Schema information:
   Title: My FastAPI Application
   Version: 1.0.0
   Description: A production-ready FastAPI application
   Endpoints: 23
```

### 5. Next Steps

Provides helpful commands:

```
💡 You can now:
   - View: cat openapi.json
   - Pretty print: jq . openapi.json
   - Interactive docs: open http://localhost:8000/docs
```

## Output Format

The script saves the OpenAPI schema in JSON format:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "My API",
    "version": "1.0.0",
    "description": "FastAPI application"
  },
  "paths": {
    "/users": {
      "get": {
        "summary": "List Users",
        "responses": { ... }
      }
    },
    ...
  },
  "components": {
    "schemas": { ... }
  }
}
```

## Prerequisites

### Required

- **curl** - HTTP client (usually pre-installed)
  ```bash
  # Check if installed
  curl --version
  ```

### Optional

- **jq** - JSON processor (for pretty output)
  ```bash
  # macOS
  brew install jq

  # Ubuntu/Debian
  sudo apt-get install jq

  # Check if installed
  jq --version
  ```

**Without jq:**
- Script still works
- Schema info section is skipped
- Manual inspection required: `cat openapi.json`

## FastAPI Setup

### Add Health Endpoint

Your FastAPI app needs a `/health` endpoint:

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

### Start Server

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Common Use Cases

### Documentation Generation

```bash
# Fetch latest schema
bash .claude/helpers/fetch_openapi.sh

# Generate client SDK
openapi-generator-cli generate -i openapi.json -g python -o ./sdk

# Generate API documentation
redoc-cli bundle openapi.json -o api-docs.html
```

### API Testing

```bash
# Fetch schema
bash .claude/helpers/fetch_openapi.sh

# Import into Postman
# File → Import → openapi.json

# Use with Insomnia
# Application → Import/Export → Import Data → openapi.json
```

### Version Comparison

```bash
# Fetch current version
bash .claude/helpers/fetch_openapi.sh http://localhost:8000 current.json

# Fetch production version
bash .claude/helpers/fetch_openapi.sh https://api.example.com production.json

# Compare
diff current.json production.json
```

### CI/CD Integration

```bash
# In your CI pipeline
bash .claude/helpers/fetch_openapi.sh http://test-server:8000 openapi.json

# Validate schema
openapi-spec-validator openapi.json

# Store as artifact
cp openapi.json $ARTIFACTS_DIR/
```

## Troubleshooting

### "curl is not installed"

**Solution:**
```bash
# macOS
brew install curl

# Ubuntu/Debian
sudo apt-get install curl

# Verify
curl --version
```

### "Server is not running"

**Cause:** FastAPI server isn't started or `/health` endpoint missing

**Solution:**
```bash
# 1. Start server
uvicorn app.main:app --reload

# 2. Add health endpoint (see FastAPI Setup above)

# 3. Verify server is running
curl http://localhost:8000/health
```

### "Failed to fetch OpenAPI schema"

**Possible causes:**
- Server doesn't expose `/openapi.json`
- CORS issues (cross-origin requests)
- Authentication required

**Solutions:**
```bash
# 1. Verify endpoint exists
curl http://localhost:8000/openapi.json

# 2. Check FastAPI docs (should work if this works)
open http://localhost:8000/docs

# 3. Check server logs for errors
```

### Wrong port or URL

**Solution:**
```bash
# Use auto-detection (EASIEST)
bash .claude/helpers/fetch_openapi.sh auto

# Or specify correct URL
bash .claude/helpers/fetch_openapi.sh http://localhost:5000

# Check if server is on different port
lsof -i :8000
netstat -an | grep 8000

# Find all listening ports
lsof -i -P | grep LISTEN
```

### Permission denied writing file

**Solution:**
```bash
# Check directory permissions
ls -la

# Use writable directory
bash .claude/helpers/fetch_openapi.sh http://localhost:8000 /tmp/openapi.json

# Or fix permissions
chmod +w .
```

## Integration with Claude Code

### Automatic Invocation

When using `/index_codebase`, Claude:

1. **Detects FastAPI:**
   ```bash
   grep -r "from fastapi import\|import fastapi" --include="*.py"
   ```

2. **Runs script with auto-detection:**
   ```bash
   bash .claude/helpers/fetch_openapi.sh auto memories/codebase/openapi.json
   ```

3. **Reports results:**
   - ✅ Success: "OpenAPI schema fetched successfully from http://localhost:XXXX"
   - ⚠️ Failure: "FastAPI server not detected on ports 8000-8010"

### Manual Invocation

You can also ask Claude directly:

```
You: Fetch the OpenAPI schema from my FastAPI server

Claude: I'll fetch the OpenAPI schema using the fetch_openapi.sh script.
[Runs script and reports results]
```

## Advanced Usage

### Multiple Environments

```bash
# Create environment-specific schemas
bash .claude/helpers/fetch_openapi.sh http://localhost:8000 dev-openapi.json
bash .claude/helpers/fetch_openapi.sh https://staging.example.com staging-openapi.json
bash .claude/helpers/fetch_openapi.sh https://api.example.com prod-openapi.json
```

### Custom FastAPI Configuration

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="My Custom API",
    version="2.0.0",
    description="Production API with custom OpenAPI config",
    openapi_url="/api/v1/openapi.json",  # Custom path
)
```

**Fetch from custom path:**
```bash
# Modify script or use curl directly
curl http://localhost:8000/api/v1/openapi.json -o openapi.json
```

### Schema Validation

```bash
# Fetch schema
bash .claude/helpers/fetch_openapi.sh

# Validate with openapi-spec-validator
pip install openapi-spec-validator
openapi-spec-validator openapi.json

# Validate with spectral
npm install -g @stoplight/spectral-cli
spectral lint openapi.json
```

## Customization

### Expanding Port Range

If your FastAPI server runs on a port outside 8000-8010, you can:

**Option 1: Specify URL explicitly**
```bash
bash .claude/helpers/fetch_openapi.sh http://localhost:9000
```

**Option 2: Edit the script** (edit `.claude/helpers/fetch_openapi.sh:26`)
```bash
# Change from:
for port in {8000..8010}; do

# To your preferred range:
for port in {8000..8020}; do
```

### Custom Health Endpoints

The script checks multiple endpoints in order:
1. `/health` (recommended)
2. `/docs` (FastAPI default)
3. `/openapi.json` (schema itself)

If your app uses a different health endpoint, add it to the script at line 31-33.

## Tips & Best Practices

### 1. Keep Schema Updated

```bash
# Before making API changes
bash .claude/helpers/fetch_openapi.sh

# After making API changes
bash .claude/helpers/fetch_openapi.sh

# Compare
diff openapi-before.json openapi-after.json
```

### 2. Version Control

```bash
# Add to .gitignore (temporary schemas)
echo "openapi.json" >> .gitignore

# Or commit (stable schemas)
git add openapi.json
git commit -m "docs: Update OpenAPI schema"
```

### 3. Document API Changes

```bash
# Fetch schema
bash .claude/helpers/fetch_openapi.sh

# Use with API changelog tools
npx openapi-diff openapi-old.json openapi.json
```

## Related Tools

- **Swagger UI**: Interactive API documentation
- **ReDoc**: Clean API documentation
- **Postman**: API testing with OpenAPI import
- **openapi-generator**: Generate client SDKs
- **spectral**: OpenAPI linting

## See Also

- [index_*.py](README-indexers.md) - Codebase indexing tools
- [/index_codebase command](../.claude/commands/index_codebase.md) - Auto-indexing workflow
- [FastAPI Documentation](https://fastapi.tiangolo.com/advanced/extending-openapi/)
