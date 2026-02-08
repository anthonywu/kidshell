import argparse
import atexit
import copy
import functools
import json
import logging
import math
import os
import pathlib
import random
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import rich.color as rich_color
import rich.console as rich_console
import rich.emoji as rich_emoji
import rich.text as rich_text

from sympy import symbols

# Import our new Rich UI module
from kidshell.cli.rich_ui import create_rich_ui
from kidshell.core.config import get_app_home_dir
from kidshell.core.i18n import set_language, t, t_list
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

try:
    import readline
except ImportError:  # pragma: no cover - platform dependent (e.g., minimal Windows builds)
    readline = None  # type: ignore[assignment]

DEFAULT_CONSOLE = rich_console.Console(emoji=True, highlight=True, markup=True)
print = functools.partial(
    DEFAULT_CONSOLE.print,
    end="\n\n",
)

# Initialize Rich UI
RICH_UI = create_rich_ui()

# Set up logging
logger = logging.getLogger(__name__)
DEBUG = "DEBUG" in os.environ
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

# Use SystemRandom so security scans don't treat quiz randomness as weak PRNG usage.
RNG = random.SystemRandom()

SUCCESS_EMOJIS = ["😀", "🙌", "👍", "😇"]
FAILURE_EMOJIS = ["🙈", "🤦", "😑", "😕", "🙅‍♂️"]

MOTION_EMOJIS = ["🚣", "🛫", "🚋"]
TODAY_MOTION_EMOJI = RNG.choice(MOTION_EMOJIS)


class TryNext(ValueError):
    pass


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
                # History persistence must never break the interactive shell.
                pass

        atexit.register(_write_history)
    except Exception:
        # Readline availability is best-effort; fall back to plain input safely.
        pass


def show_rich_emoji(text):
    try:
        emoji_match = rich_emoji.Emoji(text)
        return f"{text} = {emoji_match}"
    except rich_emoji.NoEmoji:
        raise TryNext(f"{text}: not emoji")


def show_rich_emoji_match(text):
    emoji_map = getattr(rich_emoji, "EMOJI", {})
    matches = [
        v
        for (k, v) in emoji_map.items()
        if all(
            (
                text in k.split("_"),
                "skin_tone" not in k,
            )
        )
    ]
    if matches:
        return " ".join(matches)
    raise TryNext(f"{text}: not emoji")


def summarize_gibberish(text):
    uniq_letters = set(text)
    output = ""
    for letter in sorted(uniq_letters):
        if letter.isalpha():
            output += f"{letter}: {text.count(letter)}, "
    return output


def handle_color_name(text):
    match_found = False
    output = rich_text.Text()
    match_text = text.replace(" ", "_")
    for color_name_var in [match_text, f"{match_text}1"]:
        try:
            rich_color.Color.parse(color_name_var)
            match_found = True
            output.append("Color: ", style="bold white")
            output.append(text, style=f"bold {color_name_var}")
            break
        except rich_color.ColorParseError:
            continue

    try:
        print(show_rich_emoji_match(text))
    except TryNext:
        pass

    if not match_found:
        raise TryNext(f"not a color name: {text}")

    return output


def read_data_files(data_dir="./data"):
    """Legacy function for backward compatibility."""
    from kidshell.core.config import get_config_manager

    config_manager = get_config_manager()

    # First try the ~/.kidshell/data location
    combined_data = config_manager.load_data_files()

    # Also check the legacy ./data directory if it exists
    legacy_path = pathlib.Path(data_dir)
    if legacy_path.exists() and legacy_path.is_dir():
        # Support both .json and legacy .data files
        for pattern in ["*.json", "*.data"]:
            for data_file in legacy_path.glob(pattern):
                with open(data_file, "rb") as data_io:
                    try:
                        data_part = json.load(data_io)
                        combined_data.update(data_part)
                        logger.debug(f"Loaded legacy data from {data_file} {data_part.get('title')}")
                    except ValueError:
                        logger.warning(f"Data in {data_file} is not valid JSON.")

    if DEBUG:
        print(json.dumps(dict(combined_data), indent=4))
    return combined_data


try:
    CUSTOM_DATA = read_data_files()
    if not CUSTOM_DATA:
        from kidshell.core.config import get_config_manager

        config_manager = get_config_manager()
        print("💡 Tip: Use 'kidshell config' to edit custom data files")
        print(f"   Data location: {config_manager.data_dir}")
except FileNotFoundError:
    print("You can create files using 'kidshell config' to enable custom responses.")
    CUSTOM_DATA = {}


