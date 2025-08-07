import argparse
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

import rich.color as rich_color
import rich.console as rich_console
import rich.emoji as rich_emoji
import rich.text as rich_text

from sympy import symbols

# Import our new Rich UI module
from kidshell.cli.rich_ui import create_rich_ui
from kidshell.core.i18n import set_language, t, t_list

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

SUCCESS_EMOJIS = ["😀", "🙌", "👍", "😇"]
FAILURE_EMOJIS = ["🙈", "🤦", "😑", "😕", "🙅‍♂️"]

MOTION_EMOJIS = ["🚣", "🛫", "🚋"]
TODAY_MOTION_EMOJI = random.choice(MOTION_EMOJIS)


class TryNext(ValueError):
    pass


def show_rich_emoji(text):
    try:
        emoji_match = rich_emoji.Emoji(text)
        return f"{text} = {emoji_match}"
    except rich_emoji.NoEmoji:
        raise TryNext(f"{text}: not emoji")


def show_rich_emoji_match(text):
    matches = [
        v
        for (k, v) in rich_emoji.EMOJI.items()
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
    match_text = text.replace(" ", "_")
    for color_name_var in [match_text, f"{match_text}1"]:
        try:
            rich_color.Color.parse(color_name_var)
            match_found = True
            output = rich_text.Text()
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

    # First try the new platform-specific location
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


def handle_math_input(normalized_input):
    if isinstance(normalized_input, (int, float)):
        MATH_ENV["last_number"] = normalized_input
    elif isinstance(normalized_input, str) and normalized_input.isdigit():
        MATH_ENV["last_number"] = int(normalized_input)

    # Show thinking spinner for complex calculations
    if isinstance(normalized_input, str) and len(normalized_input) > 10:
        RICH_UI.thinking_spinner("Calculating", 0.5)

    try:
        if "=" in normalized_input:
            # handle assignment safely
            from kidshell.core.safe_math import SafeMathError, SafeMathEvaluator

            parts = normalized_input.split("=", 1)
            if len(parts) == 2:
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
    x, y = random.randint(1, number_max), random.randint(1, number_max)
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
    a, b = random.randint(1, number_max), random.randint(1, number_max)
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


def find_factors(number: int, min_factor=2) -> list[int]:
    results = []
    for factor_candidate in range(min_factor, math.floor(math.sqrt(number) + 1)):
        if number % factor_candidate == 0:
            results.append(
                (factor_candidate, number // factor_candidate),
            )
    return results


def format_factors(factors: list[int]) -> str:
    factor_seq = " = ".join([f"{a} × {b}" for a, b in factors])
    return factor_seq


def get_number_hint(number: int, placeholder="?") -> str:
    return placeholder * len(str(number))


def generate_multiplication_problem(rand_min=1, rand_max=100):
    while True:
        solution = random.randint(rand_min, rand_max)
        if factors := find_factors(solution):
            MATH_ENV["problem_expected_solution"] = str(solution)
            return f"{format_factors(factors)} = {get_number_hint(solution)}"


def generate_division_problem():
    x = random.randint(1, 10) * 10
    y = x // 10
    solution = x // y
    MATH_ENV["problem_expected_solution"] = str(solution)
    return f"{x} ➗ {y} = {get_number_hint(solution)}"


def generate_new_math_question(normalized_input):
    dice_roll = random.randint(1, 4)
    if dice_roll == 1:
        output = generate_new_addition_problem()
    elif dice_roll == 2:
        output = generate_new_subtraction_problem()
    elif dice_roll == 3:
        output = generate_multiplication_problem()
    elif dice_roll == 4:
        output = generate_division_problem()
    return output


def generate_new_math_question_basic(add_sub_max=20, mul_div_max=10):
    op = random.choice(["+", "-"])
    if op in ["+", "-"]:
        x, y = random.randint(0, add_sub_max), random.randint(0, add_sub_max)
        x, y = max(x, y), min(x, y)
    elif op == "*":
        x, y = random.randint(1, mul_div_max), random.randint(1, mul_div_max)
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
    expr_parts = parse_symbol_parts(normalized_input)
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


def display_age():
    try:
        # bday_parts: yyyy, mm, dd
        bday_parts = [int(x) for x in CUSTOM_DATA["bday"].split(".")]
        age_float = (date.today() - date(*bday_parts)).days / 365
        print(
            t("birthday_msg", year=bday_parts[0], month=bday_parts[1], day=bday_parts[2]),
        )
        print(
            t("age_msg", age=age_float),
        )
        next_age = int(math.ceil(age_float))
        next_bday = date(bday_parts[0] + next_age, bday_parts[1], bday_parts[2])
        days_until_bday = (next_bday - date.today()).days
        print(
            t("next_birthday", age=next_age, days=days_until_bday),
        )
    except (KeyError, ValueError):
        # bday data not provided
        pass


def display_welcome():
    date_format = t("date_format")
    print(f"{t('today_is')} {date.today().strftime(date_format)}")
    print()
    display_age()


def praise_phrase():
    options = t_list("great_options")
    return random.choice(options)


def prompt_loop(prompt_text="> "):
    display_welcome()

    while True:
        try:
            user_input = input(prompt_text)
        except (EOFError, KeyboardInterrupt):
            print(f"👋 {t('bye')}")
            sys.exit(0)
        normalized_input = user_input.lower().strip()
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
                print(f"{random.choice(SUCCESS_EMOJIS)} {output}")
        except Exception:
            if DEBUG:
                raise
            print(f"{random.choice(FAILURE_EMOJIS)} ???")


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
