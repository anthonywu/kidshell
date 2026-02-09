"""
Textual app for KidShell - provides a rich web interface.
"""
# pyright: reportMissingImports=false

from datetime import datetime
import random
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Static,
    TextArea,
)

from kidshell.core.engine import KidShellEngine
from kidshell.core.models import Session
from kidshell.core.session_store import load_persisted_session, save_persisted_session
from kidshell.core.types import ResponseType

MOTION_EMOJIS = ["🚣", "🛫", "🚋"]
RNG = random.SystemRandom()
EXIT_INPUTS = {"bye", "quit", ":q!"}


class ResponseDisplay(Static):
    """Widget to display a response from the engine."""

    def __init__(self, response_type: ResponseType, content: Any, **kwargs):
        super().__init__(**kwargs)
        self.response_type = response_type
        self.payload = content
        self._generate_display()

    def _generate_display(self):  # noqa: C901 PLR0912 PLR0915
        """Generate the display based on response type."""
        content = self.payload if isinstance(self.payload, dict) else {}

        if self.response_type == ResponseType.MATH_RESULT:
            expr = content.get("expression", "")
            result = content.get("result")
            display = f"[bold cyan]{expr}[/bold cyan] = [bold green]{result}[/bold green]"
            if content.get("note"):
                display += f"\n[dim]{content['note']}[/dim]"
            self.update(display)

        elif self.response_type == ResponseType.TREE_DISPLAY:
            number = content.get("number")
            properties = content.get("properties", [])
            factors = content.get("factors", [])

            display = f"[bold yellow]Number {number}[/bold yellow]\n\n"
            display += "[bold]Properties:[/bold]\n"
            for prop, color in properties:
                display += f"  • [{color}]{prop}[/{color}]\n"

            display += "\n[bold]Factors:[/bold] "
            display += ", ".join(f"({a}×{b})" for a, b in factors)  # noqa: RUF001

            self.update(display)

        elif self.response_type == ResponseType.COLOR:
            name = content.get("name")
            color = content.get("color", name)
            emojis = content.get("emojis", [])

            display = f"[{color}]█████ {name}[/{color}]"
            if emojis:
                display += f"\n{' '.join(emojis[:5])}"
            self.update(display)

        elif self.response_type == ResponseType.EMOJI:
            word = content.get("word")
            if "emoji" in content:
                emoji = content.get("emoji")
                self.update(f"{word} → {emoji}")
            elif "emojis" in content:
                emojis = content.get("emojis", [])
                self.update(f"{word} → {' '.join(emojis[:10])}")
            else:
                self.update(f"No emoji for '{word}'")

        elif self.response_type == ResponseType.SYMBOL_RESULT:
            symbol = content.get("symbol", "")
            action = content.get("action", "")
            value = content.get("value", "")
            display = content.get("display", "")

            if action == "created":
                self.update(f"[bold magenta]Created symbol:[/bold magenta] {symbol}")
            elif action in {"assigned", "found"}:
                self.update(f"[bold magenta]{symbol} = {value}[/bold magenta]")
            elif display:
                # Show expression with result
                self.update(f"[bold magenta]{display}[/bold magenta]")
            else:
                result = content.get("result", value)
                self.update(f"[bold magenta]{result}[/bold magenta]")

        elif self.response_type == ResponseType.LOOP_RESULT:
            values = content.get("values", [])
            rendered_values = ", ".join(map(str, values[:20]))
            if len(values) > 20:  # noqa: PLR2004
                rendered_values += "..."
            self.update(f"[bold cyan]Loop:[/bold cyan] {rendered_values}")

        elif self.response_type == ResponseType.QUIZ:
            if isinstance(self.payload, dict):
                if content.get("correct"):
                    answer = content.get("answer")
                    streak = content.get("streak", 0)
                    display = f"[bold green]✓ Correct![/bold green] Answer: {answer}\nStreak: {streak}"
                    next_quiz = content.get("next_quiz")
                    if isinstance(next_quiz, dict):
                        next_question = next_quiz.get("question")
                        if next_question:
                            display += f"\n\n[bold yellow]Next: {next_question}[/bold yellow]"
                    self.update(display)
                elif "correct" in content:
                    encouragement = content.get("encouragement", "Nice thinking.")
                    display = f"[bold green]🌟 {encouragement}[/bold green]"
                    hint = content.get("hint")
                    if hint:
                        display += f"\n[cyan]💡 {hint}[/cyan]"

                    number_facts = content.get("number_facts")
                    if isinstance(number_facts, dict):
                        number = number_facts.get("number")
                        if number is not None:
                            display += f"\n\n[bold yellow]About {number}:[/bold yellow]"
                        factors = number_facts.get("factors", [])
                        if factors:
                            pairs = ", ".join(f"{a}×{b}" for a, b in factors[:8])
                            display += f"\nFactors: {pairs}"
                        properties = number_facts.get("properties", [])
                        if properties:
                            prop_names = ", ".join(prop for prop, _ in properties[:5])
                            display += f"\nProperties: {prop_names}"

                    self.update(display)
                else:
                    question = content.get("question", str(self.payload))
                    self.update(f"[bold yellow]Quiz: {question}[/bold yellow]")
            else:
                # New quiz
                self.update(f"[bold yellow]Quiz: {self.payload}[/bold yellow]")

        elif self.response_type == ResponseType.ERROR:
            self.update(f"[bold red]Error:[/bold red] {self.payload}")

        else:
            # Default text display
            self.update(str(self.payload))


