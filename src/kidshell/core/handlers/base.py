"""
Base handler interface.
"""

from abc import ABC, abstractmethod

from kidshell.core.models import Session
from kidshell.core.types import Response


class Handler(ABC):
    """Base handler interface for processing input."""

    @abstractmethod
    def can_handle(self, input_text: str, session: Session) -> bool:
        """
        Check if this handler can process the input.

        Args:
            input_text: Normalized input text
            session: Current session state

        Returns:
            True if this handler can process the input
        """

    @abstractmethod
    def handle(self, input_text: str, session: Session) -> Response:
        """
        Process input and return response.

        Args:
            input_text: Normalized input text
            session: Current session state

        Returns:
            Response object with result
        """

    def get_priority(self) -> int:
        """
        Get handler priority (lower = higher priority).
        Override in subclasses to change priority.
        """
        return 50
