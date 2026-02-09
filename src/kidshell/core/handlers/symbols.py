"""
Symbol and algebraic expression handler.
"""

import re
from typing import Any

from sympy import symbols

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.safe_math import SafeMathError, SafeMathEvaluator
from kidshell.core.types import Response, ResponseType


class SymbolHandler(Handler):
    """Handle symbolic math and algebra."""

    IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
    SYMBOL_ASSIGNMENT_PATTERN = re.compile(r"\s*=\s*")

    @staticmethod
    def _reserved_identifiers() -> set[str]:
        """Names reserved for built-in math functions/constants."""
        return set(SafeMathEvaluator.SAFE_FUNCTIONS) | set(SafeMathEvaluator.MATH_CONSTANTS)

    @classmethod
    def _extract_identifiers(cls, input_text: str) -> list[str]:
        """Extract candidate identifiers from an expression."""
        return cls.IDENTIFIER_PATTERN.findall(input_text)

    @staticmethod
    def _numeric_env(session: Session) -> dict[str, Any]:
        """Build a numeric-only environment for Monty evaluation."""
        numeric: dict[str, Any] = {}
        for source in (session.math_env, session.symbols_env):
            for key, value in source.items():
                if isinstance(value, (int, float, bool)):
                    numeric[key] = value
        return numeric

    @staticmethod
    def _format_symbol_value(value: Any) -> Any:
        """Format symbolic objects for display while preserving numeric values."""
        if isinstance(value, (int, float, bool)):
            return value
        return str(value)

    def _undefined_identifiers(self, expression: str, session: Session) -> list[str]:
        """Return identifiers referenced before a numeric value is assigned."""
        numeric_env = self._numeric_env(session)
        reserved = self._reserved_identifiers()
        undefined: list[str] = []
        for name in self._extract_identifiers(expression):
            if name in reserved or name in numeric_env:
                continue
            if name not in undefined:
                undefined.append(name)
        return undefined

    def _coaching_response(self, name: str, *, expression: str) -> Response:
        """Return a friendly coaching response for undefined symbols."""
        return Response(
            type=ResponseType.TEXT,
            content=(
                f"Let's set a value for {name} first. Try: {name} = 3. "
                f"Then try: {name} + 2."
            ),
            metadata={
                "coaching": True,
                "symbol": name,
                "expression": expression,
            },
        )

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if input is symbolic math."""
        # Keep short alpha words as symbols, except known numeric constants.
        if input_text.isalpha() and len(input_text) < 5:
            return input_text not in session.math_env

        # Symbol assignment (x = 5)
        if "=" in input_text:
            parts = input_text.split("=", 1)
            if len(parts) == 2:
                var_name = parts[0].strip()
                if var_name.isalpha() and len(var_name) <= 10:
                    return True

        # Symbol expressions with at least one non-reserved identifier.
        if not any(op in input_text for op in "+-*/"):
            return False

        identifiers = self._extract_identifiers(input_text)
        if not identifiers:
            return False

        reserved = self._reserved_identifiers()
        non_reserved = [name for name in identifiers if name not in reserved]
        if not non_reserved:
            return False

        if any(name in session.symbols_env for name in non_reserved):
            return True

        return any(name.isalpha() and len(name) <= 10 for name in non_reserved)

    def handle(self, input_text: str, session: Session) -> Response:
        """Process symbolic math."""
        try:
            # Single symbol lookup/creation
            if input_text.isalpha() and len(input_text) < 5:
                if input_text in session.symbols_env:
                    value = self._format_symbol_value(session.symbols_env[input_text])
                    session.add_activity("symbol_lookup", input_text, value)
                    return Response(
                        type=ResponseType.SYMBOL_RESULT,
                        content={
                            "symbol": input_text,
                            "value": value,
                            "action": "found",
                        },
                    )

                sym = symbols(input_text)
                session.symbols_env[input_text] = sym
                session.add_activity("symbol_create", input_text, str(sym))
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
                parts = re.split(self.SYMBOL_ASSIGNMENT_PATTERN, input_text, maxsplit=1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    value_str = parts[1].strip()

                    if var_name.isalpha() and len(var_name) <= 10:
                        undefined = [name for name in self._undefined_identifiers(value_str, session) if name != var_name]
                        if undefined:
                            return self._coaching_response(undefined[0], expression=input_text)

                        evaluator = SafeMathEvaluator(variables=self._numeric_env(session))
                        try:
                            value = evaluator.evaluate(value_str)
                        except SafeMathError as e:
                            return Response(
                                type=ResponseType.ERROR,
                                content=f"Symbol error: {e!s}",
                                metadata={"expression": input_text},
                            )

                        session.symbols_env[var_name] = value
                        session.math_env[var_name] = value
                        session.add_activity("symbol_assign", input_text, f"{var_name}={value}")
                        return Response(
                            type=ResponseType.SYMBOL_RESULT,
                            content={
                                "symbol": var_name,
                                "value": value,
                                "action": "assigned",
                            },
                        )

            # Symbol expression
            undefined = self._undefined_identifiers(input_text, session)
            if undefined:
                return self._coaching_response(undefined[0], expression=input_text)

            evaluator = SafeMathEvaluator(variables=self._numeric_env(session))
            try:
                result = evaluator.evaluate(input_text)
            except SafeMathError as e:
                return Response(
                    type=ResponseType.ERROR,
                    content=f"Symbol error: {e!s}",
                    metadata={
                        "expression": input_text,
                        "symbols": list(session.symbols_env.keys()),
                    },
                )

            if isinstance(result, float) and int(result) == result:
                result = int(result)

            if isinstance(result, (int, float, bool)):
                session.math_env["last_number"] = result

            session.add_activity("symbol_expr", input_text, result)
            content = {
                "expression": input_text,
                "result": self._format_symbol_value(result),
                "symbols": list(session.symbols_env.keys()),
            }
            if isinstance(result, (int, float, bool)):
                content["display"] = f"{input_text} = {result}"

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
