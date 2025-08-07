"""
Safe mathematical expression evaluator using AST.
This module provides secure evaluation of mathematical expressions without using eval().
"""

import ast
import math
import operator
from typing import Any


class SafeMathError(Exception):
    """Raised when a mathematical expression cannot be safely evaluated."""


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
        "pow": pow,
    }

    MAX_NUMBER = 10**15  # Prevent huge numbers
    MAX_STRING_LENGTH = 1000  # Prevent huge strings

    def __init__(self, variables: dict[str, Any] | None = None):
        self.variables = variables or {}

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
        # Input validation
        if len(expression) > self.MAX_STRING_LENGTH:
            raise SafeMathError("Expression too long")

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
        ]

        expr_lower = expression.lower()
        for pattern in dangerous_patterns:
            if pattern in expr_lower:
                raise SafeMathError(f"Unsafe pattern: {pattern}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = self.visit(tree.body)

            # Validate result
            if isinstance(result, (int, float)):
                if abs(result) > self.MAX_NUMBER:
                    raise SafeMathError(f"Number too large: {result}")

            return result

        except (SyntaxError, ValueError) as e:
            raise SafeMathError(f"Invalid expression: {e}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.SAFE_OPERATORS.get(type(node.op))

        if not op:
            raise SafeMathError(f"Unsafe operator: {type(node.op).__name__}")

        # Prevent division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise SafeMathError("Division by zero")

        # Prevent huge exponents
        if isinstance(node.op, ast.Pow):
            if isinstance(right, (int, float)) and abs(right) > 100:
                raise SafeMathError("Exponent too large")

        return op(left, right)

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        op = self.SAFE_OPERATORS.get(type(node.op))

        if not op:
            raise SafeMathError(f"Unsafe operator: {type(node.op).__name__}")

        return op(operand)

    def visit_Compare(self, node):
        left = self.visit(node.left)

        for op, comparator in zip(node.ops, node.comparators, strict=False):
            op_func = self.SAFE_OPERATORS.get(type(op))
            if not op_func:
                raise SafeMathError(f"Unsafe operator: {type(op).__name__}")

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
                raise SafeMathError(f"Number too large: {value}")

        return value

    def visit_Num(self, node):
        # Backward compatibility for Python < 3.8
        value = node.n

        if abs(value) > self.MAX_NUMBER:
            raise SafeMathError(f"Number too large: {value}")

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

        raise SafeMathError(f"Unknown variable: {name}")

    def visit_Call(self, node):
        func = self.visit(node.func)

        if not callable(func):
            raise SafeMathError("Not a function")

        if func not in self.SAFE_FUNCTIONS.values():
            raise SafeMathError("Unsafe function call")

        args = [self.visit(arg) for arg in node.args]

        # No keyword arguments allowed for simplicity
        if node.keywords:
            raise SafeMathError("Keyword arguments not allowed")

        return func(*args)

    def visit_List(self, node):
        if len(node.elts) > 100:
            raise SafeMathError("List too large")
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node):
        if len(node.elts) > 100:
            raise SafeMathError("Tuple too large")
        return tuple(self.visit(elt) for elt in node.elts)

    def generic_visit(self, node):
        raise SafeMathError(f"Unsafe node type: {type(node).__name__}")


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
        raise SafeMathError(f"Unknown operation: {op}")

    # Special checks
    if op in ("/", "//", "%") and y == 0:
        raise SafeMathError("Division by zero")

    if op == "**" and abs(y) > 100:
        raise SafeMathError("Exponent too large")

    result = operations[op](x, y)

    if isinstance(result, (int, float)) and abs(result) > SafeMathEvaluator.MAX_NUMBER:
        raise SafeMathError(f"Result too large: {result}")

    return result
