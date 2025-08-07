"""
Terminal application using KidShell core.
"""

import functools
import math
import os
import random
import sys
from datetime import date

import rich.console as rich_console
import rich.text as rich_text

from kidshell.cli.rich_ui import KidShellRichUI
from kidshell.core import KidShellEngine, ResponseType, Session
from kidshell.core.models.achievements import get_achievement
from kidshell.core.services import DataService

# Console setup
DEFAULT_CONSOLE = rich_console.Console(emoji=True, highlight=True, markup=True)
print = functools.partial(DEFAULT_CONSOLE.print, end="\n\n")  # noqa: A001


class TerminalApp:
    """Terminal frontend for KidShell."""

    def __init__(self):
        """Initialize terminal app."""
        self.session = Session()
        self.engine = KidShellEngine(self.session)
        self.ui = KidShellRichUI(DEFAULT_CONSOLE)
        self.custom_data = DataService.load_data_files()
        self.debug = "DEBUG" in os.environ

        # Motion emojis for achievements
        self.motion_emojis = ["🚣", "🛫", "🚋"]
        self.today_motion_emoji = random.choice(self.motion_emojis)

        # Load custom data into session
        self.session.custom_data = dict(self.custom_data)

    def display_welcome(self):
        """Display welcome message."""
        print(f"今天是 {date.today().isoformat()}.")
        print(f"Today is {date.today().strftime('%A, %B %d')}")

        # Display age if birthday is configured
        bday = DataService.get_birthday_info(self.custom_data)
        if bday:
            try:
                bday_parts = [int(x) for x in bday.split(".")]
                bday_date = date(*bday_parts)
                age_float = (date.today() - bday_date).days / 365

                print(
                    f"My birthday is {bday_parts[0]}-{bday_parts[1]}-{bday_parts[2]}.\n"
                    f"我的生日是 is {bday_parts[0]}年 {bday_parts[1]}月 {bday_parts[2]}号。\n"
                    f"Today, I am {age_float:.02f} years old.\n"
                    f"今天，我是 {age_float:.02f} 岁。",
                )

                next_age = int(math.ceil(age_float))
                next_bday = date(bday_parts[0] + next_age, bday_parts[1], bday_parts[2])
                days_until_bday = (next_bday - date.today()).days

                print(
                    f"I will be {next_age} years old in {days_until_bday} days. "
                    f"过{days_until_bday}天, 我就是{next_age}岁了。",
                )
            except (ValueError, IndexError):
                pass

    def display_response(self, response):  # noqa: C901
        """
        Display response using appropriate UI method.

        Args:
            response: Response object from core engine
        """
        if response.type == ResponseType.MATH_RESULT:
            content = response.content
            if content["result"] is not None:
                # Use display field if available for clearer output
                if "display" in content:
                    print(f"🙌 {content['display']}")
                else:
                    self.ui.show_math_result(content["expression"], content["result"])

        elif response.type == ResponseType.TREE_DISPLAY:
            content = response.content
            self.ui.show_number_tree(content["number"])

        elif response.type == ResponseType.QUIZ:
            content = response.content
            if content.get("correct"):
                # Correct answer
                print(f"👏 {self._praise_phrase()}！")
                if content.get("streak", 0) > 1:
                    print(f"Streak: {content['streak']} in a row! 🔥")
                # Show next quiz
                if "next_quiz" in content:
                    print(content["next_quiz"]["question"] + " = ?")
            else:
                # Wrong answer
                print(f"🙈 {content.get('hint', 'Try again!')}")
                if "quiz" in content:
                    print(content["quiz"]["question"] + " = ?")

        elif response.type == ResponseType.ACHIEVEMENT:
            content = response.content
            for achievement_id in content["achievements"]:
                achievement = get_achievement(achievement_id)
                if achievement:
                    self.ui.show_achievement(
                        achievement.name,
                        achievement.description,
                        achievement.stars,
                    )
            # Show progress bar
            print(f"{'_' * content['total_solved']}{self.today_motion_emoji}")

        elif response.type == ResponseType.SYMBOL_RESULT:
            content = response.content
            if content.get("action") == "created":
                print(f"Add Symbol 新符号: {content['symbol']}")
            elif content.get("action") == "found":
                print(f"Found Symbol 符号: {content['value']}")
            elif content.get("action") == "assigned":
                print(f"Set {content['symbol']} = {content['value']}")
            elif "display" in content:
                # Show expression with result for clarity
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
                print(f"No emoji for '{content['word']}'")

        elif response.type == ResponseType.COLOR:
            content = response.content
            # Use Rich text for color display
            output = rich_text.Text()
            output.append("Color: ", style="bold white")
            output.append(content["name"], style=f"bold {content['color']}")
            DEFAULT_CONSOLE.print(output)

            if content.get("emojis"):
                print(f"Related: {' '.join(content['emojis'])}")

        elif response.type == ResponseType.LOOP_RESULT:
            content = response.content
            # Show with status message
            self.ui.status_message(
                f"Counting from {content['start']} to {content['end']}",
                duration=0.5,
            )

            # Display numbers
            numbers = content["numbers"]
            if len(numbers) <= 20:
                display = ", ".join(map(str, numbers))
            else:
                display = ", ".join(map(str, numbers[:10])) + "..." + ", ".join(map(str, numbers[-5:]))

            self.ui.show_answer_panel(display, "Counting Complete")
            print("👌 好了 OK")

        elif response.type == ResponseType.ERROR:
            print(f"🙈 {response.content}")

        elif response.type == ResponseType.TEXT or response.content:
            print(f"🙌 {response.content}")

    def _praise_phrase(self) -> str:
        """Get random praise phrase."""
        options = ["好棒", "真棒", "精彩", "奇妙", "Great", "Awesome", "Amazing"]
        return random.choice(options)

    def run(self):
        """Run the terminal REPL."""
        self.display_welcome()

        # Main loop
        prompt_text = "> "

        while True:
            try:
                user_input = input(prompt_text)
            except (EOFError, KeyboardInterrupt):
                print("👋 再见 Bye Bye!")
                sys.exit(0)

            # Process input through core engine
            try:
                response = self.engine.process_input(user_input)
                self.display_response(response)

                # Check for pending response (e.g., after achievement)
                pending = self.engine.get_pending_response()
                if pending:
                    self.display_response(pending)

            except Exception as e:
                if self.debug:
                    raise
                print(f"🙈 Error: {e!s}")


def main():
    """Main entry point for terminal frontend."""
    app = TerminalApp()
    app.run()


if __name__ == "__main__":
    main()