class KidShellTextualApp(App):
    """Textual app for KidShell."""

    BINDINGS = [
        # macOS terminals often emit super/meta for Command shortcuts.
        Binding("super+c", "platform_copy", "Copy", show=False),
        Binding("super+v", "platform_paste", "Paste", show=False),
        Binding("meta+c", "platform_copy", "Copy", show=False),
        Binding("meta+v", "platform_paste", "Paste", show=False),
    ]

    CSS = """
    .history-container {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    .history-input {
        color: $text 70%;
        margin-bottom: 0;
    }

    #history {
        height: 1fr;
        border: none;
        margin: 0;
        padding: 0;
    }

    .input-container {
        height: 3;
        dock: bottom;
        background: $surface;
        padding: 0 1;
    }

    Input {
        width: 100%;
    }

    .stats-panel {
        width: 30;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .stat-item {
        margin-bottom: 1;
    }

    .progress-track {
        height: 4;
    }
    """

    TITLE = "KidShell 🖥️"
    SUB_TITLE = " – A Terminal experience for your childish expectations!"

    def __init__(self, session: Session | None = None):
        super().__init__()
        self.engine = KidShellEngine(session or Session())
        self.history_items = []
        self._progress_emoji = RNG.choice(MOTION_EMOJIS)
        self._progress_track_length = 18

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Horizontal():
            # Main area with history
            with Vertical(classes="history-container"):
                yield Label("KidShell - Type math problems, colors, or emoji names!", classes="title")
                yield TextArea(
                    "",
                    id="history",
                    read_only=True,
                    show_line_numbers=False,
                    show_cursor=False,
                    soft_wrap=True,
                    placeholder="History appears here. Click to select text, Ctrl+C to copy.",
                )

            # Stats panel
            with Vertical(classes="stats-panel"):
                yield Label("Stats", classes="title")
                yield Label("Problems Solved: 0", id="problems-solved", classes="stat-item")
                yield Label("Current Streak: 0", id="streak", classes="stat-item")
                yield Label("", id="current-quiz", classes="stat-item")
                yield Label("Progress track", id="achievement-progress", classes="stat-item progress-track")
                yield Label("Session Time: 0:00", id="session-time", classes="stat-item")

        # Input area
        with Horizontal(classes="input-container"):
            yield Input(placeholder="Enter expression, number, color, or emoji...", id="input")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize when app starts."""
        # Keep app-local session timer separate from Textual internals.
        self._session_started_at = datetime.now()

        if self.engine.session.current_quiz:
            self._display_quiz(self.engine.session.current_quiz)
        else:
            # Generate initial quiz for fresh sessions.
            response = self.engine.process_input("")
            if response.type == ResponseType.QUIZ:
                self._display_quiz(response.content)

        # Focus on input
        self.query_one("#input", Input).focus()

        # Start session timer
        self.set_interval(1, self._update_session_time)
        self._update_stats()

    def _update_session_time(self) -> None:
        """Update the session timer."""
        if not hasattr(self, "_session_started_at") or not isinstance(self._session_started_at, datetime):
            self._session_started_at = datetime.now()

        elapsed = datetime.now() - self._session_started_at
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        self.query_one("#session-time", Label).update(f"Session Time: {minutes}:{seconds:02d}")

    def _display_quiz(self, quiz_content):
        """Display current quiz in stats panel."""
        if isinstance(quiz_content, dict):
            question = quiz_content.get("question", "")
            self.query_one("#current-quiz", Label).update(f"[bold yellow]Quiz: {question}[/bold yellow]")
        else:
            self.query_one("#current-quiz", Label).update(f"[bold yellow]Quiz: {quiz_content}[/bold yellow]")

    def _update_stats(self):
        """Update the stats panel."""
        session = self.engine.session
        self.query_one("#problems-solved", Label).update(f"Problems Solved: {session.problems_solved}")
        self.query_one("#streak", Label).update(f"Current Streak: {session.current_streak}")
        self.query_one("#achievement-progress", Label).update(
            self._render_achievement_progress(session.problems_solved),
        )

        if session.current_quiz:
            self._display_quiz(session.current_quiz)
        else:
            self.query_one("#current-quiz", Label).update("")

    def _render_achievement_progress(self, solved_count: int) -> str:
        """Render motion-emoji progress lane for solved-problem count."""
        solved = max(0, int(solved_count))
        lane_size = self._progress_track_length + 1
        position = solved % lane_size
        laps = solved // lane_size
        lane = ["_"] * lane_size
        lane[position] = self._progress_emoji
        lap_suffix = f" (lap {laps + 1})" if laps > 0 else ""
        return f"Progress track\n{''.join(lane)}\nSolved: {solved}{lap_suffix}"

    def _format_history_response(self, response_type: ResponseType, payload: Any) -> str:  # noqa: C901
        """Render a plain-text transcript line for selectable history view."""
        content = payload if isinstance(payload, dict) else {}

        if response_type == ResponseType.MATH_RESULT:
            expression = content.get("display") or f"{content.get('expression', '')} = {content.get('result')}"
            note = content.get("note")
            if note:
                return f"{str(expression).strip()}\n{note}"
            return str(expression).strip()

        if response_type == ResponseType.TREE_DISPLAY:
            number = content.get("number")
            factors = content.get("factors", [])
            properties = content.get("properties", [])
            lines = [f"Number {number}"]
            if factors:
                lines.append("Factors: " + ", ".join(f"{a}x{b}" for a, b in factors[:8]))
            if properties:
                lines.append("Properties: " + ", ".join(prop for prop, _ in properties[:6]))
            return "\n".join(lines)

        if response_type == ResponseType.COLOR:
            name = content.get("name", "")
            emojis = content.get("emojis", [])
            line = f"Color: {name}".strip()
            if emojis:
                line += "\nRelated: " + " ".join(emojis[:8])
            return line

        if response_type == ResponseType.EMOJI:
            if "emoji" in content:
                return f"{content.get('word', '')} -> {content.get('emoji')}"
            if "emojis" in content:
                return f"{content.get('word', '')} -> {' '.join(content.get('emojis', [])[:10])}"
            return f"No emoji for '{content.get('word', '')}'"

        if response_type == ResponseType.SYMBOL_RESULT:
            if content.get("display"):
                return str(content["display"])
            if content.get("action") == "created":
                return f"Created symbol: {content.get('symbol')}"
            if content.get("action") in {"assigned", "found"}:
                return f"{content.get('symbol')} = {content.get('value')}"
            return str(content.get("result", payload))

        if response_type == ResponseType.LOOP_RESULT:
            values = content.get("values", [])
            rendered_values = ", ".join(map(str, values[:20]))
            if len(values) > 20:  # noqa: PLR2004
                rendered_values += "..."
            return f"Loop: {rendered_values}"

        if response_type == ResponseType.QUIZ:
            if isinstance(payload, dict):
                if content.get("correct"):
                    lines = ["Correct!"]
                    if "answer" in content:
                        lines.append(f"Answer: {content['answer']}")
                    if content.get("streak") is not None:
                        lines.append(f"Streak: {content.get('streak', 0)}")
                    next_quiz = content.get("next_quiz")
                    if isinstance(next_quiz, dict) and next_quiz.get("question"):
                        lines.append(f"Next: {next_quiz['question']}")
                    return "\n".join(lines)

                if "correct" in content:
                    lines = []
                    if content.get("encouragement"):
                        lines.append(str(content["encouragement"]))
                    if content.get("hint"):
                        lines.append(str(content["hint"]))
                    number_facts = content.get("number_facts")
                    if isinstance(number_facts, dict):
                        number = number_facts.get("number")
                        if number is not None:
                            lines.append(f"About {number}:")
                        factors = number_facts.get("factors", [])
                        if factors:
                            lines.append("Factors: " + ", ".join(f"{a}x{b}" for a, b in factors[:8]))
                    quiz = content.get("quiz")
                    if isinstance(quiz, dict) and quiz.get("question"):
                        lines.append(f"Quiz: {quiz['question']}")
                    return "\n".join(lines) if lines else "Keep going!"

                if content.get("question"):
                    return f"Quiz: {content.get('question')}"
            return str(payload)

        if response_type == ResponseType.ERROR:
            return f"Error: {payload}"

        return str(payload)

    @on(Input.Submitted)
    async def handle_input(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        input_text = event.value.strip()
        normalized_input = input_text.lower()

        if normalized_input in EXIT_INPUTS:
            save_persisted_session(self.engine.session)
            self.exit()
            return

        response = self.engine.process_input("") if not input_text else self.engine.process_input(input_text)
        responses = [response]

        # Keep parity with terminal frontend: display pending response after achievements.
        pending = self.engine.get_pending_response()
        if pending is not None:
            responses.append(pending)

        # Add to history
        if input_text:  # Only add non-empty inputs to history
            history = self.query_one("#history", TextArea)
            for index, current in enumerate(responses):
                display_input = input_text if index == 0 else "..."
                response_text = self._format_history_response(current.type, current.content)
                history.insert(
                    f"> {display_input}\n{response_text}\n\n",
                    history.document.end,
                )

            # Auto-scroll to bottom
            history.scroll_end(animate=False)

        # Update stats
        self._update_stats()

        # Handle quiz updates
        for current in responses:
            if current.type == ResponseType.QUIZ:
                if isinstance(current.content, dict):
                    if "next_quiz" in current.content:
                        self._display_quiz(current.content["next_quiz"])
                    elif "quiz" in current.content:
                        self._display_quiz(current.content["quiz"])
                else:
                    self._display_quiz(current.content)

        # Clear input
        event.input.value = ""
        save_persisted_session(self.engine.session)

    def action_quit(self) -> None:
        """Quit the application."""
        save_persisted_session(self.engine.session)
        self.exit()

    def action_platform_copy(self) -> None:
        """Copy selected text with platform shortcut bindings (e.g., Cmd-C on macOS)."""
        focused = self.focused
        if focused is not None and hasattr(focused, "action_copy"):
            try:
                focused.action_copy()
                return
            except Exception:
                pass

        history = self.query_one("#history", TextArea)
        try:
            history.action_copy()
        except Exception:
            pass

    def action_platform_paste(self) -> None:
        """Paste text with platform shortcut bindings (e.g., Cmd-V on macOS)."""
        focused = self.focused
        if focused is not None and hasattr(focused, "action_paste"):
            try:
                focused.action_paste()
                return
            except Exception:
                pass

        input_widget = self.query_one("#input", Input)
        try:
            input_widget.action_paste()
        except Exception:
            clipboard = self.clipboard
            if clipboard:
                input_widget.insert_text_at_cursor(clipboard)


def main(*, start_new: bool = False):
    """Run the Textual app."""
    session = None if start_new else load_persisted_session()
    app = KidShellTextualApp(session=session)
    app.run()


if __name__ == "__main__":
    main()
