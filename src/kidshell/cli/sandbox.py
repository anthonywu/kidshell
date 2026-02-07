"""
Secure sandbox implementation for kidshell using Monty.
Provides multiple layers of security for executing untrusted Python code.
"""

import json
import math
import pathlib
import re
from contextlib import contextmanager
from typing import Any

import pydantic_monty

from kidshell.core.safe_math import SafeMathEvaluator


class SecurityError(Exception):
    """Raised when security policy is violated"""


class SecureExecutor:
    """
    Main executor with multiple security layers using Monty.
    """

    MAX_ALLOCATIONS = 10000
    MAX_DURATION_SECS = 1.0
    MAX_MEMORY_BYTES = 100 * 1024 * 1024  # 100 MB
    MAX_EXECUTIONS = 1000
    MAX_CODE_LENGTH = SafeMathEvaluator.MAX_STRING_LENGTH

    # Keep sandbox execution policy identical to SafeMathEvaluator so both paths
    # enforce the same allowlist/denylist surface.
    MATH_CONSTANTS = dict(SafeMathEvaluator.MATH_CONSTANTS)
    SAFE_FUNCTIONS = dict(SafeMathEvaluator.SAFE_FUNCTIONS)
    BLOCKED_TOKENS = tuple(SafeMathEvaluator.BLOCKED_TOKENS)
    BLOCKED_STATEMENT_KEYWORDS = tuple(SafeMathEvaluator.BLOCKED_CONTROL_FLOW_KEYWORDS)

    def __init__(self, variables: dict[str, Any] | None = None):
        self.variables = variables or {}
        self.execution_count = 0
        self._monty_cache: dict[tuple[str, tuple[tuple[str, Any], ...]], pydantic_monty.Monty] = {}

    @staticmethod
    def _cache_safe_value(value: Any) -> Any:
        try:
            hash(value)
            return value
        except TypeError:
            # Cache keys must be hashable; repr avoids executing user-provided objects.
            return repr(value)

    @classmethod
    def _find_blocked_pattern(cls, code: str) -> str | None:
        lowered = code.lower()
        if "__" in lowered:
            # Dunder access can enable object introspection/escape attempts.
            return "__"

        for token in cls.BLOCKED_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                # Token denylist blocks dangerous capabilities before execution.
                return token

        return None

    @classmethod
    def _contains_blocked_statement(cls, code: str) -> bool:
        # Restrict to expression-style commands to avoid hidden control-flow payloads.
        return bool(re.match(rf"^\s*(?:{'|'.join(cls.BLOCKED_STATEMENT_KEYWORDS)})\b", code, flags=re.IGNORECASE))

    @classmethod
    def _build_cache_key(cls, code: str, inputs: dict[str, Any]) -> tuple[str, tuple[tuple[str, Any], ...]]:
        frozen_items = tuple(sorted((key, cls._cache_safe_value(value)) for key, value in inputs.items()))
        return code, frozen_items

    def execute(self, code: str, timeout: float = 1.0) -> Any:
        """
        Execute code with multiple security layers using Monty.
        """
        stripped_code = code.strip()
        if not stripped_code:
            # Empty input is rejected to keep parser behavior deterministic.
            raise SecurityError("Empty code not allowed")

        if len(code) > self.MAX_CODE_LENGTH:
            # Input length cap avoids oversized payload abuse.
            raise SecurityError("Code too long")

        blocked_pattern = self._find_blocked_pattern(code)
        if blocked_pattern:
            # Immediate token-level rejection for clearly unsafe content.
            raise SecurityError(f"Unsafe pattern: {blocked_pattern}")

        if self._contains_blocked_statement(code):
            # Explicitly disallow statement-level control flow in sandbox commands.
            raise SecurityError("Complex control flow not allowed")

        # Rate limiting
        self.execution_count += 1
        if self.execution_count > self.MAX_EXECUTIONS:
            # Per-session rate limit helps stop brute-force probing of the sandbox.
            raise SecurityError("Execution limit exceeded")

        # Use Monty for secure execution
        try:
            inputs = dict(self.MATH_CONSTANTS)
            inputs.update(self.variables)
            external_functions = dict(self.SAFE_FUNCTIONS)

            limits = pydantic_monty.ResourceLimits(
                # Hard execution caps: allocations, runtime, and memory.
                max_allocations=self.MAX_ALLOCATIONS,
                max_duration_secs=min(timeout, self.MAX_DURATION_SECS),
                max_memory=self.MAX_MEMORY_BYTES,
            )

            # Check if we have a cached Monty instance
            cache_key = self._build_cache_key(code, inputs)
            if cache_key not in self._monty_cache:
                # Compile once per input-signature and only expose allowlisted names.
                self._monty_cache[cache_key] = pydantic_monty.Monty(
                    code,
                    inputs=list(inputs.keys()),
                    external_functions=list(external_functions.keys()),
                    type_check=False,
                )

            m = self._monty_cache[cache_key]
            result = m.run(
                inputs=inputs,
                external_functions=external_functions,
                limits=limits,
            )

            return result

        except (pydantic_monty.MontySyntaxError, pydantic_monty.MontyRuntimeError) as e:
            error_message = str(e).lower()
            if "time limit exceeded" in error_message or "timeouterror" in error_message:
                # Normalize engine-specific timeout wording.
                raise SecurityError("Execution timeout")
            if "memory limit exceeded" in error_message or "memoryerror" in error_message:
                # Normalize engine-specific memory wording.
                raise SecurityError("Memory limit exceeded")
            if "division by zero" in error_message:
                # Normalize arithmetic faults to stable external behavior.
                raise SecurityError("Division by zero")
            raise SecurityError(f"Execution error: {e}")
        except MemoryError:
            raise SecurityError("Memory limit exceeded")
        except TimeoutError:
            raise SecurityError("Execution timeout")
        except Exception as e:
            raise SecurityError(f"Execution error: {e}")

    def reset_limits(self):
        """Reset rate limiting counter"""
        self.execution_count = 0


