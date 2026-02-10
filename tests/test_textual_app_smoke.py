"""Smoke tests for the Textual frontend startup path."""

import asyncio
from types import SimpleNamespace

import pytest
from textual.css.query import NoMatches
from textual.containers import Horizontal, Vertical
from textual.widgets import HelpPanel, Label, TextArea

from kidshell.frontends.textual_app.app import KidShellTextualApp
from kidshell.frontends.textual_app.app import MOTION_EMOJIS
from kidshell.frontends.textual_app.app import ResponseDisplay
from kidshell.core.types import Response, ResponseType


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


@pytest.mark.parametrize("exit_word", [":q!", "bye", "quit", "exit", "close"])
def test_textual_app_reserved_exit_inputs_terminate_without_processing(monkeypatch, exit_word: str):
    """Reserved quit aliases should exit the TUI before regular input handling."""
    app = KidShellTextualApp()
    processed_inputs: list[str] = []
    exit_calls: list[bool] = []

    monkeypatch.setattr("kidshell.frontends.textual_app.app.save_persisted_session", lambda _session: True)
    monkeypatch.setattr(app.engine, "process_input", lambda input_text: processed_inputs.append(input_text))
    monkeypatch.setattr(app, "exit", lambda *args, **kwargs: exit_calls.append(True))

    asyncio.run(app.handle_input(SimpleNamespace(value=exit_word)))  # type: ignore[arg-type]

    assert exit_calls == [True]
    assert processed_inputs == []


def test_textual_app_help_input_shows_help_panel_without_processing(monkeypatch):
    """Typing help should open the help panel and skip engine processing."""
    app = KidShellTextualApp()
    processed_inputs: list[str] = []
    help_toggle_calls: list[bool] = []
    fake_input = SimpleNamespace(value="help")

    monkeypatch.setattr(app.engine, "process_input", lambda input_text: processed_inputs.append(input_text))
    monkeypatch.setattr(app, "action_toggle_help_panel", lambda *args, **kwargs: help_toggle_calls.append(True))

    asyncio.run(app.handle_input(SimpleNamespace(value="help", input=fake_input)))  # type: ignore[arg-type]

    assert help_toggle_calls == [True]
    assert processed_inputs == []
    assert fake_input.value == ""


@pytest.mark.parametrize("magic_word", [":fireworks", "fireworks", ":boom"])
def test_textual_app_fireworks_magic_input_triggers_animation_without_processing(monkeypatch, magic_word: str):
    """Manual fireworks command should run celebration path and skip engine processing."""
    app = KidShellTextualApp()
    processed_inputs: list[str] = []
    fireworks_calls: list[bool] = []
    fake_input = SimpleNamespace(value=magic_word)

    monkeypatch.setattr(app.engine, "process_input", lambda input_text: processed_inputs.append(input_text))
    monkeypatch.setattr(
        app,
        "_start_manual_fireworks_celebration",
        lambda *args, **kwargs: fireworks_calls.append(True),
    )
    monkeypatch.setattr("kidshell.frontends.textual_app.app.save_persisted_session", lambda _session: True)
    monkeypatch.setattr(
        app,
        "query_one",
        lambda _selector, _type: SimpleNamespace(
            document=SimpleNamespace(end=0),
            insert=lambda *_args, **_kwargs: None,
            scroll_end=lambda **_kwargs: None,
        ),
    )

    asyncio.run(app.handle_input(SimpleNamespace(value=magic_word, input=fake_input)))  # type: ignore[arg-type]

    assert fireworks_calls == [True]
    assert processed_inputs == []
    assert fake_input.value == ""


