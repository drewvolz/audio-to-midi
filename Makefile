# Voice to MIDI - Development Commands

# Check linting
lint:
	uv run ruff check .
	@echo "Ruff check passed ✓"

# Format code
format:
	uv run black .
	uv run ruff check --fix .
	@echo "Code formatted ✓"

# Type checking
typecheck:
	uv run mypy voice_to_midi/ || echo "Type checking needs configuration"

# Run all pre-commit checks
pre-commit: format lint
	@echo "Pre-commit checks passed ✓"

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v --cov=voice_to_midi --cov-report=html

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

# Development setup
setup:
	uv sync --dev
	uv run pre-commit install
	@echo "Development environment setup complete ✓"

.PHONY: lint format typecheck pre-commit test test-cov install-hooks pre-commit-all clean setup
