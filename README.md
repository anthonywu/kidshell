# kidshell

![icon](./docs/icon-128.png)

A [REPL](https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop) shell that is resilient in the face of _childish expectations_.

> 🔒 **Security First**: kidshell implements comprehensive security measures to protect young users.

All standard entrypoints (`kidshell`, `python -m kidshell`, and `just run`) use secure/sandboxed evaluation by default.

See [SECURITY.md](SECURITY.md) for details on our security features and vulnerability reporting.

## Quick Start

```bash
# Run without installation (recommended)
uvx kidshell
```

Once launched, think *"What would a child do?"* and try:

- **Colors**: `blue`, `red`, `green` (or any color name)
- **Emojis**: `bread`, `cat`, `star` (anything with an emoji)
- **Ranges**: `0...100...1` or `0...10000...10...0.01`
- **Math**: `1+1`, `pi`, `c`, `g`, `h`, `tau` (constants and expressions)
- **Symbolic algebra**:
  - `x`, `x + 3`, `x = 2`, then `x + 3` again
  - Define multiple variables: `x + y - z`
- **Just press Enter** - see what happens!
- **Smash the keyboard** - it handles gibberish gracefully

## Installation Options

### For Parents and IT Admin

```bash
# Fastest - no installation needed
uvx kidshell

# Normal users: the terminal app is meant to be installed system-wide
uv tool install kidshell  # global in PATH in your ~/.local/bin/kidshell
pipx install kidshell  # global in PATH

# For this repository workflow, prefer justfile helpers:
just setup   # project .venv + dev dependencies
just install # install kidshell as a uv tool from git cloned src
```

### For Developers

See [DEVELOPMENT.md](DEVELOPMENT.md) for the complete development guide.

**Quick start:**
```bash
git clone https://github.com/anthonywu/kidshell.git
cd kidshell
just setup                      # Uses uv to create .venv and install deps
just run                        # Run kidshell
```

## Custom Data Configuration

kidshell supports custom input→output mappings stored in platform-specific directories:

```bash
# Edit custom data
kidshell config                 # Opens editor with example.json
kidshell config edit mydata.json # Create/edit specific file
kidshell config list            # List all data files
kidshell config info            # Show config locations
```

Data files are JSON with custom mappings:

```json
{
  "hello": "👋",
  "birthday": "2018-01-01"
}
```

## Project Structure

```
kidshell/
├── src/kidshell/       # Source code
│   ├── cli/           # CLI and REPL
│   ├── core/          # Core services
│   └── frontends/     # UI frontends
├── tests/             # Test files
├── justfile          # Development commands
└── pyproject.toml    # Project configuration
```

## Roadmap

1. 👥 Multiple profiles for N users in your family/classroom
1. 🖥 Run in browser or host at a web site
1. 📥 Load user/family configs from public https URLs
1. 📖 Dictionary database/API integration for spelling validation
1. 💬 Translation lookups for multilingual households
1. 🔊 Text-to-speech integration via [localtalk](https://github.com/anthonywu/localtalk)
1. ✨ Local/offline AI magic, if applicable and reasonably to introduce to children.
1. 🏞 Local/offline image generation with content moderation
1. 🧮 Expand usage of math libraries
1. 🌐 More UI languages

## Security

kidshell takes security seriously, especially given our young user base. We implement:

- **Path traversal protection** preventing unauthorized file system access
- **Safe JSON processing** without code execution risks
- **Subprocess security** with command validation and safe defaults
- **Secure file operations** confined to user-specific directories

For detailed security information, vulnerability reporting, and best practices, see [SECURITY.md](SECURITY.md).

## License

MIT

## Contributing

Contributions welcome! Please:
1. Review [SECURITY.md](SECURITY.md) for security guidelines
2. See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and workflow
3. Run `just check` before submitting PRs
4. Follow secure coding practices for any changes
