.PHONY: run dev sync check format clean-all test lint desktop build-frontend build-app clean-build install

# Alias for desktop
run: desktop

# Start backend + frontend in separate terminal processes
dev: sync
	./start-claude-flow.sh

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

# Build frontend for desktop app
build-frontend:
	cd claude-flow-board && npm run build

# Run desktop app with full HMR (backend + frontend hot reload)
desktop: sync
	uv run python desktop_app.py --dev

# Build standalone executable
build-app: build-frontend
	@echo "Installing build dependencies..."
	uv sync --extra build
	@echo "Building executable with PyInstaller..."
	uv run pyinstaller claude-flow.spec --clean --noconfirm
	@echo "Installing Finder environment wrapper for macOS..."
	@if [ -d "dist/Claude Flow.app" ]; then \
		cp finder-env-wrapper.sh "dist/Claude Flow.app/Contents/MacOS/launcher" && \
		chmod +x "dist/Claude Flow.app/Contents/MacOS/launcher" && \
		sed -i '' 's|<string>claude-flow</string>|<string>launcher</string>|' "dist/Claude Flow.app/Contents/Info.plist" && \
		echo "Launcher installed successfully"; \
	fi
	@echo ""
	@echo "Build complete!"
	@echo "  macOS: dist/Claude Flow.app"
	@echo "  Other: dist/claude-flow"
	@echo ""
	@echo "Test the app:"
	@echo "  open 'dist/Claude Flow.app'"

# Build and install to /Applications
install: build-app
	@echo "Installing to /Applications..."
	@rm -rf "/Applications/Claude Flow.app"
	@cp -r "dist/Claude Flow.app" /Applications/
	@echo ""
	@echo "Installed to /Applications/Claude Flow.app"
	@echo "Launch with: open -a 'Claude Flow'"

# Clean build artifacts
clean-build:
	rm -rf build/ dist/ *.spec.bak
	find . -name "*.pyc" -delete
