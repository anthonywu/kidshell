"""
Input handlers for KidShell core.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.handlers.colors import ColorHandler
from kidshell.core.handlers.emoji import EmojiHandler
from kidshell.core.handlers.loops import LoopHandler
from kidshell.core.handlers.math import MathHandler
from kidshell.core.handlers.number_tree import NumberTreeHandler
from kidshell.core.handlers.quiz import QuizHandler
from kidshell.core.handlers.symbols import SymbolHandler

__all__ = [
    "ColorHandler",
    "EmojiHandler",
    "Handler",
    "LoopHandler",
    "MathHandler",
    "NumberTreeHandler",
    "QuizHandler",
    "SymbolHandler",
]
