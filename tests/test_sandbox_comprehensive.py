"""
Comprehensive test suite for sandbox module.
Tests security guards, file validation, and JSON loading.
"""

import json
import math

import pytest

from kidshell.cli.sandbox import (
    SecurityError,
    SecureExecutor,
    resource_limits,
    safe_integer,
    safe_json_load,
    validate_data_path,
)


class TestSecureExecutor:
    """Test SecureExecutor class."""

    def test_basic_execution(self):
        """Test basic code execution."""
        executor = SecureExecutor()

        result = executor.execute("1 + 1")
        assert result == 2

    def test_execution_with_variables(self):
        """Test execution with variables."""
        executor = SecureExecutor({"x": 10, "y": 5})

        result = executor.execute("x + y")
        assert result == 15

    def test_execution_rate_limit(self):
        """Test that execution rate limit is enforced."""

        # Create executor with lowered limit
        class TestExecutor(SecureExecutor):
            MAX_EXECUTIONS = 3

        executor = TestExecutor()

        # Should work for first 3 executions
        for _ in range(3):
            executor.execute("1 + 1")

        # 4th execution should fail
        with pytest.raises(SecurityError, match="Execution limit exceeded"):
            executor.execute("1 + 1")

    def test_reset_limits(self):
        """Test that rate limit can be reset."""

        # Create executor with lowered limit
        class TestExecutor(SecureExecutor):
            MAX_EXECUTIONS = 2

        executor = TestExecutor()

        # Exhaust limit
        executor.execute("1 + 1")
        executor.execute("1 + 1")

        # Should fail
        with pytest.raises(SecurityError, match="Execution limit exceeded"):
            executor.execute("1 + 1")

        # Reset and try again
        executor.reset_limits()
        result = executor.execute("1 + 1")
        assert result == 2

    def test_execution_blocks_dangerous_patterns(self):
        """Test that dangerous patterns are blocked."""
        executor = SecureExecutor()

        # __ patterns
        with pytest.raises(SecurityError, match="Unsafe pattern"):
            executor.execute("__import__('os')")

        # import
        with pytest.raises(SecurityError, match="Unsafe pattern"):
            executor.execute("import os")

        # exec
        with pytest.raises(SecurityError, match="Unsafe pattern"):
            executor.execute("exec('print(1)')")

        # open
        with pytest.raises(SecurityError, match="Unsafe pattern"):
            executor.execute("open('/etc/passwd')")

    def test_execution_blocks_complex_control_flow(self):
        """Test that complex control flow is blocked."""
        executor = SecureExecutor()

        # for loops
        with pytest.raises(SecurityError, match="Complex control flow not allowed"):
            executor.execute("for i in range(10): i")

        # while loops
        with pytest.raises(SecurityError, match="Complex control flow not allowed"):
            executor.execute("while True: 1")

        # def statements
        with pytest.raises(SecurityError, match="Complex control flow not allowed"):
            executor.execute("def foo(): return 1")

        # class statements
        with pytest.raises(SecurityError, match="Complex control flow not allowed"):
            executor.execute("class Foo: pass")

    def test_execution_timeout(self):
        """Test that timeout is enforced."""
        executor = SecureExecutor()
        executor.MAX_DURATION_SECS = 0.01  # Very short timeout

        # Long computation should timeout
        with pytest.raises(SecurityError, match="Execution timeout"):
            executor.execute("sum([i for i in range(1000000)])")

    def test_caching_behavior(self):
        """Test that Monty instances are cached."""
        executor = SecureExecutor({"x": 10})

        # First execution
        result1 = executor.execute("x + 5")
        assert result1 == 15

        # Second execution with same variables should use cache
        result2 = executor.execute("x + 5")
        assert result2 == 15
        assert len(executor._monty_cache) == 1

    def test_different_variables_separate_cache(self):
        """Test that different variable sets use separate caches."""
        executor1 = SecureExecutor({"x": 10})
        executor2 = SecureExecutor({"x": 20, "y": 5})

        result1 = executor1.execute("x + 5")
        result2 = executor2.execute("x + y")

        assert result1 == 15
        assert result2 == 25

    def test_execution_with_nested_functions(self):
        """Test execution with nested function calls."""
        executor = SecureExecutor()

        result = executor.execute("abs(round(-3.7))")
        assert result == 4

    def test_execution_with_expanded_math_and_science_ops(self):
        """Test expanded math/science operations in executor context."""
        executor = SecureExecutor()

        assert executor.execute("gcd(84, 30)") == 6
        assert executor.execute("lcm(12, 18)") == 36
        assert executor.execute("factorial(5)") == 120
        assert executor.execute("comb(10, 3)") == 120
        assert executor.execute("perm(5, 2)") == 20
        assert executor.execute("percent(120, 12.5)") == pytest.approx(15.0)
        assert executor.execute("degrees(pi)") == pytest.approx(180.0)
        assert executor.execute("radians(180)") == pytest.approx(math.pi)
        assert executor.execute("mean([2, 4, 6, 8])") == 5.0
        assert executor.execute("hypot(8, 15)") == 17.0

        if "c" in executor.MATH_CONSTANTS:
            assert executor.execute("c") > 2.9e8


