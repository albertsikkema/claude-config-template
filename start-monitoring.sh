#!/bin/bash

set -e

MONITORING_DIR="claude-code-hooks-multi-agent-observability"
MONITORING_REPO="https://github.com/disler/claude-code-hooks-multi-agent-observability"
FORCE_INSTALL=false
SKIP_HOOKS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force-install)
            FORCE_INSTALL=true
            shift
            ;;
        --skip-hooks)
            SKIP_HOOKS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force-install    Force reinstall of all dependencies"
            echo "  --skip-hooks       Skip hooks setup (use if you have custom hooks)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "==================================================================="
echo "Claude Code Orchestrator - Monitoring Dashboard Setup"
echo "==================================================================="
echo ""

# Check if Bun is installed
if ! command -v bun &> /dev/null; then
    echo "❌ Bun is not installed"
    echo ""
    echo "Please install Bun first:"
    echo "  - macOS/Linux: curl -fsSL https://bun.sh/install | bash"
    echo "  - Or visit: https://bun.sh"
    echo ""
    echo "After installation, restart your terminal or run:"
    echo "  source ~/.zshrc  # or ~/.bashrc"
    exit 1
fi

echo "✓ Bun found: $(bun --version)"
echo ""

# Check if monitoring directory exists
if [ ! -d "$MONITORING_DIR" ]; then
    echo "📥 Cloning monitoring dashboard repository..."
    git clone "$MONITORING_REPO"
    echo ""

    # Add to .gitignore
    echo "📝 Updating .gitignore..."
    GITIGNORE_PATH=".gitignore"

    # Create .gitignore if it doesn't exist
    if [ ! -f "$GITIGNORE_PATH" ]; then
        touch "$GITIGNORE_PATH"
    fi

    # Check if entry already exists in .gitignore
    if grep -qxF "$MONITORING_DIR/" "$GITIGNORE_PATH" 2>/dev/null; then
        echo "  ⊘ $MONITORING_DIR/ already in .gitignore"
    else
        # Add entry to .gitignore
        echo "$MONITORING_DIR/" >> "$GITIGNORE_PATH"
        echo "  ✓ Added $MONITORING_DIR/ to .gitignore"
    fi
    echo ""
fi

cd "$MONITORING_DIR"
echo ""

# Set up hooks
if [ "$SKIP_HOOKS" = true ]; then
    echo "⏭️  Skipping hooks setup (--skip-hooks flag used)"
    echo ""
else
    echo "🔗 Setting up Claude Code hooks..."

    if [ -d ".claude/hooks" ]; then
        # Create hooks directory in parent project if it doesn't exist
        mkdir -p "../.claude/hooks"

        # Copy hooks to parent project
        echo "  Copying hook scripts..."
        cp -r .claude/hooks/* "../.claude/hooks/"
        echo "  ✓ Hooks copied to .claude/hooks/"

        # Merge hooks configuration into settings.json
        if [ -f ".claude/settings.json" ]; then
            echo "  Merging hooks into .claude/settings.json..."

            if command -v python3 &> /dev/null; then
                # Python script to merge hooks into settings.json
                python3 << 'EOF'
import json
import os

# Load hooks from monitoring repo's settings.json
with open('.claude/settings.json', 'r') as f:
    monitoring_settings = json.load(f)
    monitoring_hooks = monitoring_settings.get('hooks', {})

# Load existing settings.json or create new one
settings_path = '../.claude/settings.json'
if os.path.exists(settings_path):
    with open(settings_path, 'r') as f:
        settings = json.load(f)
else:
    settings = {}

# Merge hooks
settings['hooks'] = monitoring_hooks

# Save back to settings.json
with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)

print("  ✓ Hooks merged into .claude/settings.json")
EOF
            else
                echo "  ⚠️  Python3 not found, cannot merge hooks configuration"
                echo "     You may need to manually copy hooks to .claude/settings.json"
            fi
        else
            echo "  ⚠️  No settings.json found in monitoring repo"
        fi
    else
        echo "  ⚠️  No hooks directory found in monitoring repo"
    fi
    echo ""
fi

# Install dependencies
echo "📦 Checking and installing dependencies..."
if [ "$FORCE_INSTALL" = true ]; then
    echo "⚠️  Force install mode: Will reinstall all dependencies"
fi
echo ""

# Server dependencies
echo "🔧 Server dependencies:"
cd apps/server
if [ "$FORCE_INSTALL" = true ] && [ -d "node_modules" ]; then
    echo "  Removing existing server dependencies..."
    rm -rf node_modules
fi
if [ ! -d "node_modules" ]; then
    echo "  Installing server dependencies..."
    bun install || { echo "❌ Failed to install server dependencies"; exit 1; }
    echo "  ✓ Server dependencies installed"
else
    echo "  ✓ Server dependencies already installed (skipping)"
fi

# Client dependencies
echo ""
echo "🎨 Client (frontend) dependencies:"
cd ../client
if [ "$FORCE_INSTALL" = true ] && [ -d "node_modules" ]; then
    echo "  Removing existing client dependencies..."
    rm -rf node_modules
fi
if [ ! -d "node_modules" ]; then
    echo "  Installing client dependencies..."
    bun install || { echo "❌ Failed to install client dependencies"; exit 1; }
    echo "  ✓ Client dependencies installed"
else
    echo "  ✓ Client dependencies already installed (skipping)"
fi
cd ../..

echo ""
echo "==================================================================="
echo "🚀 Starting Monitoring Dashboard"
echo "==================================================================="
echo ""
echo "Services will start on:"
echo "  • Server API:  http://localhost:4000"
echo "  • Dashboard:   http://localhost:5173"
echo ""
echo "💡 Helper scripts (run from this directory):"
echo "  • Reset/stop:  ./$MONITORING_DIR/scripts/reset-system.sh"
echo "  • Test system: ./$MONITORING_DIR/scripts/test-system.sh"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Use the provided start script
./scripts/start-system.sh
