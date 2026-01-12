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

# Ports (will be set by find_available_ports)
FRONTEND_PORT=""
BACKEND_PORT=""

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if a port is available
is_port_available() {
    local port=$1
    ! lsof -i:"$port" >/dev/null 2>&1
}

# Find available port pair (frontend, backend)
# NOTE: This sequential port searching is largely redundant now.
# Prefer `make desktop` which runs the desktop app with full HMR in a single window.
# This script is kept for cases where you need separate terminal processes.
find_available_ports() {
    local frontend_base=8119
    local backend_base=9118
    local max_attempts=10

    for ((i=0; i<max_attempts; i++)); do
        local frontend_port=$((frontend_base + i))
        local backend_port=$((backend_base + i))

        if is_port_available "$frontend_port" && is_port_available "$backend_port"; then
            FRONTEND_PORT=$frontend_port
            BACKEND_PORT=$backend_port
            return 0
        fi
        print_message "$YELLOW" "  Ports $frontend_port/$backend_port in use, trying next..."
    done

    print_message "$RED" "Error: Could not find available port pair after $max_attempts attempts"
    print_message "$RED" "Tried frontend ports ${frontend_base}-$((frontend_base + max_attempts - 1))"
    print_message "$RED" "Tried backend ports ${backend_base}-$((backend_base + max_attempts - 1))"
    return 1
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
    print_message "$BLUE" "Starting backend on http://localhost:$BACKEND_PORT..."
    cd "$BACKEND_DIR"
    # Use .venv binaries directly instead of uv run to avoid subprocess spawning issues
    ./.venv/bin/python -m uvicorn kanban.main:app --reload --port "$BACKEND_PORT" &
    BACKEND_PID=$!
}

# Start frontend
start_frontend() {
    print_message "$BLUE" "Starting frontend on http://localhost:$FRONTEND_PORT..."
    cd "$FRONTEND_DIR"
    # Export backend URL for Vite environment variables
    export VITE_BACKEND_URL="http://localhost:$BACKEND_PORT"
    export VITE_WS_URL="ws://localhost:$BACKEND_PORT"
    if command -v bun &> /dev/null; then
        bun run dev --port "$FRONTEND_PORT" &
    else
        npm run dev -- --port "$FRONTEND_PORT" &
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

    print_message "$BLUE" "Finding available ports..."
    if ! find_available_ports; then
        exit 1
    fi
    print_message "$GREEN" "  ✓ Using ports: frontend=$FRONTEND_PORT, backend=$BACKEND_PORT"

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
    print_message "$GREEN" "  - Backend:  http://localhost:$BACKEND_PORT"
    print_message "$GREEN" "  - API Docs: http://localhost:$BACKEND_PORT/docs"
    print_message "$GREEN" "  - Frontend: http://localhost:$FRONTEND_PORT"
    print_message "$GREEN" "========================================="
    print_message "$YELLOW" "Press Ctrl+C to stop all services"
    echo ""

    # Wait for processes
    wait
}

main "$@"
