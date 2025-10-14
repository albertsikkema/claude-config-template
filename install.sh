#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/albertsikkema/claude-config-template"
TARBALL_URL="${REPO_URL}/archive/refs/heads/main.tar.gz"
TEMP_DIR=""

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print header
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Cleanup function
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        print_message "$BLUE" "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v tar &> /dev/null; then
        missing_deps+=("tar")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_message "$RED" "Error: Missing required dependencies: ${missing_deps[*]}"
        print_message "$YELLOW" "Please install the missing tools and try again."
        exit 1
    fi
}

# Main installation function
main() {
    print_header "Claude Code Configuration Remote Installer"

    # Save original working directory
    ORIGINAL_DIR="$(pwd)"
    print_message "$BLUE" "Target directory: $ORIGINAL_DIR"

    # Check dependencies
    print_message "$BLUE" "Checking dependencies..."
    check_dependencies
    print_message "$GREEN" "  ✓ Dependencies found"

    # Create temporary directory
    print_message "$BLUE" "Creating temporary directory..."
    TEMP_DIR=$(mktemp -d -t claude-config.XXXXXXXXXX)
    print_message "$GREEN" "  ✓ Created: $TEMP_DIR"

    # Download repository
    print_header "Downloading Repository"
    print_message "$BLUE" "Fetching from: $REPO_URL"

    if curl -fsSL "$TARBALL_URL" -o "$TEMP_DIR/repo.tar.gz"; then
        print_message "$GREEN" "  ✓ Download complete"
    else
        print_message "$RED" "Error: Failed to download repository"
        print_message "$YELLOW" "Please check your internet connection and try again."
        exit 1
    fi

    # Extract tarball
    print_message "$BLUE" "Extracting files..."
    if tar -xzf "$TEMP_DIR/repo.tar.gz" -C "$TEMP_DIR"; then
        print_message "$GREEN" "  ✓ Extraction complete"
    else
        print_message "$RED" "Error: Failed to extract repository"
        exit 1
    fi

    # Find the extracted directory (GitHub creates a directory with repo name and branch)
    EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "claude-config-template-*" | head -n 1)

    if [ -z "$EXTRACTED_DIR" ]; then
        print_message "$RED" "Error: Could not find extracted directory"
        exit 1
    fi

    # Run the installer
    print_header "Running Installer"

    # Change to extracted directory and run install-helper.sh with all passed arguments
    cd "$EXTRACTED_DIR"

    if [ ! -f "install-helper.sh" ]; then
        print_message "$RED" "Error: install-helper.sh not found in repository"
        exit 1
    fi

    # Make install-helper.sh executable
    chmod +x install-helper.sh

    # Parse arguments to see if user specified a target directory
    # If not, we'll add the original directory as the target
    local has_target=false
    for arg in "$@"; do
        # Check if argument doesn't start with -- (i.e., it's a positional argument)
        if [[ ! "$arg" =~ ^-- ]] && [[ ! "$arg" =~ ^- ]]; then
            has_target=true
            break
        fi
    done

    # Run installer with all arguments passed to this script
    if [ "$has_target" = true ]; then
        print_message "$BLUE" "Executing install-helper.sh with options: $*"
        echo ""
        ./install-helper.sh "$@"
    else
        print_message "$BLUE" "Executing install-helper.sh with options: $* $ORIGINAL_DIR"
        echo ""
        ./install-helper.sh "$@" "$ORIGINAL_DIR"
    fi

    # Success message
    echo ""
    print_header "Remote Installation Complete!"
    print_message "$GREEN" "✓ Repository downloaded and installed successfully"
}

# Run main function with all arguments
main "$@"
