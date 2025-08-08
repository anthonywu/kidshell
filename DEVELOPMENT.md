# Development Guide

Complete guide for developing kidshell with modern Python tooling.

## Prerequisites

- Python 3.9+
- [just](https://github.com/casey/just) - Command runner
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

### Installing Prerequisites

Choose your preferred method to install `just`:
- macOS: `brew install just`
- Cargo: `cargo install just`
- Nix: `nix-env -iA nixpkgs.just`

Install `uv`:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Setup

```bash
# Clone the repository
git clone https://github.com/anthonywu/kidshell.git
cd kidshell

# Setup development environment
just setup                      # Creates venv, installs all deps
source .venv/bin/activate

# Run kidshell
just run                        # Normal mode
just debug                      # Debug mode with verbose output
```

## Essential Commands

### Most Common Tasks

```bash
just            # List all available commands
just run        # Run kidshell
just debug      # Run with debug output
just test       # Run tests
just fix        # Auto-fix formatting and linting
just check      # Run all quality checks
```

### Development Workflow

```bash
# Before committing
just fix        # Format and fix issues
just check      # Verify everything passes

# Testing
just test       # Run tests
just test-cov   # With coverage
just watch      # Auto-test on file changes

# Utilities
just clean      # Remove artifacts
just build      # Build package
just todos      # Show TODO items
```

## Full Command Reference

```bash
just           # List all available commands
just install   # Install project dependencies
just dev       # Install development dependencies
just format    # Format code with ruff
just lint      # Run ruff linter
just lint-fix  # Run linter with auto-fix
just type-check # Run type checking (ty + mypy)
just test      # Run tests with pytest
just test-cov  # Run tests with coverage
just clean     # Clean build artifacts
just build     # Build distribution packages
just run       # Run kidshell
just debug     # Run in debug mode
```

### Quick Development Cycle

```bash
# Format and lint code
just quick

# Run all checks before committing
just check

# Full workflow (format, lint, type-check, test)
just all

# Fix formatting and linting issues
just fix
```

### Advanced Commands

```bash
just test-file tests/test_sandbox.py  # Run specific test file
just test-verbose                      # Run tests with verbose output
just test-unit                         # Run only unit tests
just run-secure                        # Run secure sandbox version
just todos                             # Show TODO items in code
just loc                               # Count lines of code
just deps-tree                         # Show dependency tree
just check-security                    # Check for security issues
just watch                             # Watch for changes and run tests
just repl                              # Interactive Python with kidshell
```

## Code Quality Tools

### Ruff (Linting & Formatting)

Ruff is configured to enforce many quality checks:

```bash
# Check for issues
ruff check src tests

# Auto-fix issues
ruff check --fix src tests

# Format code
ruff format src tests

# Check formatting without changing files
ruff format --check src tests
```

### Type Checking

We use both Ty and MyPy for comprehensive type checking:

```bash
# Run Ty (Astral's type checker)
ty check src

# Run MyPy
mypy src

# Run both
just type-check
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_sandbox.py

# Run with verbose output
pytest -v

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

## Pre-commit Hooks

Set up pre-commit hooks to automatically check code before commits:

```bash
# Install pre-commit
uv pip install pre-commit

# Install the git hook scripts
pre-commit install

# Run against all files (useful for first time)
pre-commit run --all-files
```

## Project Structure

```
kidshell/
├── src/
│   └── kidshell/
│       ├── __init__.py
│       ├── __main__.py          # Module entry point
│       └── cli/
│           ├── __init__.py
│           ├── __main__.py      # CLI module entry point
│           ├── main.py          # Main REPL implementation
│           ├── main_secure.py   # Secure version with sandbox
│           └── sandbox.py       # Security sandbox implementation
├── tests/
│   └── test_sandbox.py          # Security tests
├── data/
│   └── example.json             # Example configuration
├── plan/                        # Documentation and planning
├── pyproject.toml               # Modern Python packaging config
├── Makefile                     # Development commands
├── .gitignore
├── .pre-commit-config.yaml      # Pre-commit hooks configuration
└── README.md

```

## Configuration

All tool configurations are in `pyproject.toml`:

- **[build-system]**: Uses hatchling for modern packaging
- **[project]**: Package metadata and dependencies
- **[dependency-groups]**: Development dependencies (PEP 735)
- **[tool.ruff]**: Linting and formatting rules
- **[tool.ty]**: Type checking configuration (Astral's type checker)
- **[tool.mypy]**: Additional type checking
- **[tool.pytest]**: Test configuration
- **[tool.coverage]**: Code coverage settings
- **[tool.uv]**: UV-specific settings

## Best Practices

1. **Always format before committing**: `make format`
2. **Run checks before pushing**: `make check`
3. **Write tests for new features**: Add to `tests/`
4. **Add type hints**: Especially for public APIs
5. **Keep dependencies minimal**: Evaluate transitive deps
6. **Document complex logic**: Use clear docstrings
7. **Security first**: All user input must be sanitized

## Common Tasks

### Adding a New Dependency

```bash
# Add to main dependencies
uv pip install package-name
# Then add to pyproject.toml dependencies

# Add to dev dependencies
uv pip install --group dev package-name
# Then add to appropriate dependency-group in pyproject.toml
```

### Creating a New Handler

1. Add handler function in `src/kidshell/cli/main.py`
2. Add predicate function
3. Register in `HANDLERS` list
4. Add tests in `tests/test_handlers.py`
5. Run `make all` to verify

### Debugging

```bash
# Run with debug output
DEBUG=1 kidshell

# Or use make
make debug

# Use Python debugger
python -m pdb -m kidshell
```

### Building for Distribution

```bash
# Build wheel and source distribution
make build

# Files will be in dist/
ls dist/
```

### Publishing to PyPI

```bash
# Build the package
make build

# Upload to TestPyPI first
uv publish --test

# Upload to PyPI
uv publish
```

## Continuous Integration

The project is configured to work with GitHub Actions, but can be adapted for other CI systems. Key checks:

1. Formatting: `ruff format --check`
2. Linting: `ruff check`
3. Type checking: `ty check && mypy`
4. Tests: `pytest --cov`
5. Security: Sandbox tests must pass

## Troubleshooting

### Import Errors
- Ensure you're in the virtual environment: `source .venv/bin/activate`
- Reinstall in editable mode: `uv pip install -e .`

### Ruff Conflicts
- Some rules may conflict with the formatter
- Check `pyproject.toml` for ignored rules
- Run `ruff check --fix` for auto-fixes

### Type Checking Issues
- Ty may have different rules than MyPy
- Check `pyproject.toml` for configuration
- Use `# type: ignore` sparingly with explanations

### Test Failures
- Run specific test with `-v` for details
- Check test fixtures and mocks
- Ensure test data files exist

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make all` to ensure quality
5. Commit with clear messages
6. Push and create a pull request

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ty Documentation](https://github.com/astral-sh/ty)
- [Hatchling Documentation](https://hatch.pypa.io/)
- [PEP 735 - Dependency Groups](https://peps.python.org/pep-0735/)
