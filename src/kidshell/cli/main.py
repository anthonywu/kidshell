"""KidShell CLI entrypoint backed by the unified core engine."""

from __future__ import annotations

import argparse
import atexit
import functools
import json
import logging
import os
import pathlib
import random
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import rich.console as rich_console
import rich.text as rich_text

from kidshell.cli.rich_ui import KidShellRichUI, create_rich_ui
from kidshell.core import KidShellEngine, Response, ResponseType, Session
from kidshell.core.config import get_app_home_dir, get_config_manager
from kidshell.core.i18n import set_language, t, t_list
from kidshell.core.models.achievements import get_achievement
from kidshell.core.profile import (
    ChildProfile,
    calculate_age,
    load_profile,
    next_birthday_details,
    onboarding_intro_lines,
    parse_birth_value,
    parse_month_day_value,
    sanitize_name,
    save_profile,
)
from kidshell.core.session_store import load_persisted_session, save_persisted_session
from kidshell.core.services import DataService

try:
    import readline
except ImportError:  # pragma: no cover - platform dependent
    readline = None  # type: ignore[assignment]

DEFAULT_CONSOLE = rich_console.Console(emoji=True, highlight=True, markup=True)
print = functools.partial(DEFAULT_CONSOLE.print, end="\n\n")  # noqa: A001
RICH_UI = create_rich_ui()

logger = logging.getLogger(__name__)
DEBUG = "DEBUG" in os.environ
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

RNG = random.SystemRandom()
FAILURE_EMOJIS = ["🙈", "🤦", "😑", "😕", "🙅‍♂️"]
MOTION_EMOJIS = ["🚣", "🛫", "🚋"]


class CliResponseRenderer:
    """Render core engine responses in the legacy/simple REPL view."""

    def __init__(self, ui: KidShellRichUI):
        self.ui = ui
        self.today_motion_emoji = RNG.choice(MOTION_EMOJIS)

    def _praise_phrase(self) -> str:
        options = t_list("great_options")
        if not options:
            options = ["Great", "Awesome", "Amazing", "Wonderful"]
        return RNG.choice(options)

    def _show_quiz_prompt(self, question: Any) -> None:
        """Show quiz question with visible highlight in classic REPL."""
        question_text = str(question).strip()
        if not question_text:
            return
        print(f"[bold yellow]{question_text} = ?[/bold yellow]")

    def display_response(self, response) -> None:  # noqa: C901
        """Display a response from the core engine."""
        if response.type == ResponseType.MATH_RESULT:
            content = response.content
            if content.get("result") is not None:
                if "display" in content:
                    print(f"🙌 {content['display']}")
                else:
                    self.ui.show_math_result(content["expression"], content["result"])
                if content.get("note"):
                    print(f"💡 {content['note']}")

        elif response.type == ResponseType.TREE_DISPLAY:
            content = response.content
            self.ui.show_number_tree(content["number"])

        elif response.type == ResponseType.QUIZ:
            content = response.content
            if isinstance(content, dict) and content.get("correct"):
                print(f"👏 {self._praise_phrase()}！")
                if content.get("streak", 0) > 1:
                    print(f"Streak: {content['streak']} in a row! 🔥")
                if "next_quiz" in content:
                    self._show_quiz_prompt(content["next_quiz"].get("question", ""))
            elif isinstance(content, dict) and content.get("correct") is False:
                if content.get("encouragement"):
                    print(f"🌟 {content['encouragement']}")
                if content.get("hint"):
                    print(f"💡 {content['hint']}")
                number_facts = content.get("number_facts")
                if isinstance(number_facts, dict) and isinstance(number_facts.get("number"), int):
                    print(f"🔎 Let's explore {number_facts['number']}:")
                    self.ui.show_number_tree(number_facts["number"])
                if "quiz" in content and isinstance(content["quiz"], dict):
                    self._show_quiz_prompt(content["quiz"].get("question", ""))
            elif isinstance(content, dict):
                self._show_quiz_prompt(content.get("question", str(content)))
            else:
                self._show_quiz_prompt(content)

        elif response.type == ResponseType.ACHIEVEMENT:
            content = response.content
            for achievement_id in content.get("achievements", []):
                achievement = get_achievement(achievement_id)
                if achievement:
                    self.ui.show_achievement(
                        achievement.name,
                        achievement.description,
                        achievement.stars,
                    )
            print(f"{'_' * content.get('total_solved', 0)}{self.today_motion_emoji}")

        elif response.type == ResponseType.SYMBOL_RESULT:
            content = response.content
            action = content.get("action")
            if action == "created":
                print(f"{t('add_symbol')} {content.get('symbol')}")
            elif action == "found":
                print(f"{t('found_symbol')} {content.get('value')}")
            elif action == "assigned":
                print(f"Set {content.get('symbol')} = {content.get('value')}")
            elif "display" in content:
                print(f"🙌 {content['display']}")
            else:
                print(f"🙌 {content.get('result', content)}")

        elif response.type == ResponseType.EMOJI:
            content = response.content
            if content.get("found"):
                if content.get("multiple"):
                    print(f"{content['word']} = {' '.join(content['emojis'])}")
                else:
                    print(f"{content['word']} = {content['emoji']}")
            else:
                print(f"No emoji for '{content.get('word', '')}'")

        elif response.type == ResponseType.COLOR:
            content = response.content
            output = rich_text.Text()
            output.append("Color: ", style="bold white")
            output.append(content["name"], style=f"bold {content['color']}")
            DEFAULT_CONSOLE.print(output)
            if content.get("emojis"):
                print(f"Related: {' '.join(content['emojis'])}")

        elif response.type == ResponseType.LOOP_RESULT:
            content = response.content
            self.ui.status_message(
                f"Counting from {content['start']} to {content['end']}",
                duration=0.3,
            )
            numbers = content["numbers"]
            if len(numbers) <= 20:
                display = ", ".join(map(str, numbers))
            else:
                display = ", ".join(map(str, numbers[:10])) + "..." + ", ".join(map(str, numbers[-5:]))
            self.ui.show_answer_panel(display, "Counting Complete")
            print(f"👌 {t('ok')}")

        elif response.type == ResponseType.ERROR:
            print(f"🙈 {response.content}")

        elif response.type == ResponseType.TEXT or response.content:
            print(f"🙌 {response.content}")


