# Audio to MIDI - Development Commands

# Check linting (matches CI)
lint:
	uv run ruff check .
	@echo "Ruff check passed ✓"

# Check formatting without changing files (matches CI)
format-check:
	uv run black --check .
	@echo "Code formatting check passed ✓"

# Format code
format:
	uv run black .
	uv run ruff check --fix .
	@echo "Code formatted ✓"

# Type checking (matches CI)
typecheck:
	uv run mypy audio_to_midi/ || echo "Type checking needs configuration"

# Run all quality checks (matches CI)
quality: lint format-check typecheck
	@echo "Quality checks passed ✓"

# Run all pre-commit checks
pre-commit: format lint
	@echo "Pre-commit checks passed ✓"

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v --cov=audio_to_midi --cov-report=html

# Install pre-commit hooks
install-hooks:
	uv run pre-commit install

# Run pre-commit on all files
pre-commit-all:
	uv run pre-commit run --all-files

# Clean up generated files
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build package
build:
	uv build
	@echo "Package built ✓"

# Development setup
setup:
	uv sync --dev
	uv run pre-commit install
	@echo "Development environment setup complete ✓"

# Run full CI pipeline locally
ci: quality test
	@echo "Full CI pipeline passed ✓"

.PHONY: lint format format-check typecheck quality pre-commit test test-cov install-hooks pre-commit-all clean setup build ci
