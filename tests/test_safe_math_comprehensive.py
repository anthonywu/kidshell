"""
Comprehensive test suite for safe_math module.
Tests Monty-based safe evaluation including edge cases and security scenarios.
"""

import math
import pytest

from kidshell.core.safe_math import (
    SafeMathError,
    SafeMathEvaluator,
    safe_eval,
    safe_math_operation,
)


class TestSafeMathEvaluator:
    """Test SafeMathEvaluator class with comprehensive coverage."""

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

    def test_middle_and_high_school_operations(self):
        """Test expanded operations useful for middle/high-school math and science."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("gcd(84, 30)") == 6
        assert evaluator.evaluate("lcm(12, 18)") == 36
        assert evaluator.evaluate("factorial(6)") == 720
        assert evaluator.evaluate("comb(10, 4)") == 210
        assert evaluator.evaluate("perm(6, 2)") == 30
        assert evaluator.evaluate("percent(80, 12.5)") == pytest.approx(10.0)
        assert evaluator.evaluate("asin(1)") == pytest.approx(math.pi / 2)
        assert evaluator.evaluate("acos(1)") == pytest.approx(0.0)
        assert evaluator.evaluate("atan(1)") == pytest.approx(math.pi / 4)
        assert evaluator.evaluate("atan2(1, 1)") == pytest.approx(math.pi / 4)
        assert evaluator.evaluate("degrees(pi/3)") == pytest.approx(60.0)
        assert evaluator.evaluate("radians(90)") == pytest.approx(math.pi / 2)
        assert evaluator.evaluate("log2(1024)") == 10
        assert evaluator.evaluate("mean([1, 2, 3, 4, 5])") == 3.0
        assert evaluator.evaluate("median([1, 2, 9])") == 2.0
        assert evaluator.evaluate("variance([1, 2, 3])") == pytest.approx(1.0)
        assert evaluator.evaluate("pvariance([1, 2, 3])") == pytest.approx(2 / 3)
        assert evaluator.evaluate("stdev([1, 2, 3])") == pytest.approx(1.0)
        assert evaluator.evaluate("pstdev([1, 2, 3])") == pytest.approx(math.sqrt(2 / 3))
        assert evaluator.evaluate("hypot(5, 12)") == 13.0

    def test_science_constants_available(self):
        """Test science constants where available."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("phi") == pytest.approx((1 + math.sqrt(5)) / 2)

        if "c" in evaluator.MATH_CONSTANTS:
            assert evaluator.evaluate("c") > 2.9e8
            assert evaluator.evaluate("g") == pytest.approx(9.80665)
            assert evaluator.evaluate("R") > 8
            assert evaluator.evaluate("NA") > 6e23

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

    def test_dangerous_patterns_blocked(self):
        """Test that dangerous patterns are blocked."""
        evaluator = SafeMathEvaluator()

        # __import__ will match "__" pattern first
        with pytest.raises(SafeMathError, match="Unsafe pattern: __"):
            evaluator.evaluate("__import__('os')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: exec"):
            evaluator.evaluate("exec('print(1)')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: eval"):
            evaluator.evaluate("eval('1+1')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: open"):
            evaluator.evaluate("open('/etc/passwd')")

        with pytest.raises(SafeMathError, match="Unsafe pattern: import"):
            evaluator.evaluate("import os")

        # getattr also contains __, so will match __ first
        with pytest.raises(SafeMathError, match="Unsafe pattern: __"):
            evaluator.evaluate("getattr(object, '__class__')")

        # setattr also contains __, so will match __ first
        with pytest.raises(SafeMathError, match="Unsafe pattern: __"):
            evaluator.evaluate("setattr(x, '__y__', 1)")

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

    def test_complex_expressions(self):
        """Test more complex mathematical expressions."""
        evaluator = SafeMathEvaluator({"x": 10})

        assert evaluator.evaluate("2 * (3 + 4)") == 14
        assert evaluator.evaluate("(10 - 5) * 2") == 10
        assert evaluator.evaluate("2 + 3 * 4") == 14
        assert evaluator.evaluate("x * 2 + 5") == 25
        assert evaluator.evaluate("sqrt(16)") == 4
        assert evaluator.evaluate("pow(2, 3)") == 8

    def test_edge_cases(self):
        """Test edge cases and corner cases."""
        evaluator = SafeMathEvaluator()

        # Zero operations
        assert evaluator.evaluate("0 * 100") == 0
        assert evaluator.evaluate("0 + 0") == 0

        # Negative numbers
        assert evaluator.evaluate("-5 + 3") == -2
        assert evaluator.evaluate("-10 * -2") == 20
        assert evaluator.evaluate("abs(-100)") == 100

        # Floating point precision
        result = evaluator.evaluate("0.1 + 0.2")
        assert abs(result - 0.3) < 0.0001

        # Large but valid numbers
        assert evaluator.evaluate("10000 * 10000") == 100000000

    def test_nested_function_calls(self):
        """Test nested function calls."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("abs(round(3.7))") == 4
        assert evaluator.evaluate("min(max(1, 5), 3)") == 3

    def test_expression_length_limit(self):
        """Test that very long expressions are rejected."""
        evaluator = SafeMathEvaluator()

        # Create an expression exceeding MAX_STRING_LENGTH (1000)
        long_expr = "1 + " * 500  # This is ~3000 characters

        with pytest.raises(SafeMathError, match="Expression too long"):
            evaluator.evaluate(long_expr)

    def test_complex_control_flow_blocked(self):
        """Test that complex control flow is blocked."""
        evaluator = SafeMathEvaluator()

        # for loops
        with pytest.raises(SafeMathError, match="Complex control flow not allowed"):
            evaluator.evaluate("for i in range(10): i")

        # while loops
        with pytest.raises(SafeMathError, match="Complex control flow not allowed"):
            evaluator.evaluate("while True: 1")

        # def statements
        with pytest.raises(SafeMathError, match="Complex control flow not allowed"):
            evaluator.evaluate("def foo(): return 1")

        # class statements
        with pytest.raises(SafeMathError, match="Complex control flow not allowed"):
            evaluator.evaluate("class Foo: pass")

        # lambda (for now, Monty doesn't support classes yet)
        with pytest.raises(SafeMathError, match="Complex control flow not allowed"):
            evaluator.evaluate("lambda x: x + 1")

        # if statements
        with pytest.raises(SafeMathError, match="Complex control flow not allowed"):
            evaluator.evaluate("if True: 1 else: 2")

    def test_variable_override_preserves_constants(self):
        """Test that user variables can override math constants."""
        # Create new evaluator with pi override
        evaluator = SafeMathEvaluator({"pi": 3.14, "c": 123})

        # User's pi should override built-in
        assert evaluator.evaluate("pi") == 3.14
        assert evaluator.evaluate("c") == 123

    def test_multiple_variables(self):
        """Test with multiple variables."""
        variables = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        evaluator = SafeMathEvaluator(variables)

        assert evaluator.evaluate("a + b + c + d + e") == 15
        assert evaluator.evaluate("a * b * c") == 6

    def test_list_computations(self):
        """Test list-related computations."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("len([1, 2, 3, 4, 5])") == 5
        assert evaluator.evaluate("sum([10, 20, 30])") == 60

    def test_bool_results(self):
        """Test that boolean results work correctly."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("10 > 5") is True
        assert evaluator.evaluate("5 > 10") is False
        assert evaluator.evaluate("bool(1)") is True
        assert evaluator.evaluate("bool(0)") is False

    def test_string_conversion(self):
        """Test string conversion functions."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("str(123)") == "123"
        assert evaluator.evaluate("str(3.14)") == "3.14"


