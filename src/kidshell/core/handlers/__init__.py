"""
Input handlers for KidShell core.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.handlers.colors import ColorHandler
from kidshell.core.handlers.custom_data import CustomDataHandler
from kidshell.core.handlers.emoji import EmojiHandler
from kidshell.core.handlers.gibberish import GibberishHandler
from kidshell.core.handlers.loops import LoopHandler
from kidshell.core.handlers.math import MathHandler
from kidshell.core.handlers.math_lookup import MathLookupHandler
from kidshell.core.handlers.number_tree import NumberTreeHandler
from kidshell.core.handlers.quiz import QuizHandler
from kidshell.core.handlers.repeated_chars import RepeatedCharHandler
from kidshell.core.handlers.symbols import SymbolHandler

__all__ = [
    "ColorHandler",
    "CustomDataHandler",
    "EmojiHandler",
    "GibberishHandler",
    "Handler",
    "LoopHandler",
    "MathHandler",
    "MathLookupHandler",
    "NumberTreeHandler",
    "QuizHandler",
    "RepeatedCharHandler",
    "SymbolHandler",
]
