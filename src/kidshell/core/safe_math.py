"""
Safe mathematical expression evaluator using Monty sandbox.
This module provides secure evaluation of mathematical expressions using pydantic-monty.
"""

import math
import operator
import re
import statistics
from typing import Any

import pydantic_monty

# Keep values finite and bounded, but allow common scientific constants/outputs.
# This ceiling limits abuse via gigantic intermediate values while still supporting
# classroom-scale science calculations (e.g., Avogadro's number).
MAX_SAFE_NUMBER = 10**30
MAX_SEQUENCE_LENGTH = 1000
MAX_FACTORIAL_N = 170
MAX_COMBINATORICS_N = 1000

SCIENCE_CONSTANTS: dict[str, float] = {}
try:
    import scipy.constants as scipy_constants

    SCIENCE_CONSTANTS = {
        "c": scipy_constants.c,  # speed of light (m/s)
        "g": scipy_constants.g,  # standard gravity (m/s^2)
        "G": scipy_constants.G,  # gravitational constant (N m^2 / kg^2)
        "h": scipy_constants.h,  # Planck constant (J s)
        "k": scipy_constants.k,  # Boltzmann constant (J/K)
        "R": scipy_constants.R,  # ideal gas constant (J/(mol K))
        "NA": scipy_constants.N_A,  # Avogadro constant (1/mol)
        "sigma": scipy_constants.sigma,  # Stefan-Boltzmann constant
    }
except Exception:
    SCIENCE_CONSTANTS = {}


def _coerce_int(value: Any, name: str, max_abs: int) -> int:
    # Normalize numeric-like inputs to an integer and enforce an absolute bound to
    # prevent resource abuse (e.g., enormous factorial/combinatorics requests).
    if isinstance(value, bool):
        int_value = int(value)
    elif isinstance(value, int):
        int_value = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{name} must be an integer")
        int_value = int(value)
    else:
        raise TypeError(f"{name} must be an integer")

    if abs(int_value) > max_abs:
        raise ValueError(f"{name} is too large")
    return int_value


def _coerce_numeric_sequence(values: Any, *, min_length: int = 1) -> list[float]:
    # Constrain sequence shape and element sizes so statistics helpers cannot be used
    # to allocate unbounded memory or trigger huge numeric operations.
    if not isinstance(values, (list, tuple)):
        raise TypeError("Expected a list or tuple")

    if len(values) < min_length:
        raise ValueError("Not enough values")
    if len(values) > MAX_SEQUENCE_LENGTH:
        raise ValueError("Too many values")

    numbers: list[float] = []
    for value in values:
        if not isinstance(value, (int, float)):
            raise TypeError("Sequence values must be numbers")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Sequence contains non-finite values")
        if abs(value) > MAX_SAFE_NUMBER:
            raise ValueError("Sequence value is too large")
        numbers.append(float(value))

    return numbers


def safe_factorial(value: Any) -> int:
    # Factorial grows extremely fast; cap n to avoid runaway compute/size.
    n = _coerce_int(value, "n", max_abs=MAX_FACTORIAL_N)
    if n < 0:
        raise ValueError("factorial() not defined for negative values")
    return math.factorial(n)


def safe_comb(n_value: Any, k_value: Any) -> int:
    # Keep n/k bounded to prevent combinatorics from becoming an accidental DoS.
    n = _coerce_int(n_value, "n", max_abs=MAX_COMBINATORICS_N)
    k = _coerce_int(k_value, "k", max_abs=MAX_COMBINATORICS_N)
    if n < 0 or k < 0:
        raise ValueError("comb() requires non-negative values")
    return math.comb(n, k)


def safe_perm(n_value: Any, k_value: Any | None = None) -> int:
    # Same bounded-input policy as comb() for predictable runtime and memory use.
    n = _coerce_int(n_value, "n", max_abs=MAX_COMBINATORICS_N)
    if n < 0:
        raise ValueError("perm() requires non-negative values")

    if k_value is None:
        return math.perm(n)

    k = _coerce_int(k_value, "k", max_abs=MAX_COMBINATORICS_N)
    if k < 0:
        raise ValueError("perm() requires non-negative values")
    return math.perm(n, k)


def safe_percent(base: float, percent_value: float) -> float:
    # Percent helper intentionally keeps arithmetic simple and transparent for kids.
    return float(base) * float(percent_value) / 100.0


def safe_mean(values: Any) -> float:
    # Sequence validator enforces bounded, numeric inputs first.
    return float(statistics.mean(_coerce_numeric_sequence(values)))


def safe_median(values: Any) -> float:
    # Sequence validator enforces bounded, numeric inputs first.
    return float(statistics.median(_coerce_numeric_sequence(values)))


