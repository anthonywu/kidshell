"""
Core types and data structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseType(Enum):
    """Types of responses the engine can return."""

    TEXT = "text"
    MATH_RESULT = "math_result"
    TREE_DISPLAY = "tree_display"
    PROGRESS_TABLE = "progress_table"
    ACHIEVEMENT = "achievement"
    ERROR = "error"
    QUIZ = "quiz"
    EMOJI = "emoji"
    COLOR = "color"
    LOOP_RESULT = "loop_result"
    SYMBOL_RESULT = "symbol_result"
    PANEL = "panel"
    STATUS = "status"


@dataclass
class Response:
    """Platform-agnostic response object."""

    type: ResponseType
    content: Any
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert response to dictionary for serialization."""
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Response":
        """Create response from dictionary."""
        return cls(
            type=ResponseType(data["type"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
        )
