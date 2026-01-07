.PHONY: run dev sync check format clean-all test lint

# Start the backend server in development mode
run: sync
	uv run uvicorn kanban.main:app --reload --port 9118

# Alias for run
dev: run

# Install dependencies (including dev extras)
sync:
	uv sync --extra dev

# Run linting checks
check:
	uv run ruff check src/

# Format code
format:
	uv run ruff format src/

# Format and lint (clean up code style)
lint: format
	uv run ruff check src/ --fix

# Run tests
test: sync
	uv run pytest tests/ -v

# Remove database and cache files
clean-all:
	rm -f data/kanban.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