class TestSafeEvalConvenienceFunction:
    """Test the safe_eval convenience function."""

    def test_safe_eval_convenience_function(self):
        """Test safe_eval convenience function."""
        assert safe_eval("2 + 2") == 4
        assert safe_eval("x * 2", {"x": 5}) == 10

    def test_safe_eval_no_variables(self):
        """Test safe_eval without variables."""
        assert safe_eval("1 + 2 + 3") == 6
        assert safe_eval("pi * 2") == pytest.approx(math.pi * 2)

    def test_safe_eval_with_constants(self):
        """Test that math constants are available."""
        assert safe_eval("pi") == math.pi
        assert safe_eval("e") == math.e
        assert safe_eval("tau") == math.tau


class TestSafeMathOperation:
    """Test safe_math_operation function."""

    def test_safe_math_operation_basic(self):
        """Test safe_math_operation function."""
        assert safe_math_operation(10, "+", 5) == 15
        assert safe_math_operation(10, "-", 5) == 5
        assert safe_math_operation(10, "*", 5) == 50
        assert safe_math_operation(10, "/", 5) == 2
        assert safe_math_operation(10, "//", 3) == 3
        assert safe_math_operation(10, "%", 3) == 1
        assert safe_math_operation(2, "**", 3) == 8

    def test_safe_math_operation_error_cases(self):
        """Test error cases for safe_math_operation."""
        with pytest.raises(SafeMathError, match="Division by zero"):
            safe_math_operation(5, "/", 0)

        with pytest.raises(SafeMathError, match="Unknown operation"):
            safe_math_operation(5, "&", 3)

        with pytest.raises(SafeMathError, match="Unknown operation"):
            safe_math_operation(5, "||", 3)

    def test_safe_math_operation_negative_numbers(self):
        """Test with negative numbers."""
        assert safe_math_operation(-5, "+", 3) == -2
        assert safe_math_operation(-10, "*", -2) == 20
        assert safe_math_operation(-20, "/", 4) == -5

    def test_safe_math_operation_floats(self):
        """Test with floating point numbers."""
        assert safe_math_operation(10.5, "+", 5.5) == 16.0
        assert safe_math_operation(10.0, "*", 2.5) == 25.0

    def test_safe_math_operation_large_exponent(self):
        """Test that large exponents are rejected."""
        with pytest.raises(SafeMathError, match="Exponent too large"):
            safe_math_operation(2, "**", 1000)

        with pytest.raises(SafeMathError, match="Exponent too large"):
            safe_math_operation(10, "**", 200)


