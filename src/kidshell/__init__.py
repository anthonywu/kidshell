"""
Kidshell - A Terminal experience for childish expectations!
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

try:
    __version__ = version("kidshell")
except PackageNotFoundError:
    __version__ = "0+unknown"

__author__ = "Anthony Wu"


def prompt_loop(prompt_text: str = "> ", *args: Any, **kwargs: Any) -> None:
    """Lazy proxy to prompt loop to avoid eager CLI-module import side effects."""
    from kidshell.cli.main import prompt_loop as main_prompt_loop

    main_prompt_loop(prompt_text, *args, **kwargs)


__all__ = ["prompt_loop"]
