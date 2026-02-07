"""
Main entry point for kidshell when run as a module.
Allows execution via: python -m kidshell
"""

from kidshell.cli.main import main as cli_main


def main():
    """Main entry point for the kidshell application."""
    cli_main()


if __name__ == "__main__":
    main()
