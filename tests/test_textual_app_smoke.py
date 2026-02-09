"""Smoke tests for the Textual frontend startup path."""

import asyncio

from textual.widgets import TextArea

from kidshell.frontends.textual_app.app import KidShellTextualApp
from kidshell.frontends.textual_app.app import ResponseDisplay
from kidshell.core.types import ResponseType


def test_textual_app_starts_headless_without_internal_timer_collision():
    """App startup should not overwrite Textual's internal timing fields."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.pause()

    asyncio.run(_run())


def test_response_display_handles_quiz_feedback_dict_payload():
    """Quiz feedback payloads should render without treating dict as Textual visual content."""
    widget = ResponseDisplay(
        ResponseType.QUIZ,
        {
            "correct": False,
            "user_answer": "3",
            "hint": "Great attempt! Keep going on this one.",
            "encouragement": "Nice thinking with 3! Let's explore it while we keep going.",
            "attempts": 1,
            "quiz": {"question": "7 - 5", "answer": 2},
            "number_facts": {"number": 3, "factors": [(1, 3)], "properties": [("Odd number", "orange")]},
        },
    )
    assert isinstance(widget.payload, dict)
    assert widget.payload["hint"] == "Great attempt! Keep going on this one."


def test_textual_app_accepts_numeric_quiz_answer_without_crashing():
    """Submitting a numeric answer should append history and not crash the app."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.press("3", "enter")
            await pilot.pause()
            history = app.query_one("#history", TextArea)
            assert history.read_only is True
            assert "> 3" in history.text

    asyncio.run(_run())