def enable_readline_history() -> None:
    """Enable readline editing/history so arrow keys recall previous commands."""
    if readline is None or not sys.stdin.isatty():
        return

    history_file = get_app_home_dir() / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind("tab: complete")

        if history_file.exists():
            readline.read_history_file(history_file)

        def _write_history() -> None:
            try:
                if readline is not None:
                    readline.write_history_file(history_file)
            except Exception:
                pass

        atexit.register(_write_history)
    except Exception:
        pass


def load_custom_data(data_dir: str = "./data") -> dict[str, Any]:
    """Load custom data from ~/.kidshell/data and legacy ./data."""
    combined_data = DataService.load_data_files()

    legacy_path = pathlib.Path(data_dir)
    if legacy_path.exists() and legacy_path.is_dir():
        for pattern in ("*.json", "*.data"):
            for data_file in legacy_path.glob(pattern):
                try:
                    with data_file.open(encoding="utf-8") as data_io:
                        data_part = json.load(data_io)
                        if isinstance(data_part, dict):
                            combined_data.update(data_part)
                except (OSError, ValueError):
                    logger.warning("Data in %s is not valid JSON.", data_file)

    return dict(combined_data)


def get_profile_path() -> Path:
    """Return persisted child profile path under ~/.kidshell/config."""
    return get_config_manager().profile_file


def load_child_profile(today: date | None = None) -> ChildProfile | None:
    """Load persisted profile if present and valid."""
    return load_profile(get_profile_path(), today=today)


