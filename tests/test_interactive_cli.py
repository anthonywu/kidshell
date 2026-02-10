"""Interactive CLI behavior tests for onboarding and engine-backed prompt loop."""

from __future__ import annotations

import importlib
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from kidshell.core.profile import ChildProfile, load_profile
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


def _input_feeder(values: list[Any]):
    iterator = iter(values)

    def _fake_input(_prompt: str = "") -> str:
        value = next(iterator)
        if isinstance(value, BaseException):
            raise value
        return str(value)

    return _fake_input


@pytest.fixture
def cli_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Load kidshell.cli.main with isolated ~/.kidshell storage."""
    monkeypatch.setenv("KIDSHELL_HOME", str(tmp_path / ".kidshell"))
    import kidshell.core.config as config_module
    import kidshell.cli.main as main_module

    config_module._config_manager = None
    main = importlib.reload(main_module)
    yield main
    config_module._config_manager = None


def test_run_onboarding_saves_full_birthday(cli_main, tmp_path: Path):
    """Onboarding should persist full birthday when provided."""
    profile_path = tmp_path / ".kidshell" / "config" / "profile.json"
    outputs: list[str] = []
    profile = cli_main.run_onboarding(
        input_func=_input_feeder(["Avery", "2015-03-01"]),
        output_func=outputs.append,
        today=date(2026, 2, 7),
    )

    loaded = load_profile(profile_path)
    assert profile is not None
    assert profile.name == "Avery"
    assert profile.birth_year == 2015
    assert profile.birthday == "2015-03-01"
    assert loaded is not None
    assert loaded.birthday == "2015-03-01"
    assert any("Welcome to KidShell!" in line for line in outputs)


def test_run_onboarding_year_then_optional_month_day(cli_main, tmp_path: Path):
    """Onboarding should support birth year first, then optional month/day."""
    profile_path = tmp_path / ".kidshell" / "config" / "profile.json"
    outputs: list[str] = []
    profile = cli_main.run_onboarding(
        input_func=_input_feeder(["Kai", "2014", "13-99", "03-05"]),
        output_func=outputs.append,
        today=date(2026, 2, 7),
    )

    loaded = load_profile(profile_path)
    assert profile is not None
    assert profile.birth_year == 2014
    assert profile.birthday == "2014-03-05"
    assert loaded is not None
    assert loaded.birthday == "2014-03-05"
    assert any("real calendar date" in line for line in outputs)


def test_ensure_child_profile_skips_onboarding_when_non_interactive(cli_main):
    """Non-interactive runs should not block waiting for onboarding input."""
    profile = cli_main.ensure_child_profile(
        input_func=_input_feeder(["Should not be read"]),
        output_func=lambda _line: None,
        today=date(2026, 2, 7),
        is_tty=False,
    )
    assert profile is None


def test_display_welcome_uses_profile_name_age_and_countdown(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Welcome should greet by name, show age, and show birthday countdown."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    profile = ChildProfile(name="Sam", birth_year=2012, birthday="2012-12-31")
    cli_main.display_welcome(profile=profile, custom_data={}, today=date(2026, 2, 7))

    assert any("Hi Sam! You are 13 years old." in line for line in rendered)
    assert any("Your next birthday is in" in line for line in rendered)


def test_apply_history_escape_fallback_replays_last_input(cli_main):
    """Raw up-arrow escape input should replay previous command."""
    assert cli_main.apply_history_escape_fallback("^[[A", "1 + 1") == "1 + 1"


def test_apply_history_escape_fallback_ignores_without_previous(cli_main):
    """Raw arrow input without history should be ignored."""
    assert cli_main.apply_history_escape_fallback("^[[A", "") is None
    assert cli_main.apply_history_escape_fallback("^[[B", "2 + 2") is None


def test_prompt_loop_reuses_last_command_for_raw_up_arrow(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Prompt loop should treat raw up-arrow as command recall."""
    observed_inputs: list[str] = []

    class FakeEngine:
        def __init__(self, _session):
            pass

        def process_input(self, input_text: str):
            observed_inputs.append(input_text)
            return Response(type=ResponseType.TEXT, content="ok")

        def get_pending_response(self):
            return None

    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {})
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "builtins.input",
        _input_feeder(["1 + 1", "^[[A", KeyboardInterrupt()]),
    )

    with pytest.raises(SystemExit):
        cli_main.prompt_loop()

    assert observed_inputs == ["1 + 1", "1 + 1"]