def test_textual_app_help_action_toggles_panel():
    """Help action should open and then close the help panel."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            with pytest.raises(NoMatches):
                app.screen.query_one(HelpPanel)

            app.action_toggle_help_panel()
            await pilot.pause()
            assert app.screen.query_one(HelpPanel) is not None

            app.action_toggle_help_panel()
            await pilot.pause()
            with pytest.raises(NoMatches):
                app.screen.query_one(HelpPanel)

    asyncio.run(_run())


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
            assert any(emoji in updated for emoji in MOTION_EMOJIS)

    asyncio.run(_run())


def test_textual_history_formats_correct_quiz_with_solved_equation():
    """Quiz success transcript should include solved question and answer."""
    app = KidShellTextualApp()
    rendered = app._format_history_response(
        ResponseType.QUIZ,
        {
            "correct": True,
            "quiz": {"question": "23 x 15"},
            "question": "23 x 15",
            "answer": 345,
            "streak": 1,
        },
    )
    assert "Correct, 23 x 15 = 345!" in rendered


def test_textual_history_formats_achievement_with_name():
    """Achievement history entries should show readable unlocked names."""
    app = KidShellTextualApp()
    rendered = app._format_history_response(
        ResponseType.ACHIEVEMENT,
        {"achievements": ["first_five"], "total_solved": 5},
    )
    assert "Achievement unlocked: First Steps" in rendered
    assert "Total solved: 5" in rendered


def test_textual_app_celebration_tier_selection():
    """Achievement payloads should map to progressively bigger celebration tiers."""
    app = KidShellTextualApp()

    tier_one = app._celebration_tier_for_payload({"achievements": ["first_five"], "total_solved": 5})
    tier_two = app._celebration_tier_for_payload({"achievements": ["first_ten"], "total_solved": 10})
    tier_three = app._celebration_tier_for_payload({"achievements": ["math_master"], "total_solved": 25})

    assert tier_one == 1
    assert tier_two == 2
    assert tier_three == 3


def test_textual_app_progress_boost_advances_lane_position():
    """Progress lane should animate forward while a temporary boost is active."""
    app = KidShellTextualApp()
    app.engine.session.problems_solved = 12
    base_lane = app._render_achievement_progress(12).splitlines()[1]

    app._progress_boost_ticks_remaining = 3
    app._progress_boost_velocity = 2
    assert app._advance_progress_boost() is True
    boosted_lane = app._render_achievement_progress(12).splitlines()[1]

    assert boosted_lane != base_lane


def test_textual_app_fireworks_burst_is_transient_history_line():
    """Fireworks burst should appear in history and be removable."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            history = app.query_one("#history", TextArea)

            app._start_fireworks_burst(2, duration_seconds=0)
            await pilot.pause()
            fireworks_line = app._fireworks_line_for_tier(2)
            assert fireworks_line in history.text

            app._clear_fireworks_burst()
            await pilot.pause()
            assert fireworks_line not in history.text

    asyncio.run(_run())


def test_textual_app_starts_celebration_for_achievement_response(monkeypatch):
    """Achievement responses should trigger celebration animation hook."""

    async def _run() -> None:
        app = KidShellTextualApp()
        celebration_payloads: list[dict] = []
        fake_input = SimpleNamespace(value="7")

        async with app.run_test() as pilot:
            monkeypatch.setattr(
                app.engine,
                "process_input",
                lambda _text: Response(
                    type=ResponseType.ACHIEVEMENT,
                    content={"achievements": ["first_five"], "total_solved": 5},
                ),
            )
            monkeypatch.setattr(app.engine, "get_pending_response", lambda: None)
            monkeypatch.setattr(
                app,
                "_start_achievement_celebration",
                lambda payload: celebration_payloads.append(payload),
            )
            monkeypatch.setattr("kidshell.frontends.textual_app.app.save_persisted_session", lambda _session: True)

            await app.handle_input(SimpleNamespace(value="7", input=fake_input))  # type: ignore[arg-type]
            await pilot.pause()

        assert celebration_payloads
        assert celebration_payloads[0]["achievements"] == ["first_five"]

    asyncio.run(_run())


def test_textual_app_color_input_updates_theme_palette():
    """Typing a recognized color should retheme the TUI palette."""

    async def _run() -> None:
        app = KidShellTextualApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            stats_panel = app.query_one(".stats-strip", Horizontal)
            history_container = app.query_one(".history-container", Vertical)
            initial_border_color = stats_panel.styles.border.top[1]
            initial_history_background = history_container.styles.background

            await pilot.press("o", "r", "a", "n", "g", "e", "enter")
            await pilot.pause()

            updated_border_color = stats_panel.styles.border.top[1]
            updated_history_background = history_container.styles.background
            history = app.query_one("#history", TextArea)
            session_time = app.query_one("#session-time", Label)

            assert updated_border_color != initial_border_color
            assert updated_history_background != initial_history_background
            assert "Theme shifted to match your color." in history.text
            assert session_time.styles.background.is_transparent

    asyncio.run(_run())