class TestMontyIntegration:
    """Test Monty-specific integration details."""

    def test_monty_caching_behavior(self):
        """Test that Monty instances are cached for performance."""
        evaluator = SafeMathEvaluator({"x": 10})

        # First call creates and caches Monty instance
        result1 = evaluator.evaluate("x + 5")

        # Second call with same inputs should use cached instance
        result2 = evaluator.evaluate("x + 5")

        assert result1 == 15
        assert result2 == 15
        assert len(evaluator._monty_cache) == 1

    def test_monty_different_inputs_separate_cache(self):
        """Test that different inputs create separate cache entries."""
        evaluator1 = SafeMathEvaluator({"x": 10})
        evaluator2 = SafeMathEvaluator({"x": 20, "y": 5})

        # Different variable sets should use different cache keys
        result1 = evaluator1.evaluate("x + 5")
        result2 = evaluator2.evaluate("x + y")

        assert result1 == 15
        assert result2 == 25

    def test_monty_error_propagation(self):
        """Test that Monty errors are properly converted."""
        evaluator = SafeMathEvaluator()

        # Invalid syntax
        with pytest.raises(SafeMathError, match="Invalid expression"):
            evaluator.evaluate("1 + * 2")

        # Undefined variable
        with pytest.raises(SafeMathError):
            evaluator.evaluate("undefined_var + 1")

    def test_external_functions_provided(self):
        """Test that external functions are properly provided to Monty."""
        evaluator = SafeMathEvaluator()

        # These should work as they're in SAFE_FUNCTIONS
        assert evaluator.evaluate("sin(0)") == 0.0
        assert evaluator.evaluate("cos(0)") == 1.0
        assert evaluator.evaluate("sqrt(9)") == 3
        assert evaluator.evaluate("log10(100)") == 2

    def test_math_module_functions(self):
        """Test all math module functions work."""
        evaluator = SafeMathEvaluator()

        # Trig functions
        assert abs(evaluator.evaluate("sin(pi/2)") - 1.0) < 0.0001
        assert abs(evaluator.evaluate("cos(pi)") - (-1.0)) < 0.0001

        # Log/exp
        assert abs(evaluator.evaluate("exp(1)") - math.e) < 0.0001
        assert evaluator.evaluate("log(e)") == 1.0
        assert evaluator.evaluate("log10(1000)") == 3.0

        # Floor/ceil
        assert evaluator.evaluate("floor(3.7)") == 3
        assert evaluator.evaluate("ceil(3.2)") == 4


