"""Scenario DSL helpers for multi-turn KidShellEngine state-machine tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kidshell.core.engine import KidShellEngine
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType

_UNSET = object()


def _assert_mapping_subset(actual: Any, expected: dict[str, Any], *, label: str) -> None:
    if not isinstance(actual, dict):
        raise AssertionError(f"{label} expected mapping, got {type(actual)!r}")

    for key, expected_value in expected.items():
        if key not in actual:
            raise AssertionError(f"{label} missing key: {key!r}")
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            _assert_mapping_subset(
                actual_value,
                expected_value,
                label=f"{label}[{key!r}]",
            )
        else:
            assert actual_value == expected_value, (
                f"{label}[{key!r}] expected {expected_value!r}, got {actual_value!r}"
            )


@dataclass(slots=True)
class ResponseExpectation:
    """Declarative response expectation for one turn."""

    type: ResponseType | None = None
    content_subset: dict[str, Any] | None = None
    metadata_subset: dict[str, Any] | None = None
    content_equals: Any = _UNSET
    check: Any = None

    def assert_matches(self, response: Response, *, turn: int, stage: str) -> None:
        prefix = f"turn {turn} {stage}"
        if self.type is not None:
            assert response.type == self.type, f"{prefix} expected type {self.type.value}, got {response.type.value}"

        if self.content_equals is not _UNSET:
            assert response.content == self.content_equals, (
                f"{prefix} expected exact content {self.content_equals!r}, got {response.content!r}"
            )

        if self.content_subset is not None:
            _assert_mapping_subset(response.content, self.content_subset, label=f"{prefix} content")

        if self.metadata_subset is not None:
            _assert_mapping_subset(response.metadata, self.metadata_subset, label=f"{prefix} metadata")

        if self.check is not None:
            self.check(response)


@dataclass(slots=True)
class StateExpectation:
    """Declarative session-state expectation after one turn."""

    problems_solved: int | object = _UNSET
    current_streak: int | object = _UNSET
    current_quiz_id: str | None | object = _UNSET
    last_number: int | float | bool | object = _UNSET
    achievements_includes: set[str] = field(default_factory=set)
    symbols_include: set[str] = field(default_factory=set)
    quiz_attempts_subset: dict[str, int] = field(default_factory=dict)
    custom_data_subset: dict[str, Any] = field(default_factory=dict)
    check: Any = None

    def assert_matches(self, session: Session, *, turn: int) -> None:
        prefix = f"turn {turn} state"

        if self.problems_solved is not _UNSET:
            assert session.problems_solved == self.problems_solved, (
                f"{prefix} expected problems_solved={self.problems_solved}, got {session.problems_solved}"
            )

        if self.current_streak is not _UNSET:
            assert session.current_streak == self.current_streak, (
                f"{prefix} expected current_streak={self.current_streak}, got {session.current_streak}"
            )

        if self.current_quiz_id is not _UNSET:
            actual_quiz_id = session.current_quiz.get("id") if session.current_quiz else None
            assert actual_quiz_id == self.current_quiz_id, (
                f"{prefix} expected current_quiz_id={self.current_quiz_id!r}, got {actual_quiz_id!r}"
            )

        if self.last_number is not _UNSET:
            actual_last_number = session.math_env.get("last_number")
            assert actual_last_number == self.last_number, (
                f"{prefix} expected last_number={self.last_number!r}, got {actual_last_number!r}"
            )

        if self.achievements_includes:
            missing = self.achievements_includes.difference(set(session.achievements))
            assert not missing, f"{prefix} missing achievements: {sorted(missing)}"

        if self.symbols_include:
            missing_symbols = self.symbols_include.difference(set(session.symbols_env))
            assert not missing_symbols, f"{prefix} missing symbols: {sorted(missing_symbols)}"

        if self.quiz_attempts_subset:
            for key, value in self.quiz_attempts_subset.items():
                actual_value = session.quiz_attempts.get(key)
                assert actual_value == value, f"{prefix} expected quiz_attempts[{key!r}]={value}, got {actual_value!r}"

        if self.custom_data_subset:
            _assert_mapping_subset(session.custom_data, self.custom_data_subset, label=f"{prefix} custom_data")

        if self.check is not None:
            self.check(session)


@dataclass(slots=True)
class Turn:
    """One interaction turn in a scenario."""

    input_text: str
    response: ResponseExpectation
    state: StateExpectation | None = None
    pending: ResponseExpectation | None = None
    expect_no_pending: bool = False


@dataclass(slots=True)
class Scenario:
    """Executable multi-turn interaction scenario."""

    name: str
    turns: list[Turn]
    session: Session | None = None
    setup: Any = None


def expect_response(
    response_type: ResponseType | None = None,
    *,
    content_subset: dict[str, Any] | None = None,
    metadata_subset: dict[str, Any] | None = None,
    content_equals: Any = _UNSET,
    check: Any = None,
) -> ResponseExpectation:
    """Build a response expectation."""
    return ResponseExpectation(
        type=response_type,
        content_subset=content_subset,
        metadata_subset=metadata_subset,
        content_equals=content_equals,
        check=check,
    )


def expect_state(
    *,
    problems_solved: int | object = _UNSET,
    current_streak: int | object = _UNSET,
    current_quiz_id: str | None | object = _UNSET,
    last_number: int | float | bool | object = _UNSET,
    achievements_includes: set[str] | None = None,
    symbols_include: set[str] | None = None,
    quiz_attempts_subset: dict[str, int] | None = None,
    custom_data_subset: dict[str, Any] | None = None,
    check: Any = None,
) -> StateExpectation:
    """Build a state expectation."""
    return StateExpectation(
        problems_solved=problems_solved,
        current_streak=current_streak,
        current_quiz_id=current_quiz_id,
        last_number=last_number,
        achievements_includes=achievements_includes or set(),
        symbols_include=symbols_include or set(),
        quiz_attempts_subset=quiz_attempts_subset or {},
        custom_data_subset=custom_data_subset or {},
        check=check,
    )


def step(
    input_text: str,
    *,
    response: ResponseExpectation,
    state: StateExpectation | None = None,
    pending: ResponseExpectation | None = None,
    expect_no_pending: bool = False,
) -> Turn:
    """Build one scenario turn."""
    return Turn(
        input_text=input_text,
        response=response,
        state=state,
        pending=pending,
        expect_no_pending=expect_no_pending,
    )


def run_scenario(
    scenario: Scenario,
    *,
    engine: KidShellEngine | None = None,
) -> KidShellEngine:
    """Execute a scenario and assert all expectations."""
    active_engine = engine
    if active_engine is None:
        session = scenario.session or Session()
        active_engine = KidShellEngine(session)

    if scenario.setup is not None:
        scenario.setup(active_engine.session)

    for index, turn in enumerate(scenario.turns, start=1):
        response = active_engine.process_input(turn.input_text)
        turn.response.assert_matches(response, turn=index, stage="response")

        if turn.pending is not None:
            pending = active_engine.get_pending_response()
            assert pending is not None, f"turn {index} expected pending response but found none"
            turn.pending.assert_matches(pending, turn=index, stage="pending")
        elif turn.expect_no_pending:
            pending = active_engine.get_pending_response()
            assert pending is None, f"turn {index} expected no pending response, got {pending!r}"

        if turn.state is not None:
            turn.state.assert_matches(active_engine.session, turn=index)

    return active_engine
