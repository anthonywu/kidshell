"""
Secure sandbox implementation for kidshell.
Provides multiple layers of security for executing untrusted Python code.
"""

import ast
import json
import math
import operator
import pathlib
import resource
import sys
from contextlib import contextmanager
from typing import Any


class SecurityError(Exception):
    """Raised when security policy is violated"""


class SafeMathEvaluator(ast.NodeVisitor):
    """
    AST-based safe math evaluator.
    Only allows mathematical operations, no imports or dangerous functions.
    """

    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
    }

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
        # Math functions
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    MAX_NUMBER = 10**15  # Prevent huge numbers
    MAX_ITERATIONS = 10000  # Prevent infinite loops

    def __init__(self, variables: dict[str, Any] | None = None):
        self.variables = variables or {}
        self.iteration_count = 0

    def evaluate(self, expression: str) -> Any:
        """Safely evaluate mathematical expression"""
        # Input validation
        if len(expression) > 1000:
            raise SecurityError("Expression too long")

        # Check for dangerous patterns
        dangerous_patterns = [
            "__",
            "import",
            "exec",
            "eval",
            "compile",
            "open",
            "file",
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
            "classmethod",
            "staticmethod",
            "property",
            "super",
            "type",
            "object",
            "bytes",
            "bytearray",
        ]

        expr_lower = expression.lower()
        for pattern in dangerous_patterns:
            if pattern in expr_lower:
                raise SecurityError(f"Unsafe pattern: {pattern}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = self.visit(tree.body)

            # Validate result
            if isinstance(result, (int, float)):
                if abs(result) > self.MAX_NUMBER:
                    raise SecurityError(f"Number too large: {result}")

            return result

        except (SyntaxError, ValueError) as e:
            raise SecurityError(f"Invalid expression: {e}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.SAFE_OPERATORS.get(type(node.op))

        if not op:
            raise SecurityError(f"Unsafe operator: {type(node.op).__name__}")

        # Prevent division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise SecurityError("Division by zero")

        return op(left, right)

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        op = self.SAFE_OPERATORS.get(type(node.op))

        if not op:
            raise SecurityError(f"Unsafe operator: {type(node.op).__name__}")

        return op(operand)

    def visit_Compare(self, node):
        left = self.visit(node.left)

        for op, comparator in zip(node.ops, node.comparators, strict=False):
            op_func = self.SAFE_OPERATORS.get(type(op))
            if not op_func:
                raise SecurityError(f"Unsafe operator: {type(op).__name__}")

            right = self.visit(comparator)
            if not op_func(left, right):
                return False
            left = right

        return True

    def visit_Constant(self, node):
        # Python 3.8+ uses Constant
        value = node.value

        if isinstance(value, (int, float)):
            if abs(value) > self.MAX_NUMBER:
                raise SecurityError(f"Number too large: {value}")

        return value

    def visit_Num(self, node):
        # Backward compatibility for Python < 3.8
        value = node.n

        if abs(value) > self.MAX_NUMBER:
            raise SecurityError(f"Number too large: {value}")

        return value

    def visit_Name(self, node):
        name = node.id

        # Check variables
        if name in self.variables:
            return self.variables[name]

        # Check safe functions
        if name in self.SAFE_FUNCTIONS:
            return self.SAFE_FUNCTIONS[name]

        # Math constants
        if name in ("pi", "e", "tau"):
            return getattr(math, name)

        raise SecurityError(f"Unknown variable: {name}")

    def visit_Call(self, node):
        func = self.visit(node.func)

        if not callable(func):
            raise SecurityError("Not a function")

        if func not in self.SAFE_FUNCTIONS.values():
            raise SecurityError("Unsafe function call")

        args = [self.visit(arg) for arg in node.args]

        # No keyword arguments allowed for simplicity
        if node.keywords:
            raise SecurityError("Keyword arguments not allowed")

        return func(*args)

    def visit_List(self, node):
        self.iteration_count += len(node.elts)
        if self.iteration_count > self.MAX_ITERATIONS:
            raise SecurityError("Too many iterations")

        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node):
        self.iteration_count += len(node.elts)
        if self.iteration_count > self.MAX_ITERATIONS:
            raise SecurityError("Too many iterations")

        return tuple(self.visit(elt) for elt in node.elts)

    def generic_visit(self, node):
        raise SecurityError(f"Unsafe node type: {type(node).__name__}")


@contextmanager
def resource_limits(cpu_time: int = 1, memory_mb: int = 100):
    """
    Context manager to set resource limits.
    Only works on Unix-like systems.
    """
    if sys.platform == "win32":
        # Windows doesn't support resource module
        yield
        return

    old_limits = {}

    try:
        # Save old limits
        old_limits["cpu"] = resource.getrlimit(resource.RLIMIT_CPU)
        old_limits["memory"] = resource.getrlimit(resource.RLIMIT_AS)

        # Set new limits
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_time, cpu_time))

        # Memory limit in bytes
        memory_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

        yield

    finally:
        # Restore old limits
        for key, limit in old_limits.items():
            if key == "cpu":
                resource.setrlimit(resource.RLIMIT_CPU, limit)
            elif key == "memory":
                resource.setrlimit(resource.RLIMIT_AS, limit)


