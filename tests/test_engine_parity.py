"""Regression tests for engine parity and handler routing."""

from kidshell.core.engine import KidShellEngine
from kidshell.core.models import Session
from kidshell.core.types import ResponseType


def test_math_lookup_handler_resolves_constants():
    """Math constants should be resolved through session math env lookup."""
    engine = KidShellEngine(Session())
    response = engine.process_input("pi")

    assert response.type == ResponseType.MATH_RESULT
    assert response.content["expression"] == "pi"
    assert response.content["result"] > 3.14


def test_custom_data_lookup_is_available():
    """Custom data should be resolved before broad text handlers."""
    session = Session()
    session.custom_data = {"hello": "world"}
    engine = KidShellEngine(session)

    response = engine.process_input("HELLO")

    assert response.type == ResponseType.TEXT
    assert response.content == "world"


def test_custom_data_lookup_precedes_color_handler():
    """Custom data entries should override color-name matches."""
    session = Session()
    session.custom_data = {"blue": "ocean"}
    engine = KidShellEngine(session)

    response = engine.process_input("blue")

    assert response.type == ResponseType.TEXT
    assert response.content == "ocean"


def test_short_alpha_word_prefers_symbol_flow():
    """Short alpha input should create a symbol, not stop at emoji fallback."""
    engine = KidShellEngine(Session())
    response = engine.process_input("foo")

    assert response.type == ResponseType.SYMBOL_RESULT
    assert response.content["action"] == "created"
    assert response.content["symbol"] == "foo"


def test_symbol_assignment_after_symbol_creation_is_numeric():
    """Symbol assignment should work even after symbol placeholder creation."""
    engine = KidShellEngine(Session())

    created = engine.process_input("x")
    assigned = engine.process_input("x = 2")
    expression = engine.process_input("x+3")

    assert created.type == ResponseType.SYMBOL_RESULT
    assert assigned.type == ResponseType.SYMBOL_RESULT
    assert assigned.content["value"] == 2
    assert expression.type == ResponseType.SYMBOL_RESULT
    assert expression.content["result"] == 5


def test_symbol_assignment_updates_math_lookup():
    """Assigned symbols should be available via direct math lookup."""
    engine = KidShellEngine(Session())
    engine.process_input("x = 10")

    lookup = engine.process_input("x")

    assert lookup.type == ResponseType.MATH_RESULT
    assert lookup.content["result"] == 10


def test_keyboard_smash_and_gibberish_handlers():
    """Repeated chars and long gibberish should use dedicated handlers."""
    engine = KidShellEngine(Session())

    repeated = engine.process_input("aaaaaa")
    gibberish = engine.process_input("asdasdasdasd")

    assert repeated.type == ResponseType.TEXT
    assert repeated.content == "6 x a"
    assert gibberish.type == ResponseType.TEXT
    assert "a:" in gibberish.content
    assert "s:" in gibberish.content
    assert "d:" in gibberish.content


def test_quiz_does_not_hijack_loop_input():
    """Loop syntax should still route to loop handler when quiz is active."""
    engine = KidShellEngine(Session())
    engine.session.current_quiz = {
        "id": "q1",
        "question": "2 + 2",
        "answer": 4,
        "difficulty": 1,
        "type": "math",
    }

    response = engine.process_input("0...5...2")

    assert response.type == ResponseType.LOOP_RESULT


def test_emoji_lookup_precedes_symbol_for_known_word():
    """Known emoji words (e.g., tree) should resolve to emoji responses."""
    engine = KidShellEngine(Session())

    response = engine.process_input("tree")

    assert response.type == ResponseType.EMOJI
    assert response.content["found"] is True


def test_symbol_expression_with_undefined_name_returns_coaching():
    """Undefined symbol expressions should coach assignment instead of erroring."""
    engine = KidShellEngine(Session())

    response = engine.process_input("x + 2")

    assert response.type == ResponseType.TEXT
    assert "x = 3" in response.content
    assert "x + 2" in response.content


def test_math_interprets_x_between_numbers_as_multiplication():
    """`8 x 6` should evaluate as multiplication with a friendly clarification note."""
    engine = KidShellEngine(Session())

    response = engine.process_input("8 x 6")

    assert response.type == ResponseType.MATH_RESULT
    assert response.content["result"] == 48
    assert response.content["expression"] == "8 * 6"
    assert "Interpreted 'x' as multiplication" in response.content["note"]