def test_prompt_loop_strips_pasted_prompt_markers(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Prompt loop should normalize pasted prompt text like '> 1 + 1'."""
    observed_inputs: list[str] = []

    class FakeEngine:
        def __init__(self, _session):
            pass

        def process_input(self, input_text: str):
            observed_inputs.append(input_text)
            return Response(type=ResponseType.TEXT, content="ok")

        def get_pending_response(self):
            return None

    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {})
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "builtins.input",
        _input_feeder(["> 1 + 1", KeyboardInterrupt()]),
    )

    with pytest.raises(SystemExit):
        cli_main.prompt_loop()

    assert observed_inputs == ["1 + 1"]


def test_prompt_loop_loads_custom_data_into_session(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Prompt loop should pass loaded custom data into engine session."""
    captured_custom_data: dict[str, Any] = {}

    class FakeEngine:
        def __init__(self, session):
            captured_custom_data.update(session.custom_data)

        def process_input(self, input_text: str):
            return Response(type=ResponseType.TEXT, content=input_text)

        def get_pending_response(self):
            return None

    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {"hello": "world"})
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr("builtins.input", _input_feeder([KeyboardInterrupt()]))

    with pytest.raises(SystemExit):
        cli_main.prompt_loop()

    assert captured_custom_data == {"hello": "world"}


