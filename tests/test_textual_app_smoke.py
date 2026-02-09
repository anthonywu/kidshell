"""Smoke tests for the Textual frontend startup path."""

import asyncio
from types import SimpleNamespace

from textual.containers import Vertical
from textual.widgets import Label, TextArea

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


def test_textual_app_includes_macos_copy_paste_shortcuts():
    """App bindings should include Command-key copy/paste aliases."""
    keys = {binding.key for binding in KidShellTextualApp.BINDINGS}
    assert "super+c" in keys
    assert "super+v" in keys
    assert "meta+c" in keys
    assert "meta+v" in keys


def test_textual_app_vim_quit_alias_terminates_without_processing(monkeypatch):
    """Vim-style quit alias should exit the TUI before regular input handling."""
    app = KidShellTextualApp()
    processed_inputs: list[str] = []
    exit_calls: list[bool] = []

    monkeypatch.setattr("kidshell.frontends.textual_app.app.save_persisted_session", lambda _session: True)
    monkeypatch.setattr(app.engine, "process_input", lambda input_text: processed_inputs.append(input_text))
    monkeypatch.setattr(app, "exit", lambda *args, **kwargs: exit_calls.append(True))

    asyncio.run(app.handle_input(SimpleNamespace(value=":q!")))  # type: ignore[arg-type]

    assert exit_calls == [True]
    assert processed_inputs == []


def test_textual_app_progress_track_updates_with_solved_count():
    """Progress pane should reflect solved-count changes with a moving emoji lane."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            progress = app.query_one("#achievement-progress", Label)
            initial = str(progress.content)

            app.engine.session.problems_solved = 5
            app._update_stats()
            updated = str(progress.content)

            assert "Solved: 5" in updated
            assert updated != initial
            assert any(emoji in updated for emoji in {"🚣", "🛫", "🚋"})

    asyncio.run(_run())


def test_textual_app_color_input_updates_theme_palette():
    """Typing a recognized color should retheme the TUI palette."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            stats_panel = app.query_one(".stats-panel", Vertical)
            history_container = app.query_one(".history-container", Vertical)
            initial_border_color = stats_panel.styles.border.top[1]
            initial_history_background = history_container.styles.background

            await pilot.press("o", "r", "a", "n", "g", "e", "enter")
            await pilot.pause()

            updated_border_color = stats_panel.styles.border.top[1]
            updated_history_background = history_container.styles.background
            history = app.query_one("#history", TextArea)

            assert updated_border_color != initial_border_color
            assert updated_history_background != initial_history_background
            assert "Theme shifted to match your color." in history.text

    asyncio.run(_run())
