"""
Color handler for showing color names.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType

import rich.color as rich_color
import rich.emoji as rich_emoji


class ColorHandler(Handler):
    """Handle color name lookups."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input might be a color name."""
        # Only handle if it looks like a color name:
        # - Known color words
        # - Not a single letter (leave for symbols)
        # - Not too long
        if len(input_text) < 2 or len(input_text) > 30:
            return False

        # Actually try to parse it as a color to be sure
        match_text = input_text.replace(" ", "_")

        for color_variant in [match_text, f"{match_text}1"]:
            try:
                rich_color.Color.parse(color_variant)
                return True  # It's a valid color
            except rich_color.ColorParseError:
                continue

        return False  # Not a valid color

    def handle(self, input_text: str, session: Session) -> Response:
        """Process color name."""
        try:
            # Try to parse as color
            match_text = input_text.replace(" ", "_")
            color_found = False
            color_value = None

            for color_variant in [match_text, f"{match_text}1"]:
                try:
                    rich_color.Color.parse(color_variant)
                    color_found = True
                    color_value = color_variant
                    break
                except rich_color.ColorParseError:
                    continue

            if color_found:
                # Also check for emoji matches
                emoji_matches = []
                matches = [
                    v for k, v in rich_emoji.EMOJI.items() if input_text in k.split("_") and "skin_tone" not in k
                ]
                emoji_matches = matches[:5]  # Limit to 5
                return Response(
                    type=ResponseType.COLOR,
                    content={
                        "name": input_text,
                        "color": color_value,
                        "emojis": emoji_matches,
                    },
                )

            # Not a color - don't handle it, let other handlers try
            # This is important: return None or raise to indicate we can't handle it
            raise ValueError(f"Not a color: {input_text}")

        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Color lookup error: {e!s}",
                metadata={"color": input_text},
            )
