"""
Tests for the safe math evaluator.
"""

import math

import pytest

from kidshell.core.safe_math import SafeMathError, SafeMathEvaluator, safe_eval, safe_math_operation


class TestSafeMathEvaluator:
    """Test the SafeMathEvaluator class."""

    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("2 + 2") == 4
        assert evaluator.evaluate("10 - 3") == 7
        assert evaluator.evaluate("4 * 5") == 20
        assert evaluator.evaluate("15 / 3") == 5
        assert evaluator.evaluate("17 // 5") == 3
        assert evaluator.evaluate("17 % 5") == 2
        assert evaluator.evaluate("2 ** 3") == 8

    def test_comparison_operators(self):
        """Test comparison operations."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("5 > 3") is True
        assert evaluator.evaluate("3 < 5") is True
        assert evaluator.evaluate("5 >= 5") is True
        assert evaluator.evaluate("3 <= 5") is True
        assert evaluator.evaluate("5 == 5") is True
        assert evaluator.evaluate("5 != 3") is True

    def test_math_functions(self):
        """Test math functions."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("abs(-5)") == 5
        assert evaluator.evaluate("round(3.7)") == 4
        assert evaluator.evaluate("min(3, 5, 1)") == 1
        assert evaluator.evaluate("max(3, 5, 1)") == 5
        assert evaluator.evaluate("sum([1, 2, 3])") == 6
        assert evaluator.evaluate("int(3.7)") == 3
        assert evaluator.evaluate("float(3)") == 3.0

    def test_extended_math_and_science_functions(self):
        """Test expanded middle/high-school math and science functions."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("gcd(84, 30)") == 6
        assert evaluator.evaluate("lcm(12, 18)") == 36
        assert evaluator.evaluate("factorial(5)") == 120
        assert evaluator.evaluate("comb(10, 3)") == 120
        assert evaluator.evaluate("perm(5, 2)") == 20
        assert evaluator.evaluate("percent(250, 12)") == 30.0
        assert evaluator.evaluate("log2(8)") == 3
        assert evaluator.evaluate("degrees(pi)") == pytest.approx(180.0)
        assert evaluator.evaluate("radians(180)") == pytest.approx(math.pi)
        assert evaluator.evaluate("mean([2, 4, 6, 8])") == 5.0
        assert evaluator.evaluate("median([1, 9, 3])") == 3.0
        assert evaluator.evaluate("stdev([1, 2, 3, 4])") == pytest.approx(1.2909944487358056)
        assert evaluator.evaluate("hypot(3, 4)") == 5.0

    def test_variables(self):
        """Test evaluation with variables."""
        variables = {"x": 10, "y": 5}
        evaluator = SafeMathEvaluator(variables)

        assert evaluator.evaluate("x + y") == 15
        assert evaluator.evaluate("x * 2") == 20
        assert evaluator.evaluate("x / y") == 2

    def test_math_constants(self):
        """Test math constants."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("pi") == math.pi
        assert evaluator.evaluate("e") == math.e
        assert evaluator.evaluate("tau") == math.tau
        assert evaluator.evaluate("phi") == pytest.approx((1 + math.sqrt(5)) / 2)

        if "c" in evaluator.MATH_CONSTANTS:
            assert evaluator.evaluate("c") > 2.9e8

    def test_dangerous_patterns_blocked(self):
        """Test that dangerous patterns are blocked."""
        evaluator = SafeMathEvaluator()

        # __import__ will match "__" pattern first
        with pytest.raises(SafeMathError, match="Unsafe pattern: __"):
            evaluator.evaluate("__import__('os').system('ls')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: exec"):
            evaluator.evaluate("exec('print(1)')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: eval"):
            evaluator.evaluate("eval('1+1')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: open"):
            evaluator.evaluate("open('/etc/passwd')")

        # Test import without __
        with pytest.raises(SafeMathError, match="Unsafe pattern: import"):
            evaluator.evaluate("import os")

    def test_division_by_zero(self):
        """Test division by zero protection."""
        evaluator = SafeMathEvaluator()

        with pytest.raises(SafeMathError, match="Division by zero"):
            evaluator.evaluate("5 / 0")

        with pytest.raises(SafeMathError, match="Division by zero"):
            evaluator.evaluate("10 // 0")

        with pytest.raises(SafeMathError, match="Division by zero"):
            evaluator.evaluate("10 % 0")

    def test_large_numbers_blocked(self):
        """Test that very large numbers are blocked."""
        evaluator = SafeMathEvaluator()

        with pytest.raises(SafeMathError, match="Number too large"):
            evaluator.evaluate("10 ** 100")

        with pytest.raises(SafeMathError, match="Exponent too large"):
            evaluator.evaluate("2 ** 1000")

    def test_safe_eval_convenience_function(self):
        """Test the safe_eval convenience function."""
        assert safe_eval("2 + 2") == 4
        assert safe_eval("x * 2", {"x": 5}) == 10

    def test_safe_math_operation(self):
        """Test the safe_math_operation function."""
        assert safe_math_operation(10, "+", 5) == 15
        assert safe_math_operation(10, "-", 5) == 5
        assert safe_math_operation(10, "*", 5) == 50
        assert safe_math_operation(10, "/", 5) == 2
        assert safe_math_operation(10, "//", 3) == 3
        assert safe_math_operation(10, "%", 3) == 1
        assert safe_math_operation(2, "**", 3) == 8

        with pytest.raises(SafeMathError, match="Division by zero"):
            safe_math_operation(5, "/", 0)

        with pytest.raises(SafeMathError, match="Unknown operation"):
            safe_math_operation(5, "&", 3)

    def test_complex_expressions(self):
        """Test more complex mathematical expressions."""
        evaluator = SafeMathEvaluator({"x": 10})

        assert evaluator.evaluate("2 * (3 + 4)") == 14
        assert evaluator.evaluate("(10 - 5) * 2") == 10
        assert evaluator.evaluate("2 + 3 * 4") == 14  # Order of operations
        assert evaluator.evaluate("x * 2 + 5") == 25
        assert evaluator.evaluate("sqrt(16)") == 4
        assert evaluator.evaluate("pow(2, 3)") == 8