class TestValidateDataPath:
    """Test validate_data_path function."""

    def test_valid_path_within_base(self, tmp_path):
        """Test that valid path within base is accepted."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()
        file_path = base_dir / "test.data"
        file_path.touch()

        result = validate_data_path(str(base_dir), str(file_path))
        assert result == file_path

    def test_path_traversal_blocked(self, tmp_path):
        """Test that path traversal is blocked."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        # Try to escape with ..
        dangerous_paths = [
            "../etc/passwd",
            "../../sensitive.data",
            "subdir/../../escape.data",
        ]

        for dangerous_path in dangerous_paths:
            with pytest.raises(SecurityError, match="Path traversal detected"):
                validate_data_path(str(base_dir), dangerous_path)

    def test_absolute_path_blocked(self, tmp_path):
        """Test that absolute paths outside base are blocked."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        outside_file = tmp_path / "outside.data"
        outside_file.touch()

        with pytest.raises(SecurityError, match="Path traversal detected"):
            validate_data_path(str(base_dir), str(outside_file))

    def test_symlink_blocked(self, tmp_path):
        """Test that symbolic links are blocked."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        outside_file = tmp_path / "outside.data"
        outside_file.touch()

        symlink_path = base_dir / "symlink.data"
        try:
            symlink_path.symlink_to(outside_file)

            with pytest.raises(SecurityError, match="Symbolic links not allowed"):
                validate_data_path(str(base_dir), str(symlink_path))
        except OSError:
            # Skip if symlinks not supported
            pytest.skip("Symlinks not supported on this system")

    def test_only_data_files_allowed(self, tmp_path):
        """Test that only .data files are allowed."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        # Create files with different extensions
        allowed = base_dir / "allowed.data"
        allowed.touch()

        disallowed_extensions = [".txt", ".json", ".csv", ".md", ""]
        for ext in disallowed_extensions:
            filename = f"test{ext}"
            file_path = base_dir / filename
            file_path.touch()

            if ext:
                with pytest.raises(SecurityError, match="Only .data files allowed"):
                    validate_data_path(str(base_dir), str(file_path))
            else:
                # No extension
                with pytest.raises(SecurityError, match="Only .data files allowed"):
                    validate_data_path(str(base_dir), str(file_path))

    def test_resolved_path_stays_within_base(self, tmp_path):
        """Test that path resolution keeps paths within base."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        subdir = base_dir / "subdir"
        subdir.mkdir()

        # Normalized path
        file_path = subdir / "test.data"
        file_path.touch()

        result = validate_data_path(str(base_dir), "subdir/test.data")
        assert result == file_path

    def test_deeply_nested_valid_path(self, tmp_path):
        """Test that deeply nested valid paths work."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        nested_dir = base_dir / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)

        file_path = nested_dir / "deep.data"
        file_path.touch()

        result = validate_data_path(str(base_dir), str(file_path))
        assert result == file_path


class TestSafeJsonLoad:
    """Test safe_json_load function."""

    def test_valid_json_object(self, tmp_path):
        """Test loading valid JSON object."""
        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42, "nested": {"inner": "data"}}

        file_path.write_text(json.dumps(data))

        result = safe_json_load(file_path)
        assert result == data

    def test_valid_json_array(self, tmp_path):
        """Test loading valid JSON array."""
        file_path = tmp_path / "test.json"
        data = [1, 2, 3, "four", {"five": 5}]

        file_path.write_text(json.dumps(data))

        with pytest.raises(SecurityError, match="JSON must be an object"):
            safe_json_load(file_path)

    def test_invalid_json_syntax(self, tmp_path):
        """Test that invalid JSON syntax is rejected."""
        file_path = tmp_path / "test.json"
        file_path.write_text('{"invalid": json, "missing": quote}')

        with pytest.raises(SecurityError, match="Invalid JSON"):
            safe_json_load(file_path)

    def test_file_too_large(self, tmp_path):
        """Test that oversized files are rejected."""
        file_path = tmp_path / "test.json"
        file_path.write_text("x" * (1024 * 1024 + 1))  # 1MB + 1 byte

        with pytest.raises(SecurityError, match="File too large"):
            safe_json_load(file_path)

    def test_file_exactly_size_limit(self, tmp_path):
        """Test that file at size limit is accepted."""
        file_path = tmp_path / "test.json"
        file_path.write_text("x" * (1024 * 1024))  # Exactly 1MB

        # Should work (assuming valid JSON)
        with pytest.raises(SecurityError, match="Invalid JSON"):  # Not valid JSON, but size is OK
            safe_json_load(file_path)

    def test_nesting_depth_limit(self, tmp_path):
        """Test that deeply nested JSON is rejected."""
        file_path = tmp_path / "test.json"

        # Create deeply nested JSON (15 levels, max is 10)
        nested_data = {"level": 1}
        for i in range(14):
            nested_data = {"level": i + 2, "nested": nested_data}

        file_path.write_text(json.dumps(nested_data))

        with pytest.raises(SecurityError, match="JSON nesting too deep"):
            safe_json_load(file_path)

    def test_nesting_at_limit(self, tmp_path):
        """Test that JSON at nesting limit is accepted."""
        file_path = tmp_path / "test.json"

        # Create nested JSON at exactly 10 levels
        nested_data = {"level": 1}
        for i in range(9):
            nested_data = {"level": i + 2, "nested": nested_data}

        file_path.write_text(json.dumps(nested_data))

        result = safe_json_load(file_path)
        assert result is not None

    def test_invalid_encoding(self, tmp_path):
        """Test that invalid encoding is rejected."""
        file_path = tmp_path / "test.json"
        # Write binary data
        file_path.write_bytes(b"\x80\x81\x82invalid")

        with pytest.raises(SecurityError, match="Invalid encoding"):
            safe_json_load(file_path)

    def test_empty_json_object(self, tmp_path):
        """Test that empty JSON object is accepted."""
        file_path = tmp_path / "test.json"
        file_path.write_text("{}")

        result = safe_json_load(file_path)
        assert result == {}

    def test_complex_json_structure(self, tmp_path):
        """Test loading complex but valid JSON."""
        file_path = tmp_path / "test.json"
        data = {
            "name": "Test",
            "values": [1, 2, 3, 4, 5],
            "config": {
                "enabled": True,
                "timeout": 30,
                "options": ["opt1", "opt2"],
            },
        }

        file_path.write_text(json.dumps(data))

        result = safe_json_load(file_path)
        assert result == data
        assert result["name"] == "Test"
        assert len(result["values"]) == 5


class TestSafeInteger:
    """Test safe_integer function."""

    def test_valid_integer(self):
        """Test conversion of valid integers."""
        assert safe_integer(42) == 42
        assert safe_integer(0) == 0
        assert safe_integer(-100) == -100

    def test_valid_float_whole_number(self):
        """Test conversion of float that is a whole number."""
        assert safe_integer(42.0) == 42
        assert safe_integer(-10.0) == -10

    def test_float_fractional_rejected(self):
        """Test that fractional floats are rejected."""
        with pytest.raises(SecurityError, match="Number out of range"):
            safe_integer(42.5)

        with pytest.raises(SecurityError, match="Number out of range"):
            safe_integer(-10.3)

    def test_nan_rejected(self):
        """Test that NaN is rejected."""
        with pytest.raises(SecurityError, match="Invalid number"):
            safe_integer(float("nan"))

    def test_infinity_rejected(self):
        """Test that infinity is rejected."""
        with pytest.raises(SecurityError, match="Invalid number"):
            safe_integer(float("inf"))

        with pytest.raises(SecurityError, match="Invalid number"):
            safe_integer(float("-inf"))

    def test_large_number_rejected(self):
        """Test that numbers too large are rejected."""
        with pytest.raises(SecurityError, match="Number too large"):
            safe_integer(10**16)

        with pytest.raises(SecurityError, match="Number too large"):
            safe_integer(-(10**16))

    def test_number_at_limit_accepted(self):
        """Test that number at limit is accepted."""
        max_value = 10**15
        assert safe_integer(max_value) == max_value
        assert safe_integer(-max_value) == -max_value

    def test_non_number_rejected(self):
        """Test that non-numbers are rejected."""
        with pytest.raises(SecurityError, match="Not a number"):
            safe_integer("42")

        with pytest.raises(SecurityError, match="Not a number"):
            safe_integer([1, 2, 3])

        with pytest.raises(SecurityError, match="Not a number"):
            safe_integer({"key": "value"})


class TestResourceLimits:
    """Test resource_limits context manager."""

    def test_context_manager_works(self):
        """Test that resource_limits can be used as context manager."""
        # Since Monty handles limits internally, this is now a no-op
        # but should still work as a context manager
        with resource_limits(cpu_time=1, memory_mb=100):
            pass  # Should not raise

    def test_context_manager_no_error(self):
        """Test that exiting context doesn't raise errors."""
        with resource_limits():
            result = 1 + 1
        assert result == 2


