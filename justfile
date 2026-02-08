# List available commands
default:
    @just --list

# Development environment setup
setup:
    uv sync --all-extras
    @echo "✅ Development environment ready!"

# Install project dependencies
install:
    uv tool install -e .
    @echo "✅ Installed as system wide tool."

# Run ruff linter
lint:
    uv run ruff check src tests

# Run ruff linter with auto-fix
lint-fix:
    uv run ruff check --fix src tests

# Format code with ruff
format:
    uv run ruff format src tests

# Check formatting without changing files
format-check:
    uv run ruff format --check src tests

# Run type checking with ty
type-ty:
    uv run ty check src

# Run type checking
type-check: type-ty

# Run all checks (lint, format check, type check)
check: lint format-check type-check

# Run tests with pytest
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov

# Run specific test file
test-file file:
    uv run pytest {{file}}

# Run tests with verbose output
test-verbose:
    uv run pytest -v

# Run only unit tests
test-unit:
    uv run pytest -m unit

# Run only integration tests
test-integration:
    uv run pytest -m integration

# Clean build artifacts
clean:
    rm -rf build dist *.egg-info
    rm -rf .pytest_cache .ruff_cache
    rm -rf htmlcov .coverage coverage.xml
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*~" -delete

# Build distribution packages
build: fix clean
    uv build

# Run the application
run:
    #!/usr/bin/env bash
    set -euo pipefail
    # Wrap in `script` when available so Ctrl-C only shows KidShell's friendly goodbye.
    if script -q /dev/null true >/dev/null 2>&1; then
        script -q /dev/null uv run -q python -m kidshell
    elif script -q -c "true" /dev/null >/dev/null 2>&1; then
        script -q -c "uv run -q python -m kidshell" /dev/null
    else
        uv run -q python -m kidshell
    fi

# Run in debug mode
debug:
    DEBUG=1 uv run kidshell

# Run with custom prompt
run-with-prompt prompt="> ":
    #!/usr/bin/env bash
    set -euo pipefail
    cmd="uv run -q python -c \"from kidshell.cli.main import prompt_loop; prompt_loop('{{prompt}}')\""
    # Keep wrapper behavior consistent so Ctrl-C exits quietly in prompt testing mode too.
    if script -q /dev/null true >/dev/null 2>&1; then
        script -q /dev/null uv run -q python -c "from kidshell.cli.main import prompt_loop; prompt_loop('{{prompt}}')"
    elif script -q -c "true" /dev/null >/dev/null 2>&1; then
        script -q -c "$cmd" /dev/null
    else
        uv run -q python -c "from kidshell.cli.main import prompt_loop; prompt_loop('{{prompt}}')"
    fi

# Development workflow: format, lint, type-check, test
all: format lint type-check test
    @echo "✅ All checks passed!"

# Quick development check (faster, no type checking)
quick: format lint
    @echo "✅ Quick checks passed!"

# Install pre-commit hooks
pre-commit-install:
    uv run pre-commit install

# Run pre-commit on all files
pre-commit-all:
    uv run pre-commit run --all-files

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

# Run security checks with bandit (if installed)
security:
    uv run ruff check --select S src tests

# Run complexity analysis
complexity:
    uv run ruff check --select C90 src

# Generate documentation (placeholder)
docs:
    @echo "Documentation generation not yet configured"

# Watch for changes and run tests (requires watchexec)
watch:
    watchexec -e py -- just test

# Watch for changes and run quick checks
watch-quick:
    watchexec -e py -- just quick

# Run ruff with statistics
lint-stats:
    uv run ruff check --statistics src tests

# Show outdated packages
deps-outdated:
    uv pip list --outdated

# Format and lint in one command
fix: format lint-fix
    @echo "✅ Code formatted and fixed!"

# Run all tests with different Python versions (if installed)
test-all-pythons:
    #!/usr/bin/env bash
    set -euo pipefail
    py_versions=(3.10 3.11 3.12 3.13 3.14)
    for py in "${py_versions[@]}"; do
        venv_dir="/tmp/venv-kidshell-py${py/./}"
        echo "Testing with Python $py using $venv_dir"
        uv venv --python "$py" "$venv_dir"
        uv pip install --python "$venv_dir/bin/python" --group dev --editable .
        uv run --no-project --python "$venv_dir/bin/python" pytest
    done

# Check for common security issues
check-security:
    # Check for hardcoded passwords
    @rg -i "password\s*=\s*[\"']" src || true
    # Check for eval/exec usage
    @rg "eval\(|exec\(" src || true
    # Run bandit checks via ruff
    uv run ruff check --select S src tests

# Create a release (placeholder)
release version:
    @echo "Would release version {{version}}"
    @echo "1. Update version in pyproject.toml"
    @echo "2. Update CHANGELOG.md"
    @echo "3. Create git tag"
    @echo "4. Build and publish to PyPI"

# Run kidshell with profiling
profile:
    uv run python -m cProfile -s cumulative -m kidshell

# Run memory profiling (requires memory_profiler)
profile-memory:
    uv run python -m memory_profiler src/kidshell/cli/main.py

# Show TODO items in code
todos:
    @rg "TODO|FIXME|HACK|XXX" src tests || echo "No TODOs found!"

# Count lines of code
loc:
    @echo "Lines of code in src/:"
    @find src -name "*.py" -exec wc -l {} + | tail -1

# Run mutmut for mutation testing (if installed)
mutation-test:
    uv run mutmut run --paths-to-mutate src/

# Check Python version
check-python:
    @uv run python --version
    @uv run python -c "import sys; print(f'Python executable: {sys.executable}')"

# Install and run with uvx (for testing distribution)
test-uvx:
    uvx --from . kidshell

# Run interactive Python with kidshell imported
repl:
    uv run python -c "from kidshell.cli.main import *; import code; code.interact(local=locals())"

# Check for unused imports
check-unused:
    uv run ruff check --select F401 src tests

# Generate requirements.txt from pyproject.toml
requirements:
    uv pip compile pyproject.toml -o requirements.txt
    @echo "Generated requirements.txt"

# Run a specific handler test
test-handler handler:
    uv run pytest -k "test_{{handler}}" -v

# Verify package can be built and installed
verify-package: build
    #!/usr/bin/env bash
    set -euo pipefail
    temp_dir=$(mktemp -d)
    trap 'rm -rf "$temp_dir"' EXIT
    uv venv $temp_dir/venv
    uv pip install --python $temp_dir/venv/bin/python dist/*.whl
    uv run --no-project --python $temp_dir/venv/bin/python kidshell --help
    echo "✅ Package verification successful!"

# Verify wheel installs across all supported Python versions
verify-package-all-pythons: build
    #!/usr/bin/env bash
    set -euo pipefail
    wheel=$(ls -1 dist/*.whl | head -n 1)
    py_versions=(3.10 3.11 3.12 3.13 3.14)
    temp_dirs=()

    cleanup() {
        for dir in "${temp_dirs[@]:-}"; do
            rm -rf "$dir"
        done
    }
    trap cleanup EXIT

    for py in "${py_versions[@]}"; do
        echo "==> Verifying install on Python $py"
        temp_dir=$(mktemp -d)
        temp_dirs+=("$temp_dir")
        uv venv --python "$py" "$temp_dir/venv"
        uv pip install --python "$temp_dir/venv/bin/python" "$wheel"
        uv run --no-project --python "$temp_dir/venv/bin/python" python -c "import kidshell"
        uv run --no-project --python "$temp_dir/venv/bin/python" kidshell --help >/dev/null
    done

    echo "✅ Package install verified on Python ${py_versions[*]}"
