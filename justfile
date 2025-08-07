# List available commands
default:
    @just --list

# Install project dependencies
install:
    uv pip install -e .

# Install all development dependencies
dev:
    uv pip install -e ".[dev,lint,type]"

# Run ruff linter
lint:
    ruff check src tests

# Run ruff linter with auto-fix
lint-fix:
    ruff check --fix src tests

# Format code with ruff
format:
    ruff format src tests

# Check formatting without changing files
format-check:
    ruff format --check src tests

# Run type checking with ty
type-ty:
    ty check src

# Run type checking with mypy
type-mypy:
    mypy src

# Run both type checkers
type-check: type-ty type-mypy

# Run all checks (lint, format check, type check)
check: lint format-check type-check

# Run tests with pytest
test:
    pytest

# Run tests with coverage
test-cov:
    pytest --cov

# Run specific test file
test-file file:
    pytest {{file}}

# Run tests with verbose output
test-verbose:
    pytest -v

# Run only unit tests
test-unit:
    pytest -m unit

# Run only integration tests
test-integration:
    pytest -m integration

# Clean build artifacts
clean:
    rm -rf build dist *.egg-info
    rm -rf .pytest_cache .ruff_cache .mypy_cache
    rm -rf htmlcov .coverage coverage.xml
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*~" -delete

# Build distribution packages
build: clean
    uv build

# Run the application
run:
    python -m kidshell

# Run in debug mode
debug:
    DEBUG=1 python -m kidshell

# Run with custom prompt
run-with-prompt prompt="> ":
    python -c "from kidshell.cli.main import prompt_loop; prompt_loop('{{prompt}}')"

# Development workflow: format, lint, type-check, test
all: format lint type-check test
    @echo "✅ All checks passed!"

# Quick development check (faster, no type checking)
quick: format lint
    @echo "✅ Quick checks passed!"

# Install pre-commit hooks
pre-commit-install:
    pre-commit install

# Run pre-commit on all files
pre-commit-all:
    pre-commit run --all-files

# Update dependencies
update-deps:
    uv pip compile pyproject.toml -o requirements.txt
    uv pip sync requirements.txt

# Show installed packages
deps-list:
    uv pip list

# Show dependency tree
deps-tree:
    uv pip tree

# Create a new virtual environment
venv:
    uv venv --python 3.10

# Activate virtual environment (informational)
activate:
    @echo "Run: source .venv/bin/activate"

# Run security checks with bandit (if installed)
security:
    ruff check --select S src tests

# Run complexity analysis
complexity:
    ruff check --select C90 --show-source src

# Generate documentation (placeholder)
docs:
    @echo "Documentation generation not yet configured"

# Run the secure version with sandbox
run-secure:
    python -m kidshell.cli.main_secure

# Watch for changes and run tests (requires watchexec)
watch:
    watchexec -e py -- just test

# Watch for changes and run quick checks
watch-quick:
    watchexec -e py -- just quick

# Run ruff with statistics
lint-stats:
    ruff check --statistics src tests

# Show outdated packages
deps-outdated:
    uv pip list --outdated

# Run benchmarks (placeholder)
bench:
    @echo "Benchmarks not yet implemented"

# Format and lint in one command
fix: format lint-fix
    @echo "✅ Code formatted and fixed!"

# Run all tests with different Python versions (if installed)
test-all-pythons:
    #!/usr/bin/env bash
    for py in python3.8 python3.9 python3.10 python3.11 python3.12; do
        if command -v $py &> /dev/null; then
            echo "Testing with $py"
            $py -m pytest
        fi
    done

# Check for common security issues
check-security:
    # Check for hardcoded passwords
    @rg -i "password\s*=\s*[\"']" src || true
    # Check for eval/exec usage
    @rg "eval\(|exec\(" src || true
    # Run bandit checks via ruff
    ruff check --select S src tests

# Create a release (placeholder)
release version:
    @echo "Would release version {{version}}"
    @echo "1. Update version in pyproject.toml"
    @echo "2. Update CHANGELOG.md"
    @echo "3. Create git tag"
    @echo "4. Build and publish to PyPI"

# Run kidshell with profiling
profile:
    python -m cProfile -s cumulative -m kidshell

# Run memory profiling (requires memory_profiler)
profile-memory:
    python -m memory_profiler src/kidshell/cli/main.py

# Show TODO items in code
todos:
    @rg "TODO|FIXME|HACK|XXX" src tests || echo "No TODOs found!"

# Count lines of code
loc:
    @echo "Lines of code in src/:"
    @find src -name "*.py" -exec wc -l {} + | tail -1

# Run mutmut for mutation testing (if installed)
mutation-test:
    mutmut run --paths-to-mutate src/

# Check Python version
check-python:
    @python --version
    @echo "Virtual env: ${VIRTUAL_ENV:-Not activated}"

# Install and run with uvx (for testing distribution)
test-uvx:
    uvx --from . kidshell

# Development environment setup
setup: venv dev pre-commit-install
    @echo "✅ Development environment ready!"
    @echo "Run 'source .venv/bin/activate' to activate"

# Run interactive Python with kidshell imported
repl:
    python -c "from kidshell.cli.main import *; import code; code.interact(local=locals())"

# Check for unused imports
check-unused:
    ruff check --select F401 src tests

# Generate requirements.txt from pyproject.toml
requirements:
    uv pip compile pyproject.toml -o requirements.txt
    @echo "Generated requirements.txt"

# Run a specific handler test
test-handler handler:
    pytest -k "test_{{handler}}" -v

# Verify package can be built and installed
verify-package: build
    #!/usr/bin/env bash
    set -e
    temp_dir=$(mktemp -d)
    python -m venv $temp_dir/venv
    source $temp_dir/venv/bin/activate
    pip install dist/*.whl
    kidshell --help || true
    deactivate
    rm -rf $temp_dir
    @echo "✅ Package verification successful!"