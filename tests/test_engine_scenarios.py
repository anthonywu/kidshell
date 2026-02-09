"""Scenario-DSL based multi-turn interaction tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from kidshell.core.engine import KidShellEngine
from kidshell.core.models import Session
from kidshell.core.services.quiz_service import QuizService
from kidshell.core.types import ResponseType
from tests.scenario_dsl import (
    Scenario,
    expect_response,
    expect_state,
    run_scenario,
    step,
)


def _quiz(quiz_id: str, question: str, answer: int) -> dict:
    return {
        "id": quiz_id,
        "question": question,
        "answer": answer,
        "difficulty": 1,
        "type": "math",
        "operation": "+",
        "operands": [answer, 0],
    }


@pytest.fixture
def scripted_quizzes(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[list[dict]], None]:
    """Install deterministic quiz generation for scenarios."""

    def _install(quizzes: list[dict]) -> None:
        if not quizzes:
            raise ValueError("scripted_quizzes requires at least one quiz")

        script = [dict(quiz) for quiz in quizzes]
        cursor = {"index": 0}

        def _generate_math_question(*, difficulty: int = 1) -> dict:
            idx = min(cursor["index"], len(script) - 1)
            cursor["index"] += 1
            quiz = dict(script[idx])
            quiz["difficulty"] = difficulty
            return quiz

        monkeypatch.setattr(
            QuizService,
            "generate_math_question",
            staticmethod(_generate_math_question),
        )

    return _install


def test_scenario_quiz_progression(scripted_quizzes):
    """Scenario: quiz starts, wrong attempt increments, correct answer advances."""
    scripted_quizzes(
        [
            _quiz("q1", "2 + 3", 5),
            _quiz("q2", "4 + 4", 8),
        ]
    )
    scenario = Scenario(
        name="quiz progression",
        turns=[
            step(
                "",
                response=expect_response(
                    ResponseType.QUIZ,
                    content_subset={"id": "q1"},
                ),
                state=expect_state(current_quiz_id="q1"),
            ),
            step(
                "99",
                response=expect_response(
                    ResponseType.QUIZ,
                    content_subset={"correct": False, "attempts": 1},
                ),
                state=expect_state(
                    current_streak=0,
                    current_quiz_id="q1",
                    quiz_attempts_subset={"q1": 1},
                ),
            ),
            step(
                "5",
                response=expect_response(
                    ResponseType.QUIZ,
                    content_subset={"correct": True, "next_quiz": {"id": "q2"}},
                ),
                state=expect_state(
                    problems_solved=1,
                    current_streak=1,
                    current_quiz_id="q2",
                    quiz_attempts_subset={"q1": 2},
                ),
            ),
        ],
    )
    run_scenario(scenario)


def test_scenario_achievement_then_pending_response(scripted_quizzes):
    """Scenario: achievement response queues and emits pending quiz payload."""
    scripted_quizzes([_quiz("q2", "3 + 3", 6)])
    session = Session()
    session.problems_solved = 4
    session.current_streak = 4
    session.current_quiz = _quiz("q1", "2 + 3", 5)

    scenario = Scenario(
        name="achievement pending response",
        session=session,
        turns=[
            step(
                "5",
                response=expect_response(
                    ResponseType.ACHIEVEMENT,
                    content_subset={"total_solved": 5},
                ),
                pending=expect_response(
                    ResponseType.QUIZ,
                    content_subset={"correct": True, "next_quiz": {"id": "q2"}},
                ),
                state=expect_state(
                    problems_solved=5,
                    current_streak=5,
                    current_quiz_id="q2",
                    achievements_includes={"first_five", "streak_5"},
                ),
            ),
            step(
                "6",
                response=expect_response(ResponseType.QUIZ, content_subset={"correct": True}),
                expect_no_pending=True,
            ),
        ],
    )
    run_scenario(scenario)


def test_scenario_symbol_and_custom_data_journey():
    """Scenario: custom data, symbol creation, assignment, expression, and lookup."""
    session = Session()
    session.custom_data = {"blue": "ocean", "hello": "world"}
    scenario = Scenario(
        name="symbol + custom data journey",
        session=session,
        turns=[
            step(
                "blue",
                response=expect_response(ResponseType.TEXT, content_equals="ocean"),
                state=expect_state(custom_data_subset={"blue": "ocean"}),
            ),
            step(
                "x",
                response=expect_response(
                    ResponseType.SYMBOL_RESULT,
                    content_subset={"symbol": "x", "action": "created"},
                ),
                state=expect_state(symbols_include={"x"}),
            ),
            step(
                "x = 7",
                response=expect_response(
                    ResponseType.SYMBOL_RESULT,
                    content_subset={"symbol": "x", "value": 7, "action": "assigned"},
                ),
                state=expect_state(last_number=0, symbols_include={"x"}),
            ),
            step(
                "x + 3",
                response=expect_response(
                    ResponseType.SYMBOL_RESULT,
                    content_subset={"result": 10, "display": "x + 3 = 10"},
                ),
                state=expect_state(last_number=10),
            ),
            step(
                "x",
                response=expect_response(
                    ResponseType.MATH_RESULT,
                    content_subset={"result": 7},
                ),
                state=expect_state(last_number=7),
            ),
            step(
                "HELLO",
                response=expect_response(ResponseType.TEXT, content_equals="world"),
            ),
        ],
    )
    run_scenario(scenario)


def test_scenario_quiz_state_roundtrip_resume(scripted_quizzes):
    """Scenario: persist state mid-quiz and continue in a restored engine."""
    scripted_quizzes(
        [
            _quiz("q1", "2 + 3", 5),
            _quiz("q2", "4 + 4", 8),
        ]
    )
    first_half = Scenario(
        name="roundtrip part 1",
        turns=[
            step("", response=expect_response(ResponseType.QUIZ, content_subset={"id": "q1"})),
            step(
                "99",
                response=expect_response(ResponseType.QUIZ, content_subset={"correct": False, "attempts": 1}),
                state=expect_state(current_quiz_id="q1", quiz_attempts_subset={"q1": 1}),
            ),
        ],
    )
    engine = run_scenario(first_half)

    snapshot = engine.get_session_state()
    restored = KidShellEngine(Session())
    restored.restore_session_state(snapshot)

    second_half = Scenario(
        name="roundtrip part 2",
        turns=[
            step(
                "5",
                response=expect_response(
                    ResponseType.QUIZ,
                    content_subset={"correct": True, "next_quiz": {"id": "q2"}},
                ),
                state=expect_state(
                    problems_solved=1,
                    current_streak=1,
                    current_quiz_id="q2",
                    quiz_attempts_subset={"q1": 2},
                ),
            ),
        ],
    )
    run_scenario(second_half, engine=restored)
