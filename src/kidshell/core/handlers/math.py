"""
Math calculation handler.
"""

import re
import sys

from kidshell.core.handlers.base import Handler, TryNext
from kidshell.core.models import Session
from kidshell.core.safe_math import SafeMathError, SafeMathEvaluator
from kidshell.core.types import Response, ResponseType


class MathHandler(Handler):
    """Handle mathematical expressions."""

    MULTIPLY_X_PATTERN = re.compile(r"(?<=[\d\)])\s*[x×]\s*(?=[\d\(])")

    def _normalize_multiplication_aliases(self, expression: str) -> tuple[str, bool]:
        """Interpret x/× between numeric terms as multiplication."""
        if not self.MULTIPLY_X_PATTERN.search(expression):
            return expression, False
        normalized = self.MULTIPLY_X_PATTERN.sub(" * ", expression)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized, True

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is a math expression."""
        # Check for math operators or pure numbers
        if any(op in input_text for op in "+-*/"):
            return True

        # Allow "8 x 6" style multiplication shorthand.
        if self.MULTIPLY_X_PATTERN.search(input_text):
            return True

        # Check for expressions starting with operators (uses last_number)
        if input_text and input_text[0] in "+-*/":
            return True

        # Check for assignment
        if "=" in input_text and not input_text.startswith("="):
            # Could be variable assignment
            parts = input_text.split("=")
            if len(parts) == 2:
                var_name = parts[0].strip()
                # If it's a simple variable name, let symbol handler take it
                if var_name.isalpha() and len(var_name) <= 5:
                    return False
            return True

        return False

    def handle(self, input_text: str, session: Session) -> Response:
        """Process math expression."""
        try:
            # Normalize whitespace
            clean_expr = re.sub(r"\s+", " ", input_text.strip())
            clean_expr, interpreted_multiply_x = self._normalize_multiplication_aliases(clean_expr)

            # Handle expressions starting with operator (use last_number)
            if clean_expr and clean_expr[0] in "+-*/":
                clean_expr = f"{session.math_env.get('last_number', 0)} {clean_expr}"

            # Create safe evaluator with session's math environment
            # User expressions always flow through SafeMathEvaluator (Monty + guards),
            # never Python eval/exec.
            evaluator = SafeMathEvaluator(variables=session.math_env)

            # Evaluate expression safely
            if "=" in clean_expr and not clean_expr.startswith("="):
                # Handle assignment
                parts = clean_expr.split("=", 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    value_expr = parts[1].strip()

                    # Evaluate the right side safely
                    result = evaluator.evaluate(value_expr)

                    # Store in session's math environment
                    session.math_env[var_name] = result
                else:
                    raise SafeMathError("Invalid assignment syntax")
            else:
                # Calculation
                result = evaluator.evaluate(clean_expr)

                # Convert float to int if possible
                if isinstance(result, float) and int(result) == result and result <= sys.maxsize:
                    result = int(result)

                # Update last_number
                if isinstance(result, (int, float)):
                    session.math_env["last_number"] = result

            # Record activity
            session.add_activity("math", input_text, result)

            # Check if this solves a quiz
            if session.current_quiz and str(result) == str(session.current_quiz.get("answer")):
                session.problems_solved += 1
                session.current_streak += 1

            # Include display field if the expression contains variables
            content = {
                "expression": clean_expr,
                "result": result,
            }

            if interpreted_multiply_x:
                content["note"] = (
                    "Interpreted 'x' as multiplication here. "
                    "Tip: x can also be a variable (for example: x = 3)."
                )

            # If expression has variables, show the evaluation
            if any(c.isalpha() for c in clean_expr):
                content["display"] = f"{clean_expr} = {result}"

            return Response(
                type=ResponseType.MATH_RESULT,
                content=content,
                metadata={
                    "complexity": self._calculate_complexity(clean_expr),
                    "has_variables": any(c.isalpha() for c in clean_expr),
                },
            )

        except SafeMathError as e:
            error_text = str(e).lower()
            # Let SymbolHandler try expressions that failed due unknown names.
            if any(ch.isalpha() for ch in input_text) and ("nameerror" in error_text or "not defined" in error_text):
                raise TryNext(str(e))
            return Response(
                type=ResponseType.ERROR,
                content=f"Math error: {e!s}",
                metadata={"expression": input_text},
            )
        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Calculation error: {e!s}",
                metadata={"expression": input_text},
            )

    def _calculate_complexity(self, expr: str) -> int:
        """Calculate expression complexity for achievements."""
        operators = sum(1 for c in expr if c in "+-*/")
        numbers = len(re.findall(r"\d+", expr))
        return operators + (numbers - 1)
