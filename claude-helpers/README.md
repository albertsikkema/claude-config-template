# Claude Helpers

Utility scripts for Claude Code workflows.

## Overview

This directory contains helper scripts that power Claude Code slash commands and automate common development tasks:

- **Codebase Indexers** - Generate searchable documentation for Python, TypeScript, and Go
- **Documentation Fetcher** - Download LLM-optimized docs from context7.com
- **OpenAPI Fetcher** - Extract API schemas from FastAPI servers
- **Metadata Generator** - Capture development context and session information

## Quick Reference

| Script | Purpose | Documentation |
|--------|---------|---------------|
| `index_python.py` | Index Python codebases | [docs/README-indexers.md](../docs/README-indexers.md) |
| `index_ts.py` | Index TypeScript/React codebases | [docs/README-indexers.md](../docs/README-indexers.md) |
| `index_go.py` | Index Go codebases | [docs/README-indexers.md](../docs/README-indexers.md) |
| `fetch-docs.py` | Fetch documentation from context7.com | [docs/README-fetch-docs.md](../docs/README-fetch-docs.md) |
| `fetch_openapi.sh` | Fetch OpenAPI schemas from FastAPI | [docs/README-fetch-openapi.md](../docs/README-fetch-openapi.md) |
| `spec_metadata.sh` | Generate metadata for documents | [docs/README-spec-metadata.md](../docs/README-spec-metadata.md) |

