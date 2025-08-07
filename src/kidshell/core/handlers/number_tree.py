"""
Number properties tree handler.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class NumberTreeHandler(Handler):
    """Handle number property tree display."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is a number for tree display."""
        return input_text.isdigit() and 1 <= int(input_text) <= 10000

    def handle(self, input_text: str, session: Session) -> Response:
        """Generate number properties tree."""
        try:
            number = int(input_text)

            # Find factors
            factors = self._find_factors(number)

            # Determine properties
            properties = []

            # Even/Odd
            if number % 2 == 0:
                properties.append(("Even number", "blue"))
            else:
                properties.append(("Odd number", "orange"))

            # Divisibility
            if number % 3 == 0:
                properties.append(("Divisible by 3", "green"))
            if number % 5 == 0:
                properties.append(("Divisible by 5", "purple"))
            if number % 10 == 0:
                properties.append(("Divisible by 10", "red"))

            # Prime check
            if len(factors) == 1 and factors[0] == (1, number):
                properties.append(("Prime number", "gold"))
            elif len(factors) == 2:
                properties.append(("Semiprime", "silver"))

            # Perfect square
            sqrt = number**0.5
            if sqrt == int(sqrt):
                properties.append((f"Perfect square ({int(sqrt)}²)", "cyan"))

            # Operations
            operations = {
                "Square root": f"{number**0.5:.2f}",
                "Squared": f"{number**2}",
                "Doubled": f"{number * 2}",
                "Halved": f"{number / 2:.1f}",
                "Factorial": self._safe_factorial(number) if number <= 10 else "Too large",
            }

            # Record activity
            session.add_activity("number_tree", input_text, number)

            # Update last_number
            session.math_env["last_number"] = number

            return Response(
                type=ResponseType.TREE_DISPLAY,
                content={
                    "number": number,
                    "factors": factors,
                    "properties": properties,
                    "operations": operations,
                },
                metadata={"is_prime": len(factors) == 1},
            )

        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Number tree error: {e!s}",
                metadata={"number": input_text},
            )

    def _find_factors(self, number: int) -> list[tuple[int, int]]:
        """Find all factor pairs of a number."""
        factors = []
        for i in range(1, int(number**0.5) + 1):
            if number % i == 0:
                factors.append((i, number // i))
        return factors

    def _safe_factorial(self, n: int) -> str:
        """Calculate factorial safely."""
        if n > 10:
            return "Too large"
        result = 1
        for i in range(1, n + 1):
            result *= i
        return str(result)