class SecureExecutor:
    """
    Main executor with multiple security layers.
    """

    def __init__(self, variables: dict[str, Any] | None = None):
        self.evaluator = SafeMathEvaluator(variables)
        self.execution_count = 0
        self.MAX_EXECUTIONS = 1000  # Rate limiting

    def execute(self, code: str, timeout: float = 1.0) -> Any:
        """
        Execute code with multiple security layers.
        """
        # Rate limiting
        self.execution_count += 1
        if self.execution_count > self.MAX_EXECUTIONS:
            raise SecurityError("Execution limit exceeded")

        # Try AST-based evaluation first (safest)
        try:
            return self.evaluator.evaluate(code)
        except SecurityError:
            raise
        except Exception as e:
            # If it's not a simple expression, reject it
            raise SecurityError(f"Complex code not allowed: {e}")

    def reset_limits(self):
        """Reset rate limiting counter"""
        self.execution_count = 0


def validate_data_path(base_dir: str, file_path: str) -> pathlib.Path:
    """
    Validate that a file path stays within the base directory.
    Prevents path traversal attacks.
    """
    base = pathlib.Path(base_dir).resolve()
    target = pathlib.Path(file_path).resolve()

    # Ensure target is within base directory
    try:
        target.relative_to(base)
    except ValueError:
        raise SecurityError(f"Path traversal detected: {file_path}")

    # Additional checks
    if target.is_symlink():
        raise SecurityError("Symbolic links not allowed")

    if not target.suffix == ".data":
        raise SecurityError("Only .data files allowed")

    return target


def safe_json_load(file_path: pathlib.Path, max_size: int = 1024 * 1024) -> dict:
    """
    Safely load JSON with size limits and validation.
    """
    # Check file size
    if file_path.stat().st_size > max_size:
        raise SecurityError(f"File too large: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            # Read with size limit
            content = f.read(max_size)

            # Parse JSON
            data = json.loads(content)

            # Validate structure (basic check)
            if not isinstance(data, dict):
                raise SecurityError("JSON must be an object")

            # Limit nesting depth
            def check_depth(obj, depth=0, max_depth=10):
                if depth > max_depth:
                    raise SecurityError("JSON nesting too deep")

                if isinstance(obj, dict):
                    for value in obj.values():
                        check_depth(value, depth + 1, max_depth)
                elif isinstance(obj, list):
                    for item in obj:
                        check_depth(item, depth + 1, max_depth)

            check_depth(data)

            return data

    except json.JSONDecodeError as e:
        raise SecurityError(f"Invalid JSON: {e}")
    except UnicodeDecodeError as e:
        raise SecurityError(f"Invalid encoding: {e}")


def safe_integer(value: float, max_value: int = 10**15) -> int:
    """
    Safely convert to integer with bounds checking.
    """
    if isinstance(value, float):
        if not value.is_finite():
            raise SecurityError(f"Invalid number: {value}")

        if value != value:  # NaN check
            raise SecurityError("NaN not allowed")

        # Check if it's a whole number
        if value.is_integer() and abs(value) <= max_value:
            return int(value)
        raise SecurityError(f"Number out of range: {value}")

    if isinstance(value, int):
        if abs(value) > max_value:
            raise SecurityError(f"Number too large: {value}")
        return value

    raise SecurityError(f"Not a number: {value}")


# Export main components
__all__ = [
    "SafeMathEvaluator",
    "SecureExecutor",
    "SecurityError",
    "resource_limits",
    "safe_integer",
    "safe_json_load",
    "validate_data_path",
]
