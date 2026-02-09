"""
Math environment lookup handler.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class MathLookupHandler(Handler):
    """Handle direct lookups from session math environment."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input matches a math environment variable."""
        return input_text in session.math_env

    def handle(self, input_text: str, session: Session) -> Response:
        """Return the matching math variable value."""
        value = session.math_env[input_text]
        session.add_activity("math_lookup", input_text, value)

        if isinstance(value, (int, float, bool)):
            session.math_env["last_number"] = value
            return Response(
                type=ResponseType.MATH_RESULT,
                content={
                    "expression": input_text,
                    "result": value,
                    "display": f"{input_text} = {value}",
                },
                metadata={"source": "math_env", "key": input_text},
            )

        return Response(
            type=ResponseType.TEXT,
            content=str(value),
            metadata={"source": "math_env", "key": input_text},
        )