def safe_mode(values: Any) -> float:
    # Sequence validator enforces bounded, numeric inputs first.
    return float(statistics.mode(_coerce_numeric_sequence(values)))


def safe_stdev(values: Any) -> float:
    # stdev requires at least two values; validator enforces that contract.
    return float(statistics.stdev(_coerce_numeric_sequence(values, min_length=2)))


def safe_pstdev(values: Any) -> float:
    # Sequence validator enforces bounded, numeric inputs first.
    return float(statistics.pstdev(_coerce_numeric_sequence(values)))


def safe_variance(values: Any) -> float:
    # variance requires at least two values; validator enforces that contract.
    return float(statistics.variance(_coerce_numeric_sequence(values, min_length=2)))


def safe_pvariance(values: Any) -> float:
    # Sequence validator enforces bounded, numeric inputs first.
    return float(statistics.pvariance(_coerce_numeric_sequence(values)))


class SafeMathError(Exception):
    """Raised when a mathematical expression cannot be safely evaluated."""


class SafeMathEvaluator:
    """
    Monty-based safe math evaluator.
    Uses pydantic-monty for secure evaluation of mathematical expressions.
    """

    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "pow": pow,
        # Math functions
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        "radians": math.radians,
        "degrees": math.degrees,
        "sqrt": math.sqrt,
        "log": math.log,
        "log2": math.log2,
        "log10": math.log10,
        "exp": math.exp,
        "hypot": math.hypot,
        "gcd": math.gcd,
        "lcm": math.lcm,
        "factorial": safe_factorial,
        "comb": safe_comb,
        "perm": safe_perm,
        "percent": safe_percent,
        "mean": safe_mean,
        "median": safe_median,
        "mode": safe_mode,
        "stdev": safe_stdev,
        "pstdev": safe_pstdev,
        "variance": safe_variance,
        "pvariance": safe_pvariance,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    MAX_NUMBER = MAX_SAFE_NUMBER
    MAX_STRING_LENGTH = 1000
    MAX_ALLOCATIONS = 10000
    MAX_DURATION_SECS = 1.0
    MATH_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "phi": (1 + math.sqrt(5)) / 2,
        **SCIENCE_CONSTANTS,
    }
    BLOCKED_TOKENS = (
        "import",
        "exec",
        "eval",
        "compile",
        "open",
        "input",
        "raw_input",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
    )
    BLOCKED_CONTROL_FLOW_KEYWORDS = (
        "for",
        "while",
        "def",
        "class",
        "lambda",
        "if",
    )

    def __init__(self, variables: dict[str, Any] | None = None):
        self.variables = variables or {}
        self._monty_cache: dict[tuple[str, tuple[tuple[str, Any], ...]], pydantic_monty.Monty] = {}

    @staticmethod
    def _cache_safe_value(value: Any) -> Any:
        try:
            hash(value)
            return value
        except TypeError:
            # Cache keys must be hashable; repr keeps cache stable without executing code.
            return repr(value)

    @classmethod
    def _build_cache_key(cls, expression: str, inputs: dict[str, Any]) -> tuple[str, tuple[tuple[str, Any], ...]]:
        frozen_items = tuple(sorted((key, cls._cache_safe_value(value)) for key, value in inputs.items()))
        return expression, frozen_items

    @classmethod
    def _find_blocked_pattern(cls, expression: str) -> str | None:
        lowered = expression.lower()
        if "__" in lowered:
            # Dunder access is a common introspection/escape vector.
            return "__"

        for token in cls.BLOCKED_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                # Block sensitive builtins/import primitives before evaluation.
                return token
        return None

    @classmethod
    def _contains_blocked_control_flow(cls, expression: str) -> bool:
        # Restrict to expression-style math; statement control-flow can hide complex
        # or long-running behavior that is outside kid-shell scope.
        return any(
            re.search(rf"\b{re.escape(keyword)}\b", expression, flags=re.IGNORECASE)
            for keyword in cls.BLOCKED_CONTROL_FLOW_KEYWORDS
        )

    def evaluate(self, expression: str) -> Any:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: Mathematical expression as string

        Returns:
            Result of the evaluation

        Raises:
            SafeMathError: If expression is unsafe or invalid
        """
        if not expression.strip():
            # Reject blank input early so downstream evaluators don't interpret it.
            raise SafeMathError("Empty expression")

        if len(expression) > self.MAX_STRING_LENGTH:
            # Size guard to avoid pathological input strings.
            raise SafeMathError("Expression too long")

        blocked_pattern = self._find_blocked_pattern(expression)
        if blocked_pattern:
            # Token-level denylist blocks obvious unsafe capabilities.
            raise SafeMathError(f"Unsafe pattern: {blocked_pattern}")

        # Add safe functions as external functions
        external_functions = {name: func for name, func in self.SAFE_FUNCTIONS.items()}

        # Keep expression support intentionally simple for predictable, child-safe behavior.
        if self._contains_blocked_control_flow(expression):
            # Keep the interpreter surface small and predictable.
            raise SafeMathError("Complex control flow not allowed")

        # Pre-check for very large exponents
        exponent_match = re.search(r"\*\*\s*([-+]?\d+)\s*$", expression)
        if exponent_match:
            exponent = int(exponent_match.group(1))
            if abs(exponent) > 100:
                # Prevent huge exponentiation from exploding compute/memory.
                raise SafeMathError("Exponent too large")

        # Prepare inputs with defaults first, then user values override.
        inputs = dict(self.MATH_CONSTANTS)
        inputs.update(self.variables)

        try:
            # Use cached Monty instance for repeated expressions
            cache_key = self._build_cache_key(expression, inputs)
            if cache_key not in self._monty_cache:
                # Pre-register allowed inputs/functions; Monty rejects unknown symbols.
                self._monty_cache[cache_key] = pydantic_monty.Monty(
                    expression,
                    inputs=list(inputs.keys()),
                    external_functions=list(external_functions.keys()),
                    type_check=False,
                )

            m = self._monty_cache[cache_key]

            limits = pydantic_monty.ResourceLimits(
                # Runtime resource caps are the last line of defense inside evaluator.
                max_allocations=self.MAX_ALLOCATIONS,
                max_duration_secs=self.MAX_DURATION_SECS,
            )

            result = m.run(
                inputs=inputs,
                external_functions=external_functions,
                limits=limits,
            )

            # Validate result size
            if isinstance(result, (int, float)):
                if abs(result) > self.MAX_NUMBER:
                    # Post-check prevents returning extreme values even if computed.
                    raise SafeMathError(f"Number too large: {result}")
            elif isinstance(result, str):
                if len(result) > self.MAX_STRING_LENGTH:
                    # Bound string outputs to avoid oversized responses.
                    raise SafeMathError("String too long")

            return result

        except (pydantic_monty.MontySyntaxError, pydantic_monty.MontyRuntimeError) as e:
            error_msg = str(e).lower()
            if "division by zero" in error_msg:
                # Normalize engine-specific errors to stable user-facing messages.
                raise SafeMathError("Division by zero")
            if "time limit exceeded" in error_msg or "timeouterror" in error_msg:
                # Preserve timeout semantics for tests/callers.
                raise SafeMathError("Execution timeout")
            if "memory limit exceeded" in error_msg or "memoryerror" in error_msg:
                # Preserve memory-limit semantics for tests/callers.
                raise SafeMathError("Memory limit exceeded")
            raise SafeMathError(f"Invalid expression: {e}")
        except (ValueError, TypeError, ZeroDivisionError) as e:
            if isinstance(e, ZeroDivisionError):
                raise SafeMathError("Division by zero")
            raise SafeMathError(f"Math error: {e}")


def safe_eval(expression: str, variables: dict[str, Any] | None = None) -> Any:
    """
    Safely evaluate a mathematical expression.

    This is a convenience function that creates an evaluator and evaluates the expression.

    Args:
        expression: Mathematical expression to evaluate
        variables: Optional dictionary of variables to use in evaluation

    Returns:
        Result of the evaluation

    Raises:
        SafeMathError: If the expression is unsafe or invalid
    """
    evaluator = SafeMathEvaluator(variables)
    return evaluator.evaluate(expression)


def safe_math_operation(x: float, op: str, y: float) -> float:
    """
    Safely perform a basic math operation.

    Args:
        x: First operand
        op: Operation (+, -, *, /, //, %, **)
        y: Second operand

    Returns:
        Result of the operation

    Raises:
        SafeMathError: If operation is invalid or unsafe
    """
    operations = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "//": operator.floordiv,
        "%": operator.mod,
        "**": operator.pow,
    }

    if op not in operations:
        # Reject unknown operators instead of falling through to dynamic behavior.
        raise SafeMathError(f"Unknown operation: {op}")

    # Special checks
    if op in ("/", "//", "%") and y == 0:
        # Explicit arithmetic safety check for common undefined operations.
        raise SafeMathError("Division by zero")

    if op == "**" and abs(y) > 100:
        # Bound exponent growth for deterministic performance.
        raise SafeMathError("Exponent too large")

    result = operations[op](x, y)

    if isinstance(result, (int, float)) and abs(result) > SafeMathEvaluator.MAX_NUMBER:
        # Post-check large results in direct-operation path as well.
        raise SafeMathError(f"Result too large: {result}")

    return result
