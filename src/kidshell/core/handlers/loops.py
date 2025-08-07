"""
Loop handler for counting sequences.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class LoopHandler(Handler):
    """Handle counting loops like 0...10...1"""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is a loop pattern."""
        return "..." in input_text

    def handle(self, input_text: str, session: Session) -> Response:
        """Process loop pattern."""
        try:
            parts = [num.strip() for num in input_text.split("...")]

            if len(parts) < 2:
                return Response(
                    type=ResponseType.ERROR,
                    content="Loop needs at least start and end: start...end",
                    metadata={"input": input_text},
                )

            start = int(parts[0])
            end = int(parts[1])
            step = int(parts[2]) if len(parts) > 2 else 1

            # Safety limits
            if abs(end - start) / abs(step) > 1000:
                return Response(
                    type=ResponseType.ERROR,
                    content="Loop too long (max 1000 iterations)",
                    metadata={"start": start, "end": end, "step": step},
                )

            # Generate sequence
            numbers = []
            current = start
            if step > 0:
                while current <= end:
                    numbers.append(current)
                    current += step
            else:
                while current >= end:
                    numbers.append(current)
                    current += step

            # Record activity
            session.add_activity("loop", input_text, len(numbers))

            return Response(
                type=ResponseType.LOOP_RESULT,
                content={
                    "start": start,
                    "end": end,
                    "step": step,
                    "numbers": numbers,
                    "count": len(numbers),
                },
                metadata={"pattern": input_text},
            )

        except ValueError as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Invalid loop format: {e!s}",
                metadata={"input": input_text},
            )
        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Loop error: {e!s}",
                metadata={"input": input_text},
            )
