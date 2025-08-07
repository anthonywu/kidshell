"""
Kidshell - A REPL shell that is resilient in the face of childish expectations.
"""

__version__ = "1.0.0"
__author__ = "Anthony Wu"

# Make the main entry point easily accessible
from kidshell.cli.main import prompt_loop

__all__ = ["prompt_loop"]
