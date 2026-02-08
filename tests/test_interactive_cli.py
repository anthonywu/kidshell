"""Interactive CLI behavior tests for onboarding and input handling."""

from __future__ import annotations

import importlib
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from kidshell.core.profile import ChildProfile, load_profile


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

    # Reset singleton so config paths honor KIDSHELL_HOME for each test.
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
    cli_main.display_welcome(profile=profile, today=date(2026, 2, 7))

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

    def _capture(text: str) -> str:
        observed_inputs.append(text)
        return "ok"

    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cli_main,
        "HANDLERS",
        [("capture", lambda _text: True, _capture)],
    )
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

    def _capture(text: str) -> str:
        observed_inputs.append(text)
        return "ok"

    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: None)
    monkeypatch.setattr(cli_main, "display_welcome", lambda profile=None: None)
    monkeypatch.setattr(cli_main, "enable_readline_history", lambda: None)
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cli_main,
        "HANDLERS",
        [("capture", lambda _text: True, _capture)],
    )
    monkeypatch.setattr(
        "builtins.input",
        _input_feeder(["> 1 + 1", KeyboardInterrupt()]),
    )

    with pytest.raises(SystemExit):
        cli_main.prompt_loop()

    assert observed_inputs == ["1 + 1"]


def test_prompt_loop_handles_onboarding_interrupt_gracefully(cli_main, monkeypatch: pytest.MonkeyPatch):
    """Interrupt during onboarding should exit cleanly without traceback."""
    rendered: list[str] = []
    monkeypatch.setattr(cli_main, "ensure_child_profile", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(cli_main, "print", lambda *args, **kwargs: rendered.append(str(args[0]) if args else ""))

    with pytest.raises(SystemExit) as exit_info:
        cli_main.prompt_loop()

    assert exit_info.value.code == 0
    assert any("Bye Bye!" in line for line in rendered)
