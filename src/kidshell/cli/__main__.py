"""
CLI module entry point.
Allows execution via: python -m kidshell.cli
"""

from kidshell.cli.main import prompt_loop

if __name__ == "__main__":
    prompt_loop()
