"""
Symbol and algebraic expression handler.
"""

import functools
import re

from sympy import symbols

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.safe_math import SafeMathEvaluator
from kidshell.core.types import Response, ResponseType


class SymbolHandler(Handler):
    """Handle symbolic math and algebra."""

    MATH_OPS_PATTERN = re.compile(r"\s+[+\-*/]\s+")
    SYMBOL_ASSIGNMENT_PATTERN = re.compile(r"\s*=\s*")

    def __init__(self):
        self.parse_symbol_parts = functools.partial(re.split, self.MATH_OPS_PATTERN)

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is symbolic math."""
        # Single letter variables only (not words)
        if len(input_text) == 1 and input_text.isalpha():
            return True

        # Symbol assignment (x = 5)
        if "=" in input_text:
            parts = input_text.split("=")
            if len(parts) == 2:
                var_name = parts[0].strip()
                if var_name.isalpha() and len(var_name) <= 5:
                    return True

        # Symbolic expressions with known symbols
        if session.symbols_env:
            expr_parts = self.parse_symbol_parts(input_text)
            for part in expr_parts:
                if part.strip() in session.symbols_env:
                    return True

        return False

    def handle(self, input_text: str, session: Session) -> Response:
        """Process symbolic math."""
        try:
            # Initialize symbols_env with math_env if empty
            if not session.symbols_env:
                session.symbols_env = session.math_env.copy()

            # Single symbol lookup/creation
            if input_text.isalpha() and len(input_text) < 5:
                if input_text in session.symbols_env:
                    value = session.symbols_env[input_text]
                    return Response(
                        type=ResponseType.SYMBOL_RESULT,
                        content={
                            "symbol": input_text,
                            "value": value,
                            "action": "found",
                        },
                    )
                # Create new symbol
                sym = symbols(input_text)
                session.symbols_env[input_text] = sym
                return Response(
                    type=ResponseType.SYMBOL_RESULT,
                    content={
                        "symbol": input_text,
                        "value": str(sym),
                        "action": "created",
                    },
                )

            # Symbol assignment
            if "=" in input_text:
                parts = re.split(self.SYMBOL_ASSIGNMENT_PATTERN, input_text)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    value_str = parts[1].strip()

                    # Check if var_name is a valid symbol name
                    if var_name.isalpha() and len(var_name) <= 10:
                        # Try to evaluate the right side
                        try:
                            evaluator = SafeMathEvaluator(variables=session.symbols_env)
                            value = evaluator.evaluate(value_str)

                            # Store the value
                            session.symbols_env[var_name] = value
                            session.math_env[var_name] = value

                            return Response(
                                type=ResponseType.SYMBOL_RESULT,
                                content={
                                    "symbol": var_name,
                                    "value": value,
                                    "action": "assigned",
                                },
                            )
                        except Exception:
                            # If evaluation fails, store as symbolic expression
                            pass

            # Symbolic expression
            expr_parts = self.parse_symbol_parts(input_text)
            for part in expr_parts:
                part = part.strip()
                if part and not part.isnumeric() and part not in session.symbols_env:
                    # Create missing symbol
                    sym = symbols(part)
                    session.symbols_env[part] = sym

            # Evaluate expression
            # Use safe evaluator instead of eval
            evaluator = SafeMathEvaluator(variables=session.symbols_env)
            result = evaluator.evaluate(input_text)

            # Check if the result is numeric (not symbolic)
            if isinstance(result, (int, float)):
                # Show both expression and result for clarity
                content = {
                    "expression": input_text,
                    "result": result,
                    "display": f"{input_text} = {result}",
                    "symbols": list(session.symbols_env.keys()),
                }
            else:
                # Symbolic result
                content = {
                    "expression": input_text,
                    "result": str(result),
                    "symbols": list(session.symbols_env.keys()),
                }

            return Response(
                type=ResponseType.SYMBOL_RESULT,
                content=content,
            )

        except Exception as e:
            return Response(
                type=ResponseType.ERROR,
                content=f"Symbol error: {e!s}",
                metadata={"expression": input_text},
            )