class TestSecurityEdgeCases:
    """Test security edge cases."""

    def test_empty_code_execution(self):
        """Test execution of empty code."""
        executor = SecureExecutor()

        with pytest.raises(SecurityError):
            executor.execute("")

    def test_whitespace_only_execution(self):
        """Test execution of whitespace-only code."""
        executor = SecureExecutor()

        with pytest.raises(SecurityError):
            executor.execute("   ")

    def test_multiple_executors_independent(self):
        """Test that multiple executors are independent."""
        exec1 = SecureExecutor({"x": 10})
        exec2 = SecureExecutor({"x": 20})

        result1 = exec1.execute("x * 2")
        result2 = exec2.execute("x * 2")

        assert result1 == 20
        assert result2 == 40

    def test_executor_with_no_variables(self):
        """Test executor with no variables."""
        executor = SecureExecutor()

        result = executor.execute("2 + 3 * 4")
        assert result == 14

    def test_executor_variable_override(self):
        """Test that variables override built-ins."""
        executor = SecureExecutor({"pi": 3.14})

        result = executor.execute("pi")
        assert result == 3.14

    def test_very_long_variable_names(self):
        """Test execution with long variable names."""
        executor = SecureExecutor({"very_long_variable_name": 10})

        result = executor.execute("very_long_variable_name * 2")
        assert result == 20

    def test_special_characters_in_variables(self):
        """Test that special characters in variables work."""
        executor = SecureExecutor({"x_1": 10, "y_2": 5})

        result = executor.execute("x_1 + y_2")
        assert result == 15

    def test_concurrent_execution_safety(self):
        """Test that concurrent executions are safe."""
        executor = SecureExecutor({"x": 10})

        # Simulate concurrent access
        results = []
        for _ in range(10):
            results.append(executor.execute("x + 5"))

        # All should give same result
        assert all(r == 15 for r in results)

    def test_error_propagation(self):
        """Test that errors are properly propagated."""
        executor = SecureExecutor()

        with pytest.raises(SecurityError):
            executor.execute("undefined_variable + 1")

        with pytest.raises(SecurityError):
            executor.execute("1 / 0")

    def test_execution_with_math_constants(self):
        """Test that math constants are available."""
        executor = SecureExecutor()

        import math

        result1 = executor.execute("pi")
        result2 = executor.execute("e")
        result3 = executor.execute("tau")

        assert result1 == math.pi
        assert result2 == math.e
        assert result3 == math.tau