MATH_ENV = {
    "e": math.e,
    "pi": math.pi,
    "tau": math.tau,
    # Mapping[str, object]
    "last_number": 0,
}


try:
    import scipy.constants

    MATH_ENV.update(
        {
            "c": scipy.constants.c,
            "g": scipy.constants.g,
            "G": scipy.constants.G,
            "h": scipy.constants.h,
            "k": scipy.constants.k,
        }
    )
except ModuleNotFoundError:
    # scipy features are optional
    pass


SYMBOLS_ENV = copy.deepcopy(MATH_ENV)


def handle_math_input(normalized_input: str | int | float) -> Any:
    output: Any = normalized_input

    if isinstance(normalized_input, (int, float)):
        MATH_ENV["last_number"] = normalized_input
    elif isinstance(normalized_input, str) and normalized_input.isdigit():
        MATH_ENV["last_number"] = int(normalized_input)

    # Show thinking spinner for complex calculations
    if isinstance(normalized_input, str) and len(normalized_input) > 10:
        RICH_UI.thinking_spinner("Calculating", 0.5)

    try:
        if not isinstance(normalized_input, str):
            output = normalized_input
        elif "=" in normalized_input:
            # handle assignment safely
            from kidshell.core.safe_math import SafeMathError, SafeMathEvaluator

            parts = normalized_input.split("=", 1)
            if len(parts) != 2:
                raise TryNext("Invalid assignment")

            var_name = parts[0].strip()
            value_expr = parts[1].strip()
            evaluator = SafeMathEvaluator(variables=MATH_ENV)
            try:
                result = evaluator.evaluate(value_expr)
                MATH_ENV[var_name] = result
                output = result
            except SafeMathError:
                raise TryNext("Invalid assignment")
        elif any(normalized_input.startswith(op) for op in "+-*/"):
            inferred_cmd = f"{MATH_ENV['last_number']} {normalized_input}"
            print(inferred_cmd)
            # do the inferred calculation based on inferred last_number
            # Use safe evaluation instead of eval
            from kidshell.core.safe_math import safe_eval

            output = safe_eval(inferred_cmd, MATH_ENV)
        else:
            # do the calculation as entered
            from kidshell.core.safe_math import safe_eval

            output = safe_eval(normalized_input, MATH_ENV)

        if isinstance(output, float) and int(output) == output and output <= sys.maxsize:
            # floor floats of x.0 to just int x
            # so that 5 / 5 acts like 5 // 5
            output = int(output)
    except (NameError, SyntaxError):
        raise TryNext("Invalid math expression")

    if isinstance(output, (int, float)):
        MATH_ENV["last_number"] = output

        # Show result in a panel for calculations
        if isinstance(normalized_input, str) and any(op in normalized_input for op in "+-*/"):
            clean_expr = re.sub(r"\s+", " ", normalized_input.strip())
            # If expression contains variables, show both expression and result
            if any(c.isalpha() for c in clean_expr):
                return f"{clean_expr} = {output}"
            else:
                RICH_UI.show_math_result(clean_expr, output)
                return None  # Don't double-print

    if DEBUG:
        print(f"MATH_ENV={MATH_ENV}")

    return output


MATH_OP_PRETTY_CHAR = {
    "+": "+",
    "-": "−",
    "*": "×",
    "/": "÷",
}


def breakdown_number_to_ten_plus(number):
    return number > 10 and number % 10 > 0


def generate_new_addition_problem(number_max=100):
    x, y = RNG.randint(1, number_max), RNG.randint(1, number_max)
    solution = x + y
    MATH_ENV["problem_expected_solution"] = solution_text = str(solution)
    problem_texts = [f"{x} + {y}"]
    if breakdown_number_to_ten_plus(x) and breakdown_number_to_ten_plus(y):
        problem_texts.append(f"({x - x % 10} + {x % 10} + {y - y % 10} + {y % 10})")
        problem_texts.append(f"({x - x % 10} + {y - y % 10} + {x % 10} + {y % 10})")
        problem_texts.append(f"({x - x % 10} + {y - y % 10} + {x % 10 + y % 10})")
    elif breakdown_number_to_ten_plus(x):
        problem_texts.append(f"({x - x % 10} + {x % 10} + {y})")
    elif breakdown_number_to_ten_plus(y):
        problem_texts.append(f"({x} + {y - y % 10} + {y % 10})")
    return "  ==  ".join(problem_texts) + " == " + ("?" * len(solution_text))