def run_onboarding(
    input_func=input,
    output_func=print,
    today: date | None = None,
) -> ChildProfile | None:
    """Collect first-run profile data interactively and persist it."""
    today_value = today or date.today()
    profile_path = get_profile_path()
    existing_profile = load_profile(profile_path, today=today_value)
    if existing_profile is not None:
        return existing_profile

    for line in onboarding_intro_lines():
        output_func(line)

    while True:
        raw_name = input_func("What is your name? ").strip()
        name = sanitize_name(raw_name)
        if name:
            break
        output_func("Please enter a short name using letters, numbers, spaces, or .'-")

    while True:
        raw_birth = input_func("Birth year (YYYY) or full birthday (YYYY-MM-DD): ").strip()
        try:
            birth_year, full_birthday = parse_birth_value(raw_birth, today=today_value)
            break
        except ValueError as exc:
            output_func(str(exc))

    birthday_iso = full_birthday.isoformat() if full_birthday else None
    if birthday_iso is None:
        month_day = input_func("Optional month/day for birthday countdown (MM-DD), or press Enter to skip: ").strip()
        while month_day:
            try:
                birthday_iso = parse_month_day_value(month_day, birth_year, today=today_value).isoformat()
                break
            except ValueError as exc:
                output_func(str(exc))
                month_day = input_func(
                    "Optional month/day for birthday countdown (MM-DD), or press Enter to skip: "
                ).strip()

    profile = ChildProfile(name=name, birth_year=birth_year, birthday=birthday_iso)
    try:
        save_profile(profile_path, profile)
    except OSError:
        output_func("Couldn't save your profile yet, but we can still keep going.")
    return profile


def ensure_child_profile(
    input_func=input,
    output_func=print,
    today: date | None = None,
    is_tty: bool | None = None,
) -> ChildProfile | None:
    """Load profile or run first-time onboarding when interactive."""
    today_value = today or date.today()
    existing_profile = load_child_profile(today=today_value)
    if existing_profile is not None:
        return existing_profile

    interactive_tty = sys.stdin.isatty() if is_tty is None else is_tty
    if not interactive_tty:
        return None
    return run_onboarding(input_func=input_func, output_func=output_func, today=today_value)


def display_age(
    profile: ChildProfile | None = None,
    custom_data: dict[str, Any] | None = None,
    today: date | None = None,
) -> None:
    """Display age and birthday countdown when available."""
    today_value = today or date.today()

    if profile is not None:
        output_name = sanitize_name(profile.name) or "friend"
        age = calculate_age(profile, today=today_value)
        print(f"Hi {output_name}! You are {age} years old.")
        next_birthday = next_birthday_details(profile, today=today_value)
        if next_birthday is not None:
            days_until_bday, next_age = next_birthday
            if days_until_bday == 0:
                print(f"Happy birthday, {output_name}! You are now {next_age}.")
            else:
                print(f"Your next birthday is in {days_until_bday} days. You will turn {next_age}.")
        return

    data = custom_data or {}
    try:
        bday_parts = [int(x) for x in str(data["bday"]).split(".")]
        legacy_profile = ChildProfile(
            name="friend",
            birth_year=bday_parts[0],
            birthday=date(*bday_parts).isoformat(),
        )
        age = calculate_age(legacy_profile, today=today_value)
        print(t("birthday_msg", year=bday_parts[0], month=bday_parts[1], day=bday_parts[2]))
        print(t("age_msg", age=age))
        next_birthday = next_birthday_details(legacy_profile, today=today_value)
        if next_birthday is not None:
            days_until_bday, next_age = next_birthday
            print(t("next_birthday", age=next_age, days=days_until_bday))
    except (KeyError, ValueError, TypeError):
        pass


def display_welcome(
    profile: ChildProfile | None = None,
    custom_data: dict[str, Any] | None = None,
    today: date | None = None,
) -> None:
    """Display date + personalized greeting."""
    today_value = today or date.today()
    date_format = t("date_format")
    print(f"{t('today_is')} {today_value.strftime(date_format)}")
    print()
    display_age(profile=profile, custom_data=custom_data, today=today_value)


def normalize_user_input(user_input: str) -> str:
    """Normalize user input and strip pasted prompt markers like '> 1 + 1'."""
    normalized = user_input.lower().strip()
    while normalized.startswith(">"):
        normalized = normalized[1:].strip()
    return normalized


