#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default options
INSTALL_CLAUDE=true
INSTALL_THOUGHTS=true
FORCE_INSTALL=false
DRY_RUN=false
TARGET_DIR="."

# Version
VERSION="1.0.0"

# Usage information
usage() {
    cat << EOF
Claude Code Configuration Installer v${VERSION}

Usage: $0 [OPTIONS] [TARGET_DIR]

OPTIONS:
    --claude-only       Install only .claude/ configuration
    --thoughts-only     Install only thoughts/ structure
    --force, -f         Force overwrite existing files without prompting
    --dry-run           Show what would be installed without making changes
    --help, -h          Show this help message
    --version, -v       Show version information

ARGUMENTS:
    TARGET_DIR          Target directory for installation (default: current directory)

EXAMPLES:
    $0                          # Install everything in current directory
    $0 --claude-only            # Install only Claude configs
    $0 --dry-run                # Preview what will be installed
    $0 /path/to/project         # Install in specific directory
    $0 --force --thoughts-only  # Force install thoughts structure

EOF
    exit 0
}

# Version information
version() {
    echo "Claude Code Configuration Installer v${VERSION}"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --claude-only)
            INSTALL_CLAUDE=true
            INSTALL_THOUGHTS=false
            shift
            ;;
        --thoughts-only)
            INSTALL_CLAUDE=false
            INSTALL_THOUGHTS=true
            shift
            ;;
        --force|-f)
            FORCE_INSTALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        --version|-v)
            version
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
        *)
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print section header
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check if file/directory exists
check_exists() {
    local path="$1"
    if [ -e "$TARGET_DIR/$path" ]; then
        return 0
    else
        return 1
    fi
}

