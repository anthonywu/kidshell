"""
Emoji handler for showing emojis for words.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class EmojiHandler(Handler):
    """Handle emoji lookups for words."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input might be an emoji word."""
        # Single word that might have an emoji
        return len(input_text) > 2 and len(input_text) < 50 and input_text.isalpha() and " " not in input_text

    def handle(self, input_text: str, session: Session) -> Response:
        """Look up emoji for word."""
        try:
            import rich.emoji as rich_emoji

            # Try exact match
            try:
                emoji = rich_emoji.Emoji(input_text)
                return Response(
                    type=ResponseType.EMOJI,
                    content={
                        "word": input_text,
                        "emoji": str(emoji),
                        "found": True,
                    },
                )
            except rich_emoji.NoEmoji:
                pass

            # Try to find matches
            matches = [
                (k, v) for k, v in rich_emoji.EMOJI.items() if input_text in k.split("_") and "skin_tone" not in k
            ]

            if matches:
                return Response(
                    type=ResponseType.EMOJI,
                    content={
                        "word": input_text,
                        "emojis": [v for k, v in matches],
                        "found": True,
                        "multiple": True,
                    },
                )

            # No emoji found
            return Response(
                type=ResponseType.TEXT,
                content=f"No emoji found for '{input_text}'",
                metadata={"word": input_text},
            )

        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Emoji lookup error: {e!s}",
                metadata={"word": input_text},
            )