def test_prompt_loop_handles_onboarding_interrupt_gracefully(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Interrupt during onboarding should exit cleanly without traceback."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    with pytest.raises(SystemExit) as exit_info:
        cli_main.prompt_loop()

    assert exit_info.value.code == 0
    assert any("Bye Bye!" in line for line in rendered)


def test_prompt_loop_restores_previous_session_by_default(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Default prompt loop should restore persisted session state."""
    restored = Session()
    restored.problems_solved = 7
    restored.current_streak = 3

    captured: dict[str, int] = {}
    save_calls: list[int] = []

    class FakeEngine:
        def __init__(self, session):
            captured["problems_solved"] = session.problems_solved
            captured["current_streak"] = session.current_streak
            self.session = session

        def process_input(self, input_text: str):
            return Response(type=ResponseType.TEXT, content=input_text)

        def get_pending_response(self):
            return None

    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {})
    monkeypatch.setattr(cli_main, "load_persisted_session", lambda: restored)
    monkeypatch.setattr(cli_main, "save_persisted_session", lambda session: save_calls.append(session.problems_solved) or True)
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr("builtins.input", _input_feeder([KeyboardInterrupt()]))

    with pytest.raises(SystemExit):
        cli_main.prompt_loop()

    assert captured == {"problems_solved": 7, "current_streak": 3}
    assert save_calls


def test_prompt_loop_with_new_flag_skips_restore(cli_main, monkeypatch: pytest.MonkeyPatch):
    """--new should bypass persisted session restore and start fresh."""
    load_called = {"value": False}
    captured: dict[str, int] = {}

    class FakeEngine:
        def __init__(self, session):
            captured["problems_solved"] = session.problems_solved
            captured["current_streak"] = session.current_streak
            self.session = session

        def process_input(self, input_text: str):
            return Response(type=ResponseType.TEXT, content=input_text)

        def get_pending_response(self):
            return None

    def _load():
        load_called["value"] = True
        restored = Session()
        restored.problems_solved = 9
        return restored

    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {})
    monkeypatch.setattr(cli_main, "load_persisted_session", _load)
    monkeypatch.setattr(cli_main, "save_persisted_session", lambda session: True)
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr("builtins.input", _input_feeder([KeyboardInterrupt()]))

    with pytest.raises(SystemExit):
        cli_main.prompt_loop(start_new=True)

    assert load_called["value"] is False
    assert captured == {"problems_solved": 0, "current_streak": 0}


@pytest.mark.parametrize("exit_word", ["bye", "quit", "exit", "close", ":q!"])
def test_prompt_loop_reserved_exit_words_terminate_session(cli_main, monkeypatch: pytest.MonkeyPatch, exit_word: str):
    """Typing reserved exit words should end the classic REPL immediately."""
    processed_inputs: list[str] = []

    class FakeEngine:
        def __init__(self, _session):
            pass

        def process_input(self, input_text: str):
            processed_inputs.append(input_text)
            return Response(type=ResponseType.TEXT, content="unexpected")

        def get_pending_response(self):
            return None

    saves: list[bool] = []
    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {})
    monkeypatch.setattr(cli_main, "save_persisted_session", lambda session: saves.append(True) or True)
    monkeypatch.setattr("builtins.input", _input_feeder([exit_word]))
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exit_info:
        cli_main.prompt_loop()

    assert exit_info.value.code == 0
    assert processed_inputs == []
    assert saves


def test_renderer_highlights_next_quiz_prompt_in_color(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Quiz prompts should retain visible color emphasis in classic REPL."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    renderer = cli_main.CliResponseRenderer(cli_main.RICH_UI)
    renderer.display_response(
        Response(
            type=ResponseType.QUIZ,
            content={"correct": True, "next_quiz": {"question": "7 - 5"}},
        )
    )

    assert any("[bold yellow]7 - 5 = ?[/bold yellow]" in line for line in rendered)


def test_renderer_repeats_solved_quiz_equation_on_correct(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Correct quiz feedback should restate solved equation in classic REPL."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    renderer = cli_main.CliResponseRenderer(cli_main.RICH_UI)
    renderer.display_response(
        Response(
            type=ResponseType.QUIZ,
            content={
                "correct": True,
                "quiz": {"question": "23 x 15"},
                "question": "23 x 15",
                "answer": 345,
            },
        )
    )

    assert any("Correct, 23 x 15 = 345!" in line for line in rendered)


def test_prompt_loop_shows_initial_quiz_on_startup(cli_main, monkeypatch: pytest.MonkeyPatch):
    """REPL should display the first quiz immediately so quiz mode is obvious."""
    rendered: list[str] = []
    observed_inputs: list[str] = []

    class FakeEngine:
        def __init__(self, session):
            self.session = session

        def process_input(self, input_text: str):
            observed_inputs.append(input_text)
            if input_text == "":
                quiz = {"id": "q1", "question": "2 + 3", "answer": 5}
                self.session.current_quiz = quiz
                return Response(type=ResponseType.QUIZ, content=quiz)
            return Response(type=ResponseType.TEXT, content="ok")

        def get_pending_response(self):
            return None

    monkeypatch.setattr(cli_main, "KidShellEngine", FakeEngine)
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None, custom_data=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "load_custom_data", lambda: {})
    monkeypatch.setattr(cli_main, "load_persisted_session", lambda: None)
    monkeypatch.setattr(cli_main, "save_persisted_session", lambda session: True)
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))
    monkeypatch.setattr("builtins.input", _input_feeder([KeyboardInterrupt()]))

    with pytest.raises(SystemExit):
        cli_main.prompt_loop()

    assert observed_inputs == [""]
    assert any("[bold yellow]2 + 3 = ?[/bold yellow]" in line for line in rendered)


def test_renderer_shows_math_alias_interpretation_note(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Classic renderer should print math alias clarification notes."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    renderer = cli_main.CliResponseRenderer(cli_main.RICH_UI)
    renderer.display_response(
        Response(
            type=ResponseType.MATH_RESULT,
            content={
                "expression": "8 * 6",
                "result": 48,
                "display": "8 * 6 = 48",
                "note": "Interpreted 'x' as multiplication here.",
            },
        )
    )

    assert any("8 * 6 = 48" in line for line in rendered)
    assert any("Interpreted 'x' as multiplication" in line for line in rendered)


def test_renderer_shows_two_digit_multiplication_breakdown_hint(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Classic renderer should show distributive breakdown hint for two-digit multiplication."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    renderer = cli_main.CliResponseRenderer(cli_main.RICH_UI)
    renderer.display_response(
        Response(
            type=ResponseType.MATH_RESULT,
            content={
                "expression": "12 * 25",
                "result": 300,
                "display": "12 * 25 = 300",
            },
        )
    )

    assert any("12 * 25 = 300" in line for line in rendered)
    assert any(
        "Try breaking it apart: 12 * 25 = (10 + 2) x (20 + 5) = 200 + 50 + 40 + 10 = 300" in line
        for line in rendered
    )


def test_main_defaults_to_tui_mode(cli_main, monkeypatch: pytest.MonkeyPatch):
    """`kidshell` with no command should launch TUI mode."""
    calls: list[bool] = []
    monkeypatch.setattr("kidshell.frontends.textual_app.app.main", lambda *, start_new=False: calls.append(start_new))
    monkeypatch.setattr(sys, "argv", ["kidshell"])

    cli_main.main()

    assert calls == [False]


def test_main_classic_command_launches_repl(cli_main, monkeypatch: pytest.MonkeyPatch):
    """`kidshell classic` should launch the legacy/basic REPL."""
    calls: list[bool] = []
    monkeypatch.setattr(cli_main, "prompt_loop", lambda *args, **kwargs: calls.append(kwargs.get("start_new", False)))
    monkeypatch.setattr(sys, "argv", ["kidshell", "--new", "classic"])

    cli_main.main()

    assert calls == [True]