# Prompt for confirmation
confirm() {
    local message="$1"
    if [ "$FORCE_INSTALL" = true ]; then
        return 0
    fi

    echo -e "${YELLOW}${message} (y/N)${NC}"
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Copy file or directory
install_item() {
    local src="$1"
    local dest="$2"
    local description="$3"

    if [ "$DRY_RUN" = true ]; then
        print_message "$GREEN" "  [DRY RUN] Would install: $description"
        return 0
    fi

    # Create parent directory if it doesn't exist
    local dest_dir="$(dirname "$dest")"
    mkdir -p "$dest_dir"

    # Copy the file or directory
    if [ -d "$src" ]; then
        cp -r "$src" "$dest"
    else
        cp "$src" "$dest"
    fi

    print_message "$GREEN" "  ✓ Installed: $description"
}

# Update .gitignore with Claude Code entries
update_gitignore() {
    local gitignore_path="$TARGET_DIR/.gitignore"
    local entries_to_add=()

    # Determine which entries to add based on what was installed
    if [ "$INSTALL_CLAUDE" = true ]; then
        entries_to_add+=(".claude/")
        entries_to_add+=("claude-helpers/")
        entries_to_add+=(".env.claude")
    fi

    if [ "$INSTALL_THOUGHTS" = true ]; then
        entries_to_add+=("thoughts/")
    fi

    # If no entries to add, skip
    if [ ${#entries_to_add[@]} -eq 0 ]; then
        return 0
    fi

    print_header "Updating .gitignore"

    if [ "$DRY_RUN" = true ]; then
        print_message "$YELLOW" "  [DRY RUN] Would update .gitignore with:"
        for entry in "${entries_to_add[@]}"; do
            print_message "$YELLOW" "    - $entry"
        done
        return 0
    fi

    # Create .gitignore if it doesn't exist
    if [ ! -f "$gitignore_path" ]; then
        print_message "$BLUE" "Creating .gitignore..."
        touch "$gitignore_path"
    fi

    local added_entries=()
    local skipped_entries=()

    for entry in "${entries_to_add[@]}"; do
        # Check if entry already exists in .gitignore
        if grep -qxF "$entry" "$gitignore_path" 2>/dev/null; then
            skipped_entries+=("$entry")
        else
            # Add entry to .gitignore
            echo "$entry" >> "$gitignore_path"
            added_entries+=("$entry")
        fi
    done

    # Report what was done
    if [ ${#added_entries[@]} -gt 0 ]; then
        print_message "$GREEN" "  ✓ Added to .gitignore:"
        for entry in "${added_entries[@]}"; do
            print_message "$GREEN" "    - $entry"
        done
    fi

    if [ ${#skipped_entries[@]} -gt 0 ]; then
        print_message "$YELLOW" "  ⊘ Already in .gitignore:"
        for entry in "${skipped_entries[@]}"; do
            print_message "$YELLOW" "    - $entry"
        done
    fi
}

# Main installation function
main() {
    print_header "Claude Code Configuration Installer v${VERSION}"

    # Validate script directory
    if [ ! -d "$SCRIPT_DIR/.claude" ] && [ "$INSTALL_CLAUDE" = true ]; then
        print_message "$RED" "Error: .claude/ directory not found in script directory"
        exit 1
    fi

    if [ ! -d "$SCRIPT_DIR/thoughts" ] && [ "$INSTALL_THOUGHTS" = true ]; then
        print_message "$RED" "Error: thoughts/ directory not found in script directory"
        exit 1
    fi

    # Resolve target directory
    TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
    print_message "$BLUE" "Target directory: $TARGET_DIR"

    if [ "$DRY_RUN" = true ]; then
        print_message "$YELLOW" "DRY RUN MODE - No changes will be made"
    fi

    # Check for existing installations
    # .claude is always overwritten - just inform the user
    if [ "$INSTALL_CLAUDE" = true ] && check_exists ".claude"; then
        print_message "$BLUE" "Existing .claude/ will be overwritten"
    fi

    # thoughts preserves content by default - just inform the user
    if [ "$INSTALL_THOUGHTS" = true ] && check_exists "thoughts"; then
        if [ "$FORCE_INSTALL" != true ]; then
            print_message "$BLUE" "Existing thoughts/ found - missing folders will be added, content preserved"
        fi
    fi

    # Install .claude configuration
    if [ "$INSTALL_CLAUDE" = true ]; then
        print_header "Installing .claude/ Configuration"

        # Install agents
        if [ -d "$SCRIPT_DIR/.claude/agents" ]; then
            print_message "$BLUE" "Installing agents..."
            for agent in "$SCRIPT_DIR/.claude/agents"/*.md; do
                if [ -f "$agent" ]; then
                    local agent_name=$(basename "$agent")
                    install_item "$agent" "$TARGET_DIR/.claude/agents/$agent_name" "agents/$agent_name"
                fi
            done
        fi

        # Install commands
        if [ -d "$SCRIPT_DIR/.claude/commands" ]; then
            print_message "$BLUE" "Installing commands..."
            for command in "$SCRIPT_DIR/.claude/commands"/*.md; do
                if [ -f "$command" ]; then
                    local command_name=$(basename "$command")
                    install_item "$command" "$TARGET_DIR/.claude/commands/$command_name" "commands/$command_name"
                fi
            done
        fi

        # Install settings.local.json (always overwrite)
        if [ -f "$SCRIPT_DIR/.claude/settings.local.json" ]; then
            print_message "$BLUE" "Installing settings..."
            install_item "$SCRIPT_DIR/.claude/settings.local.json" "$TARGET_DIR/.claude/settings.local.json" "settings.local.json"
        fi

        # Install .gitkeep files
        if [ "$DRY_RUN" != true ]; then
            touch "$TARGET_DIR/.claude/agents/.gitkeep"
            touch "$TARGET_DIR/.claude/commands/.gitkeep"
        fi
        print_message "$GREEN" "  ✓ Created .gitkeep files"
    fi

    # Install thoughts structure
    if [ "$INSTALL_THOUGHTS" = true ]; then
        print_header "Installing thoughts/ Structure"

        # Copy entire thoughts directory structure
        if [ "$FORCE_INSTALL" = true ]; then
            print_message "$BLUE" "Replacing thoughts/ directory structure (overwrite mode)..."
            if [ "$DRY_RUN" != true ]; then
                # Remove existing directory and replace completely
                rm -rf "$TARGET_DIR/thoughts"
                cp -r "$SCRIPT_DIR/thoughts" "$TARGET_DIR/"
            fi
            print_message "$GREEN" "  ✓ Replaced thoughts/ directory structure"
        else
            print_message "$BLUE" "Adding missing directories and files..."
            if [ "$DRY_RUN" != true ]; then
                # Use rsync to copy only missing files and directories
                rsync -a --ignore-existing "$SCRIPT_DIR/thoughts/" "$TARGET_DIR/thoughts/"
            fi
            print_message "$GREEN" "  ✓ Added missing directories and files"
        fi

        # Remove .template extensions from template files
        if [ "$DRY_RUN" != true ]; then
            print_message "$BLUE" "Processing template files..."
            for template in "$TARGET_DIR/thoughts/templates"/*.template; do
                if [ -f "$template" ]; then
                    local target_name="${template%.template}"
                    mv "$template" "$target_name"
                    print_message "$GREEN" "  ✓ Processed: $(basename "$target_name")"
                fi
            done
        fi
    fi

    # Install claude-helpers
    if [ "$INSTALL_CLAUDE" = true ]; then
        if [ -d "$SCRIPT_DIR/claude-helpers" ]; then
            print_header "Installing claude-helpers/"
            print_message "$BLUE" "Copying claude-helpers/ directory..."
            if [ "$DRY_RUN" != true ]; then
                cp -r "$SCRIPT_DIR/claude-helpers" "$TARGET_DIR/"
            fi
            print_message "$GREEN" "  ✓ Copied claude-helpers/ directory"
        fi
    fi

    # Update .gitignore
    update_gitignore

    # Installation complete
    print_header "Installation Complete!"

    if [ "$DRY_RUN" = true ]; then
        print_message "$YELLOW" "This was a dry run. No changes were made."
        echo ""
        print_message "$BLUE" "Run without --dry-run to actually install."
    else
        echo ""
        print_message "$GREEN" "✓ Configuration installed successfully!"
        echo ""
        print_message "$BLUE" "Next steps:"

        if [ "$INSTALL_CLAUDE" = true ]; then
            echo "  1. Review .claude/settings.local.json and adjust permissions as needed"
            echo "  2. Explore available agents in .claude/agents/"
            echo "  3. Check out slash commands in .claude/commands/"
        fi

        if [ "$INSTALL_THOUGHTS" = true ]; then
            echo "  4. Review .gitignore for Claude Code entries"
            echo "  5. Use /project command to create project documentation"
            echo "  6. Start creating plans in thoughts/shared/plans/"
            echo "  7. Document research in thoughts/shared/research/"
        fi

        echo ""
        print_message "$BLUE" "For more information, see README.md in the config repository."
    fi
}

# Run main function
main
