"""
Custom data lookup handler.
"""

from collections.abc import Mapping
from typing import Any

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class CustomDataHandler(Handler):
    """Handle input mapped in custom data files."""

    def _lookup(self, data: Mapping[str, Any], input_text: str) -> Any:
        if input_text in data:
            return data[input_text]

        lower_input = input_text.lower()
        for key, value in data.items():
            if isinstance(key, str) and key.lower() == lower_input:
                return value

        raise KeyError(input_text)

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input has a custom data mapping."""
        if not session.custom_data:
            return False

        if not isinstance(session.custom_data, Mapping):
            return False

        try:
            self._lookup(session.custom_data, input_text)
            return True
        except KeyError:
            return False

    def handle(self, input_text: str, session: Session) -> Response:
        """Return custom data lookup result."""
        if not isinstance(session.custom_data, Mapping):
            return Response(
                type=ResponseType.ERROR,
                content="Custom data is not loaded correctly.",
            )

        value = self._lookup(session.custom_data, input_text)
        session.add_activity("custom_data", input_text, value)
        return Response(
            type=ResponseType.TEXT,
            content=value,
            metadata={"source": "custom_data"},
        )
