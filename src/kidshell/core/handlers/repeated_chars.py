"""
Repeated character input handler.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class RepeatedCharHandler(Handler):
    """Handle keyboard-smash style repeated-letter input."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is made of one repeated letter."""
        return input_text.isalpha() and len(input_text) > 5 and len(set(input_text)) == 1

    def handle(self, input_text: str, session: Session) -> Response:
        """Return count summary for repeated character input."""
        result = f"{len(input_text)} x {input_text[0]}"
        session.add_activity("repeated_chars", input_text, result)
        return Response(
            type=ResponseType.TEXT,
            content=result,
            metadata={"kind": "repeated_chars"},
        )
