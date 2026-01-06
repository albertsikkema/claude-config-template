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
BACKEND_DIR="$SCRIPT_DIR"
FRONTEND_DIR="$SCRIPT_DIR/claude-flow-board"

# PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

cleanup() {
    print_message "$BLUE" "\nShutting down..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check dependencies
check_dependencies() {
    local missing=()

    if ! command -v uv &> /dev/null; then
        missing+=("uv (https://docs.astral.sh/uv/)")
    fi

    if ! command -v npm &> /dev/null && ! command -v bun &> /dev/null; then
        missing+=("npm or bun")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        print_message "$RED" "Missing dependencies:"
        for dep in "${missing[@]}"; do
            print_message "$RED" "  - $dep"
        done
        exit 1
    fi
}

# Check if frontend exists
check_frontend() {
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_message "$YELLOW" "Frontend not found at $FRONTEND_DIR"
        print_message "$BLUE" "Clone it with:"
        print_message "$NC" "  git clone https://github.com/albertsikkema/claude-flow-board.git $FRONTEND_DIR"
        return 1
    fi
    return 0
}

# Install backend dependencies
install_backend() {
    print_message "$BLUE" "Installing backend dependencies..."
    cd "$BACKEND_DIR"
    uv sync --quiet
    print_message "$GREEN" "  ✓ Backend dependencies installed"
}

# Install frontend dependencies
install_frontend() {
    print_message "$BLUE" "Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    if command -v bun &> /dev/null; then
        bun install --silent
    else
        npm install --silent
    fi
    print_message "$GREEN" "  ✓ Frontend dependencies installed"
}

# Start backend
start_backend() {
    print_message "$BLUE" "Starting backend on http://localhost:9118..."
    cd "$BACKEND_DIR"
    uv run uvicorn kanban.main:app --reload --port 9118 &
    BACKEND_PID=$!
}

# Start frontend
start_frontend() {
    print_message "$BLUE" "Starting frontend on http://localhost:8119..."
    cd "$FRONTEND_DIR"
    if command -v bun &> /dev/null; then
        bun run dev &
    else
        npm run dev &
    fi
    FRONTEND_PID=$!
}

# Main
main() {
    echo ""
    print_message "$BLUE" "========================================="
    print_message "$BLUE" "  Claude Flow - Kanban Board"
    print_message "$BLUE" "========================================="
    echo ""

    check_dependencies

    if ! check_frontend; then
        exit 1
    fi

    install_backend
    install_frontend

    echo ""
    print_message "$GREEN" "Starting services..."
    echo ""

    start_backend
    sleep 2  # Give backend time to start
    start_frontend

    echo ""
    print_message "$GREEN" "========================================="
    print_message "$GREEN" "  Services running:"
    print_message "$GREEN" "  - Backend:  http://localhost:9118"
    print_message "$GREEN" "  - API Docs: http://localhost:9118/docs"
    print_message "$GREEN" "  - Frontend: http://localhost:8119"
    print_message "$GREEN" "========================================="
    print_message "$YELLOW" "Press Ctrl+C to stop all services"
    echo ""

    # Wait for processes
    wait
}

main "$@"