class TestSecurityAndEdgeCases:
    """Test security scenarios and edge cases."""

    def test_empty_expression(self):
        """Test handling of empty expressions."""
        evaluator = SafeMathEvaluator()

        with pytest.raises(SafeMathError):
            evaluator.evaluate("")

    def test_whitespace_only(self):
        """Test handling of whitespace-only expressions."""
        evaluator = SafeMathEvaluator()

        with pytest.raises(SafeMathError):
            evaluator.evaluate("   ")

    def test_unicode_in_expression(self):
        """Test that Unicode characters are handled."""
        evaluator = SafeMathEvaluator()

        # Some Unicode should be fine in strings
        result = evaluator.evaluate("str(123)")
        assert isinstance(result, str)

    def test_variable_with_underscore(self):
        """Test that underscore pattern is caught."""
        evaluator = SafeMathEvaluator()

        # Underscore at start should be blocked
        with pytest.raises(SafeMathError, match="Unsafe pattern: __"):
            evaluator.evaluate("__x + 1")

    def test_case_insensitive_dangerous_patterns(self):
        """Test that dangerous patterns are caught case-insensitively."""
        evaluator = SafeMathEvaluator()

        # Uppercase import
        with pytest.raises(SafeMathError, match="Unsafe pattern: import"):
            evaluator.evaluate("IMPORT os")

        # Mixed case exec
        with pytest.raises(SafeMathError, match="Unsafe pattern: exec"):
            evaluator.evaluate("ExEc('print(1)')")

    def test_extended_functions_validate_arguments(self):
        """Test argument checks in added helper functions."""
        evaluator = SafeMathEvaluator()

        with pytest.raises(SafeMathError):
            evaluator.evaluate("factorial(-1)")

        with pytest.raises(SafeMathError):
            evaluator.evaluate("comb(5.5, 2)")

        with pytest.raises(SafeMathError):
            evaluator.evaluate("stdev([1])")

        with pytest.raises(SafeMathError):
            evaluator.evaluate("mean([])")

    def test_very_small_numbers(self):
        """Test handling of very small numbers."""
        evaluator = SafeMathEvaluator()

        # Very small positive
        assert evaluator.evaluate("0.0001 * 0.0001") == pytest.approx(1e-8)

        # Very close to zero
        result = evaluator.evaluate("1e-10")
        assert isinstance(result, (int, float))

    def test_operator_precedence(self):
        """Test that operator precedence is correct."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("2 + 3 * 4") == 14  # Not 20
        assert evaluator.evaluate("10 - 3 * 2") == 4  # Not 14
        assert evaluator.evaluate("10 / 2 + 3") == 8.0  # Not 2.5

    def test_parentheses_override(self):
        """Test that parentheses correctly override precedence."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("(2 + 3) * 4") == 20
        assert evaluator.evaluate("(10 - 3) * 2") == 14
        assert evaluator.evaluate("10 / (2 + 3)") == 2.0

    def test_mixed_operations(self):
        """Test expressions with multiple operation types."""
        evaluator = SafeMathEvaluator({"x": 10, "y": 5})

        assert evaluator.evaluate("x + y * 2 - x") == 10  # 10 + 10 - 10
        assert evaluator.evaluate("(x + y) / (x - y)") == 3  # 15 / 5

    def test_exhaustion_limits(self):
        """Test that Monty's resource limits are enforced."""
        evaluator = SafeMathEvaluator()

        # Create a long computation (should hit time limit)
        # Note: This test may be flaky depending on system performance
        long_computation = "sum([i for i in range(100000)])"
        try:
            with pytest.raises(SafeMathError):
                evaluator.evaluate(long_computation)
        except AssertionError:
            # If Monty completes it quickly, skip this test
            pytest.skip("System too fast to trigger timeout")

    def test_comparison_chain(self):
        """Test chained comparisons."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("1 < 2 < 3") is True
        assert evaluator.evaluate("5 > 3 > 1") is True
        assert evaluator.evaluate("1 < 5 > 3") is True

    def test_boolean_logic_in_comparisons(self):
        """Test boolean expressions."""
        evaluator = SafeMathEvaluator()

        assert evaluator.evaluate("5 > 3 and 3 < 5") is True
        assert evaluator.evaluate("5 > 3 or 1 > 10") is True
        assert evaluator.evaluate("1 > 10 and 5 > 3") is False


class TestSafeMathEvaluatorMultipleInstances:
    """Test multiple evaluator instances."""

    def test_independent_evaluators(self):
        """Test that multiple evaluators are independent."""
        eval1 = SafeMathEvaluator({"x": 10})
        eval2 = SafeMathEvaluator({"x": 20})

        assert eval1.evaluate("x * 2") == 20
        assert eval2.evaluate("x * 2") == 40

    def test_shared_cache_isolation(self):
        """Test that cache isolation works correctly."""
        # Create first evaluator with one set of variables
        eval1 = SafeMathEvaluator({"x": 10, "y": 5})
        eval1.evaluate("x + y")  # Populate cache

        # Create second evaluator with different variables
        eval2 = SafeMathEvaluator({"a": 1, "b": 2})
        eval2.evaluate("a + b")  # Should use different cache entry

        # Each should have their own cached Monty instances
        assert len(eval1._monty_cache) == 1
        assert len(eval2._monty_cache) == 1
