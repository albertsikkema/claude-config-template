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
    local warnings=()

    if [ "$INSTALL_CLAUDE" = true ] && check_exists ".claude"; then
        warnings+=(".claude/ directory already exists")
    fi

    if [ "$INSTALL_THOUGHTS" = true ] && check_exists "thoughts"; then
        warnings+=("thoughts/ directory already exists")
    fi

    # Show warnings and get confirmation
    if [ ${#warnings[@]} -gt 0 ]; then
        echo ""
        print_message "$YELLOW" "⚠️  Warning: The following items already exist:"
        for warning in "${warnings[@]}"; do
            print_message "$YELLOW" "  - $warning"
        done
        echo ""

        if ! confirm "Do you want to continue? Existing files may be overwritten."; then
            print_message "$YELLOW" "Installation cancelled."
            exit 0
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

        # Install settings.local.json
        if [ -f "$SCRIPT_DIR/.claude/settings.local.json" ]; then
            print_message "$BLUE" "Installing settings..."

            if check_exists ".claude/settings.local.json" && [ "$FORCE_INSTALL" != true ]; then
                if confirm "settings.local.json already exists. Do you want to overwrite it?"; then
                    install_item "$SCRIPT_DIR/.claude/settings.local.json" "$TARGET_DIR/.claude/settings.local.json" "settings.local.json"
                else
                    print_message "$YELLOW" "  ⊘ Skipped: settings.local.json (already exists)"
                fi
            else
                install_item "$SCRIPT_DIR/.claude/settings.local.json" "$TARGET_DIR/.claude/settings.local.json" "settings.local.json"
            fi
        fi
    fi

    # Install thoughts structure
    if [ "$INSTALL_THOUGHTS" = true ]; then
        print_header "Installing thoughts/ Structure"

        # Create directory structure
        print_message "$BLUE" "Creating directory structure..."
        if [ "$DRY_RUN" != true ]; then
            mkdir -p "$TARGET_DIR/thoughts/docs"
            mkdir -p "$TARGET_DIR/thoughts/shared/plans"
            mkdir -p "$TARGET_DIR/thoughts/shared/research"
        fi
        print_message "$GREEN" "  ✓ Created directory structure"

        # Install template files
        if [ -d "$SCRIPT_DIR/thoughts/docs" ]; then
            print_message "$BLUE" "Installing documentation templates..."
            for template in "$SCRIPT_DIR/thoughts/docs"/*.template; do
                if [ -f "$template" ]; then
                    local template_name=$(basename "$template")
                    local target_name="${template_name%.template}"

                    # Check if non-template version exists
                    if check_exists "thoughts/docs/$target_name" && [ "$FORCE_INSTALL" != true ]; then
                        print_message "$YELLOW" "  ⊘ Skipped: $target_name (already exists)"
                    else
                        install_item "$template" "$TARGET_DIR/thoughts/docs/$target_name" "docs/$target_name"
                    fi
                fi
            done
        fi

        # Install .gitkeep files
        if [ "$DRY_RUN" != true ]; then
            touch "$TARGET_DIR/thoughts/shared/plans/.gitkeep"
            touch "$TARGET_DIR/thoughts/shared/research/.gitkeep"
        fi
        print_message "$GREEN" "  ✓ Created .gitkeep files"
    fi

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
            echo "  4. Customize documentation templates in thoughts/docs/"
            echo "  5. Start creating plans in thoughts/shared/plans/"
            echo "  6. Document research in thoughts/shared/research/"
        fi

        echo ""
        print_message "$BLUE" "For more information, see README.md in the config repository."
    fi
}

# Run main function
main
