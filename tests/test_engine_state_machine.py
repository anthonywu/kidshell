"""Multi-turn state-machine tests for KidShellEngine sessions."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from kidshell.core.engine import KidShellEngine
from kidshell.core.models import Session
from kidshell.core.services.quiz_service import QuizService
from kidshell.core.types import ResponseType


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
    """Install a deterministic quiz script for multi-turn state tests."""

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


def test_quiz_lifecycle_wrong_then_correct_generates_next(scripted_quizzes):
    """Quiz state should progress across wrong and correct multi-turn answers."""
    scripted_quizzes(
        [
            _quiz("q1", "2 + 3", 5),
            _quiz("q2", "4 + 4", 8),
        ]
    )
    engine = KidShellEngine(Session())

    initial = engine.process_input("")
    assert initial.type == ResponseType.QUIZ
    assert engine.session.current_quiz["id"] == "q1"

    wrong = engine.process_input("99")
    assert wrong.type == ResponseType.QUIZ
    assert wrong.content["correct"] is False
    assert wrong.content["attempts"] == 1
    assert "Great attempt" in wrong.content["hint"]
    assert "number_facts" in wrong.content
    assert wrong.content["number_facts"]["number"] == 99
    assert engine.session.quiz_attempts["q1"] == 1
    assert engine.session.current_streak == 0

    correct = engine.process_input("5")
    assert correct.type == ResponseType.QUIZ
    assert correct.content["correct"] is True
    assert correct.content["question"] == "2 + 3"
    assert correct.content["quiz"]["id"] == "q1"
    assert correct.content["next_quiz"]["id"] == "q2"
    assert engine.session.problems_solved == 1
    assert engine.session.current_streak == 1
    assert engine.session.quiz_attempts["q1"] == 2
    assert engine.session.current_quiz["id"] == "q2"


def test_achievement_response_exposes_pending_quiz_payload(scripted_quizzes):
    """Achievement responses should queue the underlying quiz response as pending."""
    scripted_quizzes([_quiz("q2", "3 + 3", 6)])
    session = Session()
    session.problems_solved = 4
    session.current_streak = 4
    session.current_quiz = _quiz("q1", "2 + 3", 5)
    engine = KidShellEngine(session)

    achievement = engine.process_input("5")
    assert achievement.type == ResponseType.ACHIEVEMENT
    assert set(achievement.content["achievements"]) >= {"first_five", "streak_5"}
    assert achievement.content["total_solved"] == 5

    pending = engine.get_pending_response()
    assert pending is not None
    assert pending.type == ResponseType.QUIZ
    assert pending.content["correct"] is True
    assert pending.content["next_quiz"]["id"] == "q2"
    assert engine.session.current_quiz["id"] == "q2"

    assert engine.get_pending_response() is None


def test_active_quiz_still_allows_non_answer_handlers(scripted_quizzes):
    """Loop and other handlers should still run while a quiz is active."""
    scripted_quizzes([_quiz("q2", "9 + 1", 10)])
    session = Session()
    session.current_quiz = _quiz("q1", "2 + 2", 4)
    engine = KidShellEngine(session)

    loop_response = engine.process_input("0...4...2")
    assert loop_response.type == ResponseType.LOOP_RESULT
    assert loop_response.content["numbers"] == [0, 2, 4]
    assert engine.session.current_quiz["id"] == "q1"

    answer_response = engine.process_input("4")
    assert answer_response.type == ResponseType.QUIZ
    assert answer_response.content["correct"] is True
    assert engine.session.current_quiz["id"] == "q2"


def test_last_number_progresses_across_math_turns():
    """Stateful math operators should chain across turns via last_number."""
    engine = KidShellEngine(Session())

    first = engine.process_input("2 + 3")
    second = engine.process_input("+5")
    third = engine.process_input("*2")

    assert first.type == ResponseType.MATH_RESULT
    assert first.content["result"] == 5
    assert second.type == ResponseType.MATH_RESULT
    assert second.content["result"] == 10
    assert third.type == ResponseType.MATH_RESULT
    assert third.content["result"] == 20
    assert engine.session.math_env["last_number"] == 20


def test_symbol_progression_then_numeric_lookup():
    """Symbol creation/assignment should converge to numeric lookup across turns."""
    engine = KidShellEngine(Session())

    created = engine.process_input("x")
    assigned = engine.process_input("x = 7")
    expression = engine.process_input("x + 3")
    lookup = engine.process_input("x")

    assert created.type == ResponseType.SYMBOL_RESULT
    assert created.content["action"] == "created"
    assert assigned.type == ResponseType.SYMBOL_RESULT
    assert assigned.content["value"] == 7
    assert expression.type == ResponseType.SYMBOL_RESULT
    assert expression.content["result"] == 10
    assert lookup.type == ResponseType.MATH_RESULT
    assert lookup.content["result"] == 7


def test_custom_data_precedence_persists_over_turns():
    """Custom mappings should remain stable across multi-turn interactions."""
    session = Session()
    session.custom_data = {"blue": "ocean", "hello": "world"}
    engine = KidShellEngine(session)

    blue_1 = engine.process_input("blue")
    math_turn = engine.process_input("2 + 2")
    hello = engine.process_input("HELLO")
    blue_2 = engine.process_input("blue")

    assert blue_1.type == ResponseType.TEXT
    assert blue_1.content == "ocean"
    assert math_turn.type == ResponseType.MATH_RESULT
    assert hello.type == ResponseType.TEXT
    assert hello.content == "world"
    assert blue_2.type == ResponseType.TEXT
    assert blue_2.content == "ocean"


def test_session_roundtrip_preserves_quiz_state(scripted_quizzes):
    """Serialized session should restore multi-turn quiz progress correctly."""
    scripted_quizzes(
        [
            _quiz("q1", "2 + 3", 5),
            _quiz("q2", "4 + 4", 8),
        ]
    )
    first_engine = KidShellEngine(Session())
    first_engine.process_input("")
    first_engine.process_input("99")

    state = first_engine.get_session_state()
    restored_engine = KidShellEngine(Session())
    restored_engine.restore_session_state(state)

    assert restored_engine.session.current_quiz is not None
    assert restored_engine.session.current_quiz["id"] == "q1"
    assert restored_engine.session.quiz_attempts["q1"] == 1
    assert restored_engine.session.current_streak == 0

    correct = restored_engine.process_input("5")
    assert correct.type == ResponseType.QUIZ
    assert correct.content["correct"] is True
    assert restored_engine.session.current_quiz["id"] == "q2"
    assert restored_engine.session.problems_solved == 1


def test_quiz_wrong_answer_after_multiple_attempts_handles_numeric_input_gracefully():
    """Wrong numeric answers should never crash when hinting after 3+ attempts."""
    session = Session()
    session.current_quiz = _quiz("q1", "7 - 5", 2)
    session.quiz_attempts = {"q1": 2}
    engine = KidShellEngine(session)

    response = engine.process_input("21")

    assert response.type == ResponseType.QUIZ
    assert response.content["correct"] is False
    assert response.content["attempts"] == 3
    assert response.content["number_facts"]["number"] == 21
    assert "Helpful clue" in response.content["hint"]
