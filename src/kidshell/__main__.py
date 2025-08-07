"""
Main entry point for kidshell when run as a module.
Allows execution via: python -m kidshell
"""

import sys

from kidshell.cli.config_command import config_command
from kidshell.cli.main import prompt_loop


def main():
    """Main entry point for the kidshell application."""
    # Check if user wants to manage config
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        config_command(sys.argv[2:])
    else:
        prompt_loop()


if __name__ == "__main__":
    main()
