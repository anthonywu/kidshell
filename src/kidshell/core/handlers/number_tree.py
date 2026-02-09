"""
Number properties tree handler.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType

MAX_NUMBER_TREE_INPUT = 10000
MAX_FACTORIAL_INPUT = 10


def can_build_number_tree(input_text: str) -> bool:
    """Check if input can be analyzed as number facts."""
    return input_text.isdigit() and 1 <= int(input_text) <= MAX_NUMBER_TREE_INPUT


def find_factor_pairs(number: int) -> list[tuple[int, int]]:
    """Find all factor pairs of a number."""
    factors = []
    for i in range(1, int(number**0.5) + 1):
        if number % i == 0:
            factors.append((i, number // i))
    return factors


def safe_factorial(n: int) -> str:
    """Calculate factorial safely with strict growth cap."""
    if n > MAX_FACTORIAL_INPUT:
        return "Too large"
    result = 1
    for i in range(1, n + 1):
        result *= i
    return str(result)


def build_number_tree_content(number: int) -> dict:
    """Build number facts payload used by both handlers and quiz feedback."""
    factors = find_factor_pairs(number)
    properties = []

    if number % 2 == 0:
        properties.append(("Even number", "blue"))
    else:
        properties.append(("Odd number", "orange"))

    if number % 3 == 0:
        properties.append(("Divisible by 3", "green"))
    if number % 5 == 0:
        properties.append(("Divisible by 5", "purple"))
    if number % 10 == 0:
        properties.append(("Divisible by 10", "red"))

    if len(factors) == 1 and factors[0] == (1, number):
        properties.append(("Prime number", "gold"))
    elif len(factors) == 2:
        properties.append(("Semiprime", "silver"))

    sqrt = number**0.5
    if sqrt == int(sqrt):
        properties.append((f"Perfect square ({int(sqrt)}²)", "cyan"))

    operations = {
        "Square root": f"{number**0.5:.2f}",
        "Squared": f"{number**2}",
        "Doubled": f"{number * 2}",
        "Halved": f"{number / 2:.1f}",
        "Factorial": safe_factorial(number),
    }

    return {
        "number": number,
        "factors": factors,
        "properties": properties,
        "operations": operations,
    }


class NumberTreeHandler(Handler):
    """Handle number property tree display."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is a number for tree display."""
        # Bound accepted input to keep factorization/derived operations lightweight.
        return can_build_number_tree(input_text)

    def handle(self, input_text: str, session: Session) -> Response:
        """Generate number properties tree."""
        try:
            number = int(input_text)
            content = build_number_tree_content(number)

            # Record activity
            session.add_activity("number_tree", input_text, number)

            # Update last_number
            session.math_env["last_number"] = number

            factors = content["factors"]
            return Response(
                type=ResponseType.TREE_DISPLAY,
                content=content,
                metadata={"is_prime": len(factors) == 1},
            )

        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Number tree error: {e!s}",
                metadata={"number": input_text},
            )
