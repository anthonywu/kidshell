"""
Textual app for KidShell - provides a rich web interface.
"""

from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from kidshell.core.engine import KidShellEngine
from kidshell.core.types import ResponseType


class ResponseDisplay(Static):
    """Widget to display a response from the engine."""

    def __init__(self, response_type: ResponseType, content: any, **kwargs):
        super().__init__(**kwargs)
        self.response_type = response_type
        self.content = content
        self._generate_display()

    def _generate_display(self):  # noqa: C901 PLR0912 PLR0915
        """Generate the display based on response type."""
        if self.response_type == ResponseType.MATH_RESULT:
            expr = self.content.get("expression", "")
            result = self.content.get("result")
            self.update(f"[bold cyan]{expr}[/bold cyan] = [bold green]{result}[/bold green]")

        elif self.response_type == ResponseType.TREE_DISPLAY:
            number = self.content.get("number")
            properties = self.content.get("properties", [])
            factors = self.content.get("factors", [])

            display = f"[bold yellow]Number {number}[/bold yellow]\n\n"
            display += "[bold]Properties:[/bold]\n"
            for prop, color in properties:
                display += f"  • [{color}]{prop}[/{color}]\n"

            display += "\n[bold]Factors:[/bold] "
            display += ", ".join(f"({a}×{b})" for a, b in factors)  # noqa: RUF001

            self.update(display)

        elif self.response_type == ResponseType.COLOR:
            name = self.content.get("name")
            color = self.content.get("color", name)
            emojis = self.content.get("emojis", [])

            display = f"[{color}]█████ {name}[/{color}]"
            if emojis:
                display += f"\n{' '.join(emojis[:5])}"
            self.update(display)

        elif self.response_type == ResponseType.EMOJI:
            word = self.content.get("word")
            if "emoji" in self.content:
                emoji = self.content.get("emoji")
                self.update(f"{word} → {emoji}")
            elif "emojis" in self.content:
                emojis = self.content.get("emojis", [])
                self.update(f"{word} → {' '.join(emojis[:10])}")
            else:
                self.update(f"No emoji for '{word}'")

        elif self.response_type == ResponseType.SYMBOL_RESULT:
            symbol = self.content.get("symbol", "")
            action = self.content.get("action", "")
            value = self.content.get("value", "")
            display = self.content.get("display", "")

            if action == "created":
                self.update(f"[bold magenta]Created symbol:[/bold magenta] {symbol}")
            elif action in {"assigned", "found"}:
                self.update(f"[bold magenta]{symbol} = {value}[/bold magenta]")
            elif display:
                # Show expression with result
                self.update(f"[bold magenta]{display}[/bold magenta]")
            else:
                result = self.content.get("result", value)
                self.update(f"[bold magenta]{result}[/bold magenta]")

        elif self.response_type == ResponseType.LOOP_RESULT:
            values = self.content.get("values", [])
            self.update(f"[bold cyan]Loop:[/bold cyan] {', '.join(map(str, values[:20]))}")
            if len(values) > 20:  # noqa: PLR2004
                self.update(self.renderable + "...")

        elif self.response_type == ResponseType.QUIZ:
            if isinstance(self.content, dict):
                if self.content.get("correct"):
                    answer = self.content.get("answer")
                    streak = self.content.get("streak", 0)
                    self.update(f"[bold green]✓ Correct![/bold green] Answer: {answer}\nStreak: {streak}")

                    if "next_quiz" in self.content:
                        next_quiz = self.content["next_quiz"]
                        self.update(
                            self.renderable + f"\n\n[bold yellow]Next: {next_quiz.get('question')}[/bold yellow]"
                        )
                else:
                    hint = self.content.get("hint", "Try again!")
                    self.update(f"[bold red]✗ {hint}[/bold red]")
            else:
                # New quiz
                question = self.content.get("question", self.content)
                self.update(f"[bold yellow]Quiz: {question}[/bold yellow]")

        elif self.response_type == ResponseType.ERROR:
            self.update(f"[bold red]Error:[/bold red] {self.content}")

        else:
            # Default text display
            self.update(str(self.content))


class HistoryItem(ListItem):
    """A single item in the history."""

    def __init__(self, input_text: str, response_display: ResponseDisplay):
        super().__init__()
        self.input_text = input_text
        self.response_display = response_display

    def compose(self) -> ComposeResult:
        yield Label(f"[dim]>[/dim] {self.input_text}", classes="history-input")
        yield self.response_display


class KidShellTextualApp(App):
    """Textual app for KidShell."""

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

    ResponseDisplay {
        margin-bottom: 1;
        padding-left: 2;
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
    """

    TITLE = "KidShell 🐚"
    SUB_TITLE = "A fun math shell for kids!"

    def __init__(self):
        super().__init__()
        self.engine = KidShellEngine()
        self.history_items = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Horizontal():
            # Main area with history
            with Vertical(classes="history-container"):
                yield Label("KidShell - Type math problems, colors, or emoji names!", classes="title")
                yield ListView(id="history")

            # Stats panel
            with Vertical(classes="stats-panel"):
                yield Label("Stats", classes="title")
                yield Label("Problems Solved: 0", id="problems-solved", classes="stat-item")
                yield Label("Current Streak: 0", id="streak", classes="stat-item")
                yield Label("", id="current-quiz", classes="stat-item")
                yield Label("Session Time: 0:00", id="session-time", classes="stat-item")

        # Input area
        with Horizontal(classes="input-container"):
            yield Input(placeholder="Enter expression, number, color, or emoji...", id="input")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize when app starts."""
        # Initialize start time first
        self._start_time = datetime.now()

        # Generate initial quiz
        response = self.engine.process_input("")
        if response.type == ResponseType.QUIZ:
            self._display_quiz(response.content)

        # Focus on input
        self.query_one("#input", Input).focus()

        # Start session timer
        self.set_interval(1, self._update_session_time)

    def _update_session_time(self) -> None:
        """Update the session timer."""
        # Ensure _start_time is a datetime object
        if not hasattr(self, "_start_time") or not isinstance(self._start_time, datetime):
            self._start_time = datetime.now()

        elapsed = datetime.now() - self._start_time
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

        if session.current_quiz:
            self._display_quiz(session.current_quiz)
        else:
            self.query_one("#current-quiz", Label).update("")

    @on(Input.Submitted)
    async def handle_input(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        input_text = event.value.strip()

        response = self.engine.process_input("") if not input_text else self.engine.process_input(input_text)

        # Create response display widget
        response_display = ResponseDisplay(response.type, response.content)

        # Add to history
        if input_text:  # Only add non-empty inputs to history
            history_item = HistoryItem(input_text, response_display)
            history_list = self.query_one("#history", ListView)
            history_list.append(history_item)

            # Auto-scroll to bottom
            history_list.scroll_end(animate=True)

        # Update stats
        self._update_stats()

        # Handle quiz updates
        if response.type == ResponseType.QUIZ:
            if isinstance(response.content, dict):
                if "next_quiz" in response.content:
                    self._display_quiz(response.content["next_quiz"])
                elif "quiz" in response.content:
                    self._display_quiz(response.content["quiz"])
            else:
                self._display_quiz(response.content)

        # Clear input
        event.input.value = ""

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def main():
    """Run the Textual app."""
    app = KidShellTextualApp()
    app.run()


if __name__ == "__main__":
    main()