def generate_new_subtraction_problem(number_max=100):
    a, b = RNG.randint(1, number_max), RNG.randint(1, number_max)
    x, y = max(a, b), min(a, b)
    solution = x - y
    MATH_ENV["problem_expected_solution"] = solution_text = str(solution)
    problem_texts = [f"{x} - {y}"]
    x_mod_ten = x % 10
    y_mod_ten = y % 10
    if breakdown_number_to_ten_plus(y):
        problem_texts.append(f"{x} - {y - y_mod_ten} - {y_mod_ten}")
    if x_mod_ten < y_mod_ten and breakdown_number_to_ten_plus(x) and breakdown_number_to_ten_plus(y):
        problem_texts.append(f"{x} - {y - y_mod_ten} - {x_mod_ten} - {y_mod_ten - x_mod_ten}")
    return "  ==  ".join(problem_texts) + " == " + ("?" * len(solution_text))


def find_factors(number: int, min_factor=2) -> list[tuple[int, int]]:
    results = []
    for factor_candidate in range(min_factor, math.floor(math.sqrt(number) + 1)):
        if number % factor_candidate == 0:
            results.append(
                (factor_candidate, number // factor_candidate),
            )
    return results


def format_factors(factors: list[tuple[int, int]]) -> str:
    factor_seq = " = ".join([f"{a} × {b}" for a, b in factors])
    return factor_seq


def get_number_hint(number: int, placeholder="?") -> str:
    return placeholder * len(str(number))


def generate_multiplication_problem(rand_min=1, rand_max=100):
    while True:
        solution = RNG.randint(rand_min, rand_max)
        if factors := find_factors(solution):
            MATH_ENV["problem_expected_solution"] = str(solution)
            return f"{format_factors(factors)} = {get_number_hint(solution)}"


def generate_division_problem():
    x = RNG.randint(1, 10) * 10
    y = x // 10
    solution = x // y
    MATH_ENV["problem_expected_solution"] = str(solution)
    return f"{x} ➗ {y} = {get_number_hint(solution)}"


def generate_new_math_question(normalized_input):
    dice_roll = RNG.randint(1, 4)
    output = generate_new_addition_problem()
    if dice_roll == 1:
        pass
    elif dice_roll == 2:
        output = generate_new_subtraction_problem()
    elif dice_roll == 3:
        output = generate_multiplication_problem()
    elif dice_roll == 4:
        output = generate_division_problem()
    return output


def generate_new_math_question_basic(add_sub_max=20, mul_div_max=10):
    op = RNG.choice(["+", "-"])
    x, y = 0, 0
    if op in ["+", "-"]:
        x, y = RNG.randint(0, add_sub_max), RNG.randint(0, add_sub_max)
        x, y = max(x, y), min(x, y)
    elif op == "*":
        x, y = RNG.randint(1, mul_div_max), RNG.randint(1, mul_div_max)
    MATH_ENV["problem_x"] = x
    MATH_ENV["problem_y"] = y
    MATH_ENV["problem_op"] = op
    # Use safe evaluation
    from kidshell.core.safe_math import safe_math_operation

    solution = safe_math_operation(x, op, y)
    MATH_ENV["problem_expected_solution"] = solution_text = str(solution)
    return f"{x} {MATH_OP_PRETTY_CHAR[op]} {y} = {'?' * len(solution_text)}"


ACHIEVEMENTS = {
    "math_problems_solved": 0,
}


MATH_OPS_PATTERN = re.compile(r"\s+[+\-*/]\s+")
SYMBOL_ASSIGNMENT_SPLITTER = re.compile(r"\s*=\s*")
parse_symbol_parts = functools.partial(re.split, MATH_OPS_PATTERN)


def handle_symbol_assignment(normalized_input):
    try:
        symbol, assign_value = re.split(SYMBOL_ASSIGNMENT_SPLITTER, normalized_input)
        symbol = symbol.strip()
        assign_value = assign_value.strip()

        # Check if it's a valid symbol name
        if symbol.isalpha() and len(symbol) <= 10:
            # Evaluate the right side
            from kidshell.core.safe_math import safe_eval, SafeMathError

            try:
                value = safe_eval(assign_value, SYMBOLS_ENV)
                SYMBOLS_ENV[symbol] = value
                MATH_ENV[symbol] = value  # Also update MATH_ENV
                return f"{symbol} = {value}"
            except SafeMathError as e:
                raise TryNext(f"Invalid assignment: {e}")
    except ValueError:
        raise TryNext(f"{normalized_input} does not look like assignment")


def handle_symbol_lookup(normalized_input):
    if normalized_input in SYMBOLS_ENV:
        sym_input = SYMBOLS_ENV[normalized_input]
        return f"{t('found_symbol')} {sym_input}"
    SYMBOLS_ENV[normalized_input] = sym_input = symbols(normalized_input)
    return f"{t('add_symbol')} {sym_input}"


def handle_symbol_expr(normalized_input):
    # Keep purely numeric arithmetic on the literal-math path so UI rendering is consistent.
    if not any(ch.isalpha() for ch in normalized_input):
        raise TryNext("Use literal math evaluator for numeric-only expressions.")

    # Coerce split parts to plain strings so type-checkers can verify string-only operations.
    expr_parts = [str(part) for part in parse_symbol_parts(normalized_input)]
    for part in expr_parts:
        if not (part.isalnum() or part.isnumeric()):
            raise TryNext("Ops only possible for alphanumeric var names.")
        if part not in SYMBOLS_ENV and not part.isnumeric():
            handle_symbol_lookup(part)
        if DEBUG:
            print(f"Symbols: {SYMBOLS_ENV}")
    try:
        from kidshell.core.safe_math import safe_eval

        return safe_eval(normalized_input, SYMBOLS_ENV)
    except SyntaxError as syn_err:
        raise TryNext(syn_err)


def run_loop(normalized_input, use_tqdm=True):
    parts: list[str] = []
    try:
        parts = [num.strip() for num in normalized_input.split("...")]
        print(parts)
        start, end = int(parts[0]), int(parts[1])
        step = int(parts[2]) if len(parts) > 2 else 1
        print_pause = float(parts[3]) if len(parts) > 3 else 0.5

        # Use status message for counting
        def count_task():
            result = []
            for i in range(start, end + 1, step):
                result.append(i)
                time.sleep(print_pause)
            return result

        numbers = RICH_UI.status_message(
            f"Counting from {start} to {end}",
            count_task,
        )

        if numbers:
            # Display the numbers in a nice panel
            RICH_UI.show_answer_panel(
                ", ".join(map(str, numbers[:10])) + ("..." if len(numbers) > 10 else ""),
                "Counting Complete",
            )

        print(f"👌 {t('ok')}")
    except KeyboardInterrupt:
        print(f"🤚 {t('stop')}")
    except ValueError:
        print(parts)
        raise TryNext("Invalid loop command")


HANDLERS = [
    # (
    #     "Single Letter",
    #     lambda text: text.isalpha() and len(text) == 1,
    #     lambda text: f"{text.lower()}, {text.upper()}"
    # ),
    (
        "Number properties tree",
        lambda text: text.isdigit() and 1 <= int(text) <= 1000,
        lambda text: RICH_UI.show_number_tree(int(text)),
    ),
    (
        "Data key match",
        lambda text: text.lower() in [k.lower() for k in CUSTOM_DATA],
        lambda text: CUSTOM_DATA[text.lower()],
    ),
    (
        "Color name match",
        lambda text: text.count(" ") <= 4,
        handle_color_name,
    ),
    (
        "Repeated Letter - smashing keyboard on one character",
        lambda text: text.isalpha() and len(text) > 5 and len(set(text)) == 1,
        lambda text: f"{len(text)} x {text[0]}",
    ),
    (
        "Emoji Single Word via Rich",
        lambda text: len(text) > 3 and len(text) < 50 and text.isalpha(),
        show_rich_emoji,
    ),
    (
        "Series Loop",
        lambda text: "..." in text,
        run_loop,
    ),
    (
        "Symbolic Math Variable with short names",
        lambda text: len(text) < 5 and text.isalpha(),
        handle_symbol_lookup,
    ),
    (
        "Symbolic Math Expressions",
        lambda text: any([op in text for op in "+-*/"]),
        handle_symbol_expr,
    ),
    (
        "Symbolic Assignment",
        lambda text: "=" in text,
        handle_symbol_assignment,
    ),
    (
        "Literal Math Eval",
        lambda text: True,
        handle_math_input,
    ),
    (
        "Emoji Matches via Rich",
        lambda text: len(text) > 2,
        show_rich_emoji_match,
    ),
    (
        "Gibberish",
        lambda text: len(text) > 10,
        summarize_gibberish,
    ),
]


def get_profile_path() -> Path:
    """Return persisted child profile path under ~/.kidshell/config."""
    from kidshell.core.config import get_config_manager

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
        # Rejecting malformed names avoids storing control chars that can corrupt terminal output.
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
        # Failure to save profile should not stop the child from using the shell.
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
        # Non-interactive invocations (e.g., piped commands/tests) must never block on onboarding input.
        return None
    return run_onboarding(input_func=input_func, output_func=output_func, today=today_value)


def display_age(profile: ChildProfile | None = None, today: date | None = None) -> None:
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

    try:
        # Legacy fallback for custom data entries using "bday": "yyyy.mm.dd".
        bday_parts = [int(x) for x in CUSTOM_DATA["bday"].split(".")]
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
    except (KeyError, ValueError):
        # No valid birthday data configured.
        pass


def display_welcome(profile: ChildProfile | None = None, today: date | None = None) -> None:
    """Display date + personalized greeting."""
    today_value = today or date.today()
    date_format = t("date_format")
    print(f"{t('today_is')} {today_value.strftime(date_format)}")
    print()
    display_age(profile=profile, today=today_value)


def praise_phrase():
    options = t_list("great_options")
    return RNG.choice(options)


def normalize_user_input(user_input: str) -> str:
    """Normalize user input and strip pasted prompt markers like '> 1 + 1'."""
    normalized = user_input.lower().strip()
    while normalized.startswith(">"):
        normalized = normalized[1:].strip()
    return normalized


def apply_history_escape_fallback(user_input: str, last_user_input: str) -> str | None:
    """Handle pasted/raw ANSI arrow-key sequences when readline is unavailable."""
    # Convert raw Up-arrow escape input into previous command replay for kid-friendly UX.
    if re.fullmatch(r"(?:\x1b|\^\[)\[[A-D]", user_input):
        if user_input.endswith("A") and last_user_input:
            return last_user_input
        return None
    return user_input


def prompt_loop(prompt_text="> "):
    try:
        profile = ensure_child_profile()
    except (EOFError, KeyboardInterrupt):
        # Onboarding is interactive input too; handle interrupts like the main prompt without traceback.
        print(f"👋 {t('bye')}")
        sys.exit(0)
    display_welcome(profile=profile)
    enable_readline_history()
    last_user_input = ""

    while True:
        try:
            user_input = input(prompt_text)
        except (EOFError, KeyboardInterrupt):
            print(f"👋 {t('bye')}")
            sys.exit(0)

        # Fallback: when terminals send raw ANSI history keys as text (e.g. "^[[A"),
        # treat Up as "reuse last command" rather than surfacing an error to the user.
        fallback_user_input = apply_history_escape_fallback(user_input, last_user_input)
        if fallback_user_input is None:
            continue
        user_input = fallback_user_input

        normalized_input = normalize_user_input(user_input)
        if normalized_input:
            last_user_input = user_input

        output = None
        try:
            if not normalized_input:
                # empty input, pressed return
                output = generate_new_math_question(normalized_input)
            elif normalized_input == MATH_ENV.get("problem_expected_solution", math.inf):
                ACHIEVEMENTS["math_problems_solved"] += 1

                # Show achievement for milestones
                if ACHIEVEMENTS["math_problems_solved"] % 5 == 0:
                    RICH_UI.show_achievement(
                        f"{ACHIEVEMENTS['math_problems_solved']} Problems Solved!",
                        "You're doing amazing!",
                        stars=3,
                    )
                else:
                    print(f"{'_' * ACHIEVEMENTS['math_problems_solved']}{TODAY_MOTION_EMOJI}")

                output = f"👏 {praise_phrase()}！\n\n{generate_new_math_question(normalized_input)}"
            elif normalized_input in MATH_ENV:
                output = MATH_ENV[normalized_input]
            else:
                for condition_name, predicate, get_output in HANDLERS:
                    try:
                        if predicate(normalized_input):
                            if DEBUG:
                                print(f"match: {condition_name}")
                            output = get_output(normalized_input)
                            break
                    except TryNext as tne:
                        if DEBUG:
                            print(tne)

            if isinstance(output, rich_text.Text):
                DEFAULT_CONSOLE.print(output)
            elif output is None:
                # Already handled by Rich UI (e.g., tree display)
                pass
            elif output is not None:
                print(f"{RNG.choice(SUCCESS_EMOJIS)} {output}")
        except Exception:
            if DEBUG:
                raise
            print(f"{RNG.choice(FAILURE_EMOJIS)} ???")


def main():
    """Main entry point for kidshell CLI."""
    parser = argparse.ArgumentParser(description="KidShell - A child-friendly REPL")
    parser.add_argument("--language", default="en", help="Language code (e.g., en, zh_CN)")
    parser.add_argument("command", nargs="?", help="Command to run (e.g., config)")
    parser.add_argument("args", nargs="*", help="Command arguments")

    args, unknown = parser.parse_known_args()

    # Set the language
    set_language(args.language)

    # Check if user wants to manage config
    if args.command == "config":
        from kidshell.cli.config_command import config_command

        config_command(args.args + unknown)
    else:
        prompt_loop()


if __name__ == "__main__":
    main()
