#!/bin/bash
# Finder Environment Wrapper for Claude Flow
#
# Purpose: When the app is double-clicked from Finder, macOS doesn't set up
# the environment properly (no cwd, missing env vars). This wrapper:
# 1. Derives the repository root from the app bundle location (6 levels up)
# 2. Changes to that directory so Path.cwd() returns the correct repo
# 3. Sets up missing environment variables (PATH, LANG, etc.)
# 4. Launches the actual claude-flow executable

# Get the directory where this script is located (Contents/MacOS/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Derive the repository root from the app bundle location
# Path: <repo>/claude-helpers/claude-flow/dist/Claude Flow.app/Contents/MacOS/finder-env-wrapper
# DIR = .../Contents/MacOS
# ../ = Contents, ../../ = Claude Flow.app, ../../../ = dist
# ../../../../ = claude-flow, ../../../../../ = claude-helpers, ../../../../../../ = REPO
REPO_ROOT="$( cd "$DIR/../../../../../../" && pwd )"

# Set up logging
LOG_FILE="$HOME/Library/Logs/claude-flow-finder-wrapper.log"
exec > "$LOG_FILE" 2>&1

echo "=== Claude Flow Finder Environment Wrapper ==="
echo "Started at: $(date)"
echo "Script directory: $DIR"
echo "Derived repo root: $REPO_ROOT"
echo "Current working directory: $(pwd)"

# Change to the repository root directory
# This ensures Path.cwd() returns the correct repo path
if [ -d "$REPO_ROOT/.git" ] || [ -f "$REPO_ROOT/CLAUDE.md" ]; then
    cd "$REPO_ROOT"
    echo "Changed to repo root: $(pwd)"
else
    # Fallback: if not a valid repo, use home directory
    echo "WARNING: $REPO_ROOT doesn't look like a repo, falling back to HOME"
    cd "$HOME" || cd /tmp
    echo "Changed working directory to: $(pwd)"
fi

# Set environment variables that might be missing when launched from Finder
export HOME="${HOME}"
export USER="${USER}"
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"

# Set locale if not set (common issue from search results)
if [ -z "$LANG" ]; then
    export LANG="en_US.UTF-8"
    export LC_ALL="en_US.UTF-8"
fi

echo "Environment set up complete"
echo "Launching claude-flow..."

# Launch the actual executable
exec "$DIR/claude-flow"