@contextmanager
def resource_limits(cpu_time: int = 1, memory_mb: int = 100):
    """
    Context manager to set resource limits.
    Uses Monty's built-in resource limits instead of OS-level limits.
    """
    yield


def validate_data_path(base_dir: str, file_path: str) -> pathlib.Path:
    """
    Validate that a file path stays within the base directory.
    Prevents path traversal attacks.
    """
    base = pathlib.Path(base_dir).resolve()
    raw_target = pathlib.Path(file_path)
    # Resolve relative paths against the trusted base directory, not process CWD.
    candidate = raw_target if raw_target.is_absolute() else base / raw_target

    # Check symlink on the unresolved candidate path.
    if candidate.exists() and candidate.is_symlink():
        # Symlink traversal can bypass containment checks.
        raise SecurityError("Symbolic links not allowed")

    target = candidate.resolve()

    # Ensure target is within base directory
    try:
        target.relative_to(base)
    except ValueError:
        # Reject any path that escapes base_dir after full resolution.
        raise SecurityError(f"Path traversal detected: {file_path}")

    # Additional checks
    if target.suffix != ".data":
        # Narrow file-type surface for sandboxed data payloads.
        raise SecurityError("Only .data files allowed")

    return target


def safe_json_load(file_path: pathlib.Path, max_size: int = 1024 * 1024) -> dict:
    """
    Safely load JSON with size limits and validation.
    """
    # Check file size
    if file_path.stat().st_size > max_size:
        # Avoid loading oversized files into memory.
        raise SecurityError(f"File too large: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            # Read with size limit
            content = f.read(max_size)

            # Parse JSON
            data = json.loads(content)

            # Validate structure (basic check)
            if not isinstance(data, dict):
                # Only object-shaped payloads are expected by callers.
                raise SecurityError("JSON must be an object")

            # Limit nesting depth
            def check_depth(obj, depth=0, max_depth=10):
                if depth > max_depth:
                    # Depth cap prevents recursive/nested payload abuse.
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
        if not math.isfinite(value):
            # Explicitly reject NaN/Inf before conversion.
            raise SecurityError(f"Invalid number: {value}")

        # Check if it's a whole number
        if value.is_integer() and abs(value) <= max_value:
            return int(value)
        # Reject fractional or huge float payloads.
        raise SecurityError(f"Number out of range: {value}")

    if isinstance(value, int):
        if abs(value) > max_value:
            # Bound integer size to avoid untrusted extreme values.
            raise SecurityError(f"Number too large: {value}")
        return value

    # Reject non-numeric inputs outright.
    raise SecurityError(f"Not a number: {value}")


# Export main components
__all__ = [
    "SecureExecutor",
    "SecurityError",
    "resource_limits",
    "safe_integer",
    "safe_json_load",
    "validate_data_path",
]
