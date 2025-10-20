#!/bin/bash
# Fetch OpenAPI schema from running FastAPI server

set -e

# Configuration
BASE_URL_INPUT="${1:-auto}"
OUTPUT_FILE="${2:-openapi.json}"

echo "============================================================"
echo "FastAPI OpenAPI Schema Fetcher (curl)"
echo "============================================================"

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "❌ Error: curl is not installed"
    exit 1
fi

# Auto-detect running server if "auto" is specified
if [ "$BASE_URL_INPUT" = "auto" ]; then
    echo "🔍 Auto-detecting FastAPI server on ports 8000-8010..."
    echo ""

    BASE_URL=""
    for port in {8000..8010}; do
        test_url="http://localhost:$port"
        echo -n "   Checking $test_url... "

        # Try /health first, then /docs, then /openapi.json
        if curl -s -f -o /dev/null --connect-timeout 1 "${test_url}/health" 2>/dev/null || \
           curl -s -f -o /dev/null --connect-timeout 1 "${test_url}/docs" 2>/dev/null || \
           curl -s -f -o /dev/null --connect-timeout 1 "${test_url}/openapi.json" 2>/dev/null; then
            echo "✅ Found!"
            BASE_URL="$test_url"
            break
        else
            echo "❌"
        fi
    done

    if [ -z "$BASE_URL" ]; then
        echo ""
        echo "❌ Error: No FastAPI server detected on ports 8000-8010"
        echo ""
        echo "Please either:"
        echo "   1. Start your FastAPI server, or"
        echo "   2. Specify the URL explicitly:"
        echo "      bash $0 http://localhost:YOUR_PORT $OUTPUT_FILE"
        exit 1
    fi

    echo ""
    echo "🎯 Using detected server: $BASE_URL"
else
    BASE_URL="$BASE_URL_INPUT"
    echo "Using specified URL: ${BASE_URL}"

    # Check if server is running
    echo -n "Checking server... "
    if ! curl -s -f -o /dev/null --connect-timeout 2 "${BASE_URL}/health" 2>/dev/null && \
       ! curl -s -f -o /dev/null --connect-timeout 2 "${BASE_URL}/docs" 2>/dev/null && \
       ! curl -s -f -o /dev/null --connect-timeout 2 "${BASE_URL}/openapi.json" 2>/dev/null; then
        echo "❌"
        echo ""
        echo "❌ Error: Server is not running at ${BASE_URL}"
        echo ""
        echo "Please start the server first or use 'auto' to auto-detect:"
        echo "   bash $0 auto $OUTPUT_FILE"
        exit 1
    fi
    echo "✅"
fi

echo "Output file: ${OUTPUT_FILE}"
echo ""

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
