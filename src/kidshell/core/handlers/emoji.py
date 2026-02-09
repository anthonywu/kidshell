"""
Emoji handler for showing emojis for words.
"""

from kidshell.core.handlers.base import Handler, TryNext
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
                session.add_activity("emoji", input_text, str(emoji))
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
            emoji_map = getattr(rich_emoji, "EMOJI", {})
            matches = [(k, v) for k, v in emoji_map.items() if input_text in k.split("_") and "skin_tone" not in k]

            if matches:
                emojis = [v for k, v in matches]
                session.add_activity("emoji", input_text, emojis)
                return Response(
                    type=ResponseType.EMOJI,
                    content={
                        "word": input_text,
                        "emojis": emojis,
                        "found": True,
                        "multiple": True,
                    },
                )

            # No emoji found; allow fallback handlers.
            raise TryNext(f"{input_text}: not emoji")

        except TryNext:
            raise
        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Emoji lookup error: {e!s}",
                metadata={"word": input_text},
            )
