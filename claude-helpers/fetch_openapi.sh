#!/bin/bash
# Fetch OpenAPI schema from running FastAPI server

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
OUTPUT_FILE="${2:-openapi.json}"

echo "============================================================"
echo "FastAPI OpenAPI Schema Fetcher (curl)"
echo "============================================================"
echo "Fetching from: ${BASE_URL}/openapi.json"
echo "Output file: ${OUTPUT_FILE}"
echo ""

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "❌ Error: curl is not installed"
    exit 1
fi

# Check if server is running
if ! curl -s -f -o /dev/null --connect-timeout 2 "${BASE_URL}/health"; then
    echo "❌ Error: Server is not running at ${BASE_URL}"
    echo ""
    echo "Please start the server first:"
    echo "   cd cc_wrapper/backend"
    echo "   uvicorn app.main:app --reload"
    exit 1
fi

# Fetch OpenAPI schema
echo "Fetching schema..."
if curl -s -f "${BASE_URL}/openapi.json" -o "${OUTPUT_FILE}"; then
    echo "✅ OpenAPI schema saved to: ${OUTPUT_FILE}"
    echo ""

    # Show some info about the schema (requires jq)
    if command -v jq &> /dev/null; then
        echo "Schema information:"
        echo "   Title: $(jq -r '.info.title' "${OUTPUT_FILE}")"
        echo "   Version: $(jq -r '.info.version' "${OUTPUT_FILE}")"
        echo "   Description: $(jq -r '.info.description' "${OUTPUT_FILE}")"
        echo "   Endpoints: $(jq '.paths | length' "${OUTPUT_FILE}")"
    fi

    echo ""
    echo "============================================================"
    echo "💡 You can now:"
    echo "   - View: cat ${OUTPUT_FILE}"
    echo "   - Pretty print: jq . ${OUTPUT_FILE}"
    echo "   - Interactive docs: open ${BASE_URL}/docs"
    echo "============================================================"
else
    echo "❌ Error: Failed to fetch OpenAPI schema"
    exit 1
fi
