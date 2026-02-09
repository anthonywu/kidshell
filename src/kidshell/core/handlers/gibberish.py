"""
Gibberish summarizer handler.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class GibberishHandler(Handler):
    """Summarize long gibberish input by character frequencies."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input looks like long gibberish text."""
        return len(input_text) > 10 and any(ch.isalpha() for ch in input_text)

    def handle(self, input_text: str, session: Session) -> Response:
        """Return frequency summary for alphabetic characters."""
        counts = [f"{char}: {input_text.count(char)}" for char in sorted(set(input_text)) if char.isalpha()]
        summary = ", ".join(counts) if counts else input_text
        session.add_activity("gibberish", input_text, summary)
        return Response(
            type=ResponseType.TEXT,
            content=summary,
            metadata={"kind": "gibberish"},
        )