def apply_history_escape_fallback(user_input: str, last_user_input: str) -> str | None:
    """Handle pasted/raw ANSI arrow-key sequences when readline is unavailable."""
    if re.fullmatch(r"(?:\x1b|\^\[)\[[A-D]", user_input):
        if user_input.endswith("A") and last_user_input:
            return last_user_input
        return None
    return user_input


def prompt_loop(prompt_text: str = "> ", *, start_new: bool = False) -> None:
    """Run the engine-backed simple REPL interface."""
    try:
        profile = ensure_child_profile()
    except (EOFError, KeyboardInterrupt):
        print(f"👋 {t('bye')}")
        sys.exit(0)

    custom_data = load_custom_data()
    if not custom_data:
        config_manager = get_config_manager()
        print("💡 Tip: Use 'kidshell config' to edit custom data files")
        print(f"   Data location: {config_manager.data_dir}")

    session = Session()
    if not start_new:
        restored_session = load_persisted_session()
        if restored_session is not None:
            session = restored_session

    session.custom_data = dict(custom_data)

    display_welcome(profile=profile, custom_data=custom_data)
    enable_readline_history()

    engine = KidShellEngine(session)
    renderer = CliResponseRenderer(RICH_UI)
    last_user_input = ""

    # Make quiz mode explicit as soon as REPL starts.
    active_session = getattr(engine, "session", None)
    current_quiz = getattr(active_session, "current_quiz", None)
    if current_quiz:
        renderer.display_response(Response(type=ResponseType.QUIZ, content=current_quiz))
        save_persisted_session(getattr(engine, "session", session))
    elif active_session is not None:
        initial_response = engine.process_input("")
        renderer.display_response(initial_response)
        pending = engine.get_pending_response()
        while pending is not None:
            renderer.display_response(pending)
            pending = engine.get_pending_response()
        save_persisted_session(getattr(engine, "session", session))

    while True:
        try:
            user_input = input(prompt_text)
        except (EOFError, KeyboardInterrupt):
            save_persisted_session(getattr(engine, "session", session))
            print(f"👋 {t('bye')}")
            sys.exit(0)

        fallback_user_input = apply_history_escape_fallback(user_input, last_user_input)
        if fallback_user_input is None:
            continue

        user_input = fallback_user_input
        normalized_input = normalize_user_input(user_input)
        if normalized_input:
            last_user_input = user_input

        if normalized_input in {"bye", "quit"}:
            save_persisted_session(getattr(engine, "session", session))
            print(f"👋 {t('bye')}")
            sys.exit(0)

        try:
            response = engine.process_input(normalized_input)
            renderer.display_response(response)

            pending = engine.get_pending_response()
            while pending is not None:
                renderer.display_response(pending)
                pending = engine.get_pending_response()

            save_persisted_session(getattr(engine, "session", session))

        except Exception:
            if DEBUG:
                raise
            print(f"{RNG.choice(FAILURE_EMOJIS)} ???")


def main() -> None:
    """Main entry point for kidshell CLI."""
    parser = argparse.ArgumentParser(description="KidShell - A child-friendly REPL")
    parser.add_argument("--language", default="en", help="Language code (e.g., en, zh_CN)")
    parser.add_argument("--new", action="store_true", help="Start a fresh session without restoring previous state")
    parser.add_argument("command", nargs="?", help="Command to run (e.g., config, tui, classic)")
    parser.add_argument("args", nargs="*", help="Command arguments")

    args, unknown = parser.parse_known_args()

    set_language(args.language)

    if args.command == "config":
        from kidshell.cli.config_command import config_command

        config_command(args.args + unknown)
        return

    if args.command in {None, "tui", "web"}:
        from kidshell.frontends.textual_app.app import main as textual_main

        textual_main(start_new=args.new)
        return

    if args.command in {"classic", "repl"}:
        prompt_loop(start_new=args.new)
        return

    parser.error(f"Unknown command '{args.command}'. Use one of: config, tui, classic")


if __name__ == "__main__":
    main()