class TestIntegrationScenarios:
    """Test integration scenarios with multiple components."""

    def test_validate_then_load_json(self, tmp_path):
        """Test validating path then loading JSON."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        file_path = base_dir / "test.data"
        data = {"numbers": [1, 2, 3, 4, 5], "sum": 15}
        file_path.write_text(json.dumps(data))

        # Validate path
        validated_path = validate_data_path(str(base_dir), str(file_path))
        assert validated_path == file_path

        # Load JSON
        loaded_data = safe_json_load(validated_path)
        assert loaded_data == data

    def test_execute_with_safe_integer_result(self):
        """Test executing code and converting result to safe integer."""
        executor = SecureExecutor({"x": 10.5})

        result = executor.execute("x * 2")
        safe_int = safe_integer(result)

        assert safe_int == 21

    def test_complex_workflow(self, tmp_path):
        """Test a complex workflow using all components."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        # Create a JSON file with a math problem
        problem_data = {
            "problem": "What is 15 + 27?",
            "variables": {"a": 15, "b": 27},
            "answer": 42,
        }

        file_path = base_dir / "math.data"
        file_path.write_text(json.dumps(problem_data))

        # Validate and load
        validated_path = validate_data_path(str(base_dir), str(file_path))
        data = safe_json_load(validated_path)

        # Use data in executor
        executor = SecureExecutor(data["variables"])
        result = executor.execute("a + b")

        # Validate answer
        answer = safe_integer(result)
        assert answer == data["answer"]

    def test_error_handling_in_workflow(self, tmp_path):
        """Test error handling in integrated workflow."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        # Create JSON with invalid structure
        file_path = base_dir / "invalid.data"
        file_path.write_text('{"key": "value", "trailing": }')

        # Validation should pass
        validated_path = validate_data_path(str(base_dir), str(file_path))

        # Loading should fail gracefully
        with pytest.raises(SecurityError, match="Invalid JSON"):
            safe_json_load(validated_path)

    def test_security_layers_combined(self, tmp_path):
        """Test that all security layers work together."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        # Try to load file from outside base dir
        outside_file = tmp_path / "malicious.data"
        outside_file.write_text('{"attack": true}')

        # Path validation should block
        with pytest.raises(SecurityError, match="Path traversal detected"):
            validate_data_path(str(base_dir), str(outside_file))

        # Even if validation somehow bypassed, execution should block
        executor = SecureExecutor()
        with pytest.raises(SecurityError, match="Unsafe pattern"):
            executor.execute("import os; os.system('ls')")

    def test_large_json_with_depth_check(self, tmp_path):
        """Test JSON size and depth checks together."""
        base_dir = tmp_path / "data"
        base_dir.mkdir()

        file_path = base_dir / "complex.data"

        # Create JSON that's both large and deeply nested
        nested_data = {"level": 1}
        for i in range(8):  # 9 levels total (under limit)
            nested_data = {"level": i + 2, "nested": nested_data, "data": "x" * 100}  # Add bulk

        file_path.write_text(json.dumps(nested_data))

        # Should succeed - size under limit, depth under limit
        result = safe_json_load(file_path)
        assert result is not None


class TestResourceExhaustionProtection:
    """Test protection against resource exhaustion."""

    def test_memory_limit_enforced(self):
        """Test that memory limits are enforced."""
        executor = SecureExecutor()
        executor.MAX_MEMORY_BYTES = 1024  # Very low limit

        # Try to create a very large list
        with pytest.raises(SecurityError, match="Memory limit exceeded"):
            executor.execute("list(range(1000000))")

    def test_allocation_limit_enforced(self):
        """Test that allocation limits are enforced."""
        executor = SecureExecutor()
        executor.MAX_ALLOCATIONS = 1  # Force an allocation-related failure

        # Monty may surface allocation cap exhaustion as a memory-limit failure.
        with pytest.raises(SecurityError, match="Memory limit exceeded"):
            executor.execute("sum([i*i for i in range(1000)])")

    def test_combined_limits(self):
        """Test that multiple limits work together."""
        executor = SecureExecutor()
        executor.MAX_ALLOCATIONS = 50
        executor.MAX_DURATION_SECS = 0.01

        # Larger workload should hit one of the configured runtime guards.
        with pytest.raises(SecurityError, match="Execution timeout|Memory limit exceeded"):
            executor.execute("sum([i for i in range(1000000)])")
