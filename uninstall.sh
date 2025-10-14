#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
REMOVE_CLAUDE=true
REMOVE_THOUGHTS=true
FORCE_REMOVE=false
DRY_RUN=false
TARGET_DIR="."

# Version
VERSION="1.0.0"

# Usage information
usage() {
    cat << EOF
Claude Code Configuration Uninstaller v${VERSION}

Usage: $0 [OPTIONS] [TARGET_DIR]

OPTIONS:
    --claude-only       Remove only .claude/ configuration
    --thoughts-only     Remove only thoughts/ structure
    --force, -f         Force removal without prompting
    --dry-run           Show what would be removed without making changes
    --help, -h          Show this help message
    --version, -v       Show version information

ARGUMENTS:
    TARGET_DIR          Target directory for uninstallation (default: current directory)

EXAMPLES:
    $0                      # Remove everything from current directory
    $0 --claude-only        # Remove only Claude configs
    $0 --dry-run            # Preview what will be removed
    $0 /path/to/project     # Uninstall from specific directory

WARNING:
    This will permanently delete the .claude/ and/or thoughts/ directories!
    Use with caution. Use --dry-run to preview changes first.

EOF
    exit 0
}

# Version information
version() {
    echo "Claude Code Configuration Uninstaller v${VERSION}"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --claude-only)
            REMOVE_CLAUDE=true
            REMOVE_THOUGHTS=false
            shift
            ;;
        --thoughts-only)
            REMOVE_CLAUDE=false
            REMOVE_THOUGHTS=true
            shift
            ;;
        --force|-f)
            FORCE_REMOVE=true
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
    if [ "$FORCE_REMOVE" = true ]; then
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

# Remove item
remove_item() {
    local path="$1"
    local description="$2"

    if [ "$DRY_RUN" = true ]; then
        print_message "$YELLOW" "  [DRY RUN] Would remove: $description"
        return 0
    fi

    if [ -e "$path" ]; then
        rm -rf "$path"
        print_message "$GREEN" "  ✓ Removed: $description"
    else
        print_message "$YELLOW" "  ⊘ Not found: $description"
    fi
}

# Main uninstallation function
main() {
    print_header "Claude Code Configuration Uninstaller v${VERSION}"

    # Resolve target directory
    TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
    print_message "$BLUE" "Target directory: $TARGET_DIR"

    if [ "$DRY_RUN" = true ]; then
        print_message "$YELLOW" "DRY RUN MODE - No changes will be made"
    fi

    # Check what exists
    local items_to_remove=()

    if [ "$REMOVE_CLAUDE" = true ] && check_exists ".claude"; then
        items_to_remove+=(".claude/")
    fi

    if [ "$REMOVE_THOUGHTS" = true ] && check_exists "thoughts"; then
        items_to_remove+=("thoughts/")
    fi

    # Check if anything to remove
    if [ ${#items_to_remove[@]} -eq 0 ]; then
        print_message "$YELLOW" "No Claude Code configuration found to remove."
        exit 0
    fi

    # Show what will be removed
    echo ""
    print_message "$RED" "⚠️  WARNING: The following will be permanently deleted:"
    for item in "${items_to_remove[@]}"; do
        print_message "$RED" "  - $item"
    done
    echo ""

    # Get confirmation
    if ! confirm "Are you sure you want to proceed? This cannot be undone!"; then
        print_message "$YELLOW" "Uninstallation cancelled."
        exit 0
    fi

    # Remove .claude configuration
    if [ "$REMOVE_CLAUDE" = true ]; then
        print_header "Removing .claude/ Configuration"

        remove_item "$TARGET_DIR/.claude/agents" "agents/"
        remove_item "$TARGET_DIR/.claude/commands" "commands/"
        remove_item "$TARGET_DIR/.claude/settings.local.json" "settings.local.json"
        remove_item "$TARGET_DIR/.claude" ".claude/ directory"
    fi

    # Remove thoughts structure
    if [ "$REMOVE_THOUGHTS" = true ]; then
        print_header "Removing thoughts/ Structure"

        if [ "$DRY_RUN" != true ]; then
            # Check if there's any user content
            local has_user_content=false

            if [ -d "$TARGET_DIR/thoughts/shared/plans" ]; then
                local plan_count=$(find "$TARGET_DIR/thoughts/shared/plans" -type f -not -name ".gitkeep" | wc -l | tr -d ' ')
                if [ "$plan_count" -gt 0 ]; then
                    has_user_content=true
                fi
            fi

            if [ -d "$TARGET_DIR/thoughts/shared/research" ]; then
                local research_count=$(find "$TARGET_DIR/thoughts/shared/research" -type f -not -name ".gitkeep" | wc -l | tr -d ' ')
                if [ "$research_count" -gt 0 ]; then
                    has_user_content=true
                fi
            fi

            if [ -d "$TARGET_DIR/thoughts/shared/project" ]; then
                local project_count=$(find "$TARGET_DIR/thoughts/shared/project" -type f -not -name ".gitkeep" | wc -l | tr -d ' ')
                if [ "$project_count" -gt 0 ]; then
                    has_user_content=true
                fi
            fi

            if [ "$has_user_content" = true ]; then
                print_message "$YELLOW" "⚠️  Warning: thoughts/ contains user-created content!"

                if ! confirm "Do you really want to delete all plans, research, and project documents?"; then
                    print_message "$YELLOW" "  ⊘ Skipped: thoughts/ (contains user content)"
                    print_message "$BLUE" "Tip: Consider backing up your content before uninstalling."
                    exit 0
                fi
            fi
        fi

        remove_item "$TARGET_DIR/thoughts/templates" "templates/"
        remove_item "$TARGET_DIR/thoughts/shared/plans" "shared/plans/"
        remove_item "$TARGET_DIR/thoughts/shared/research" "shared/research/"
        remove_item "$TARGET_DIR/thoughts/shared/project/epics" "shared/project/epics/"
        remove_item "$TARGET_DIR/thoughts/shared/project" "shared/project/"
        remove_item "$TARGET_DIR/thoughts/shared" "shared/"
        remove_item "$TARGET_DIR/thoughts/technical_docs" "technical_docs/"
        remove_item "$TARGET_DIR/thoughts" "thoughts/ directory"
    fi

    # Uninstallation complete
    print_header "Uninstallation Complete!"

    if [ "$DRY_RUN" = true ]; then
        print_message "$YELLOW" "This was a dry run. No changes were made."
        echo ""
        print_message "$BLUE" "Run without --dry-run to actually uninstall."
    else
        echo ""
        print_message "$GREEN" "✓ Configuration removed successfully!"
        echo ""
        print_message "$BLUE" "To reinstall, run the install.sh script again."
    fi
}

# Run main function
main
