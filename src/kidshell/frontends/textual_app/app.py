"""
Textual app for KidShell - provides a rich web interface.
"""
# pyright: reportMissingImports=false

from datetime import datetime
import random
from typing import Any

import rich.color as rich_color
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.timer import Timer
from textual.widgets import (
    Footer,
    Header,
    HelpPanel,
    Input,
    Label,
    Static,
    TextArea,
)

from kidshell.core.engine import KidShellEngine
from kidshell.core.models import Session
from kidshell.core.models.achievements import get_achievement
from kidshell.core.session_store import load_persisted_session, save_persisted_session
from kidshell.core.types import ResponseType

MOTION_EMOJIS = ["🚣", "🛫", "🚋", "🚀", "👟"]
CELEBRATION_SPARKLES = ("✨", "🌟", "🎉", "🎊", "⭐", "💫")
FIREWORKS_BY_TIER = {
    1: "🎉 ✨ 🎉",
    2: "🎆 🎇 ✨ 🎉 ✨ 🎇 🎆",
    3: "🎇 🎆 💥 ✨ 🎉 ✨ 💥 🎆 🎇",
}
CELEBRATION_CAPTIONS = {
    1: "Nice streak!",
    2: "Hot streak!",
    3: "Legendary streak!",
}
RNG = random.SystemRandom()
EXIT_INPUTS = {"bye", "quit", "exit", "close", ":q!"}
FIREWORKS_INPUTS = {":fireworks", "fireworks", ":boom"}


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
                    solved_quiz = content.get("quiz")
                    solved_question = ""
                    if isinstance(solved_quiz, dict):
                        solved_question = str(solved_quiz.get("question", "")).strip()
                    if not solved_question:
                        solved_question = str(content.get("question", "")).strip()
                    answer = content.get("answer")
                    streak = content.get("streak", 0)
                    if solved_question and answer is not None:
                        display = f"[bold green]✓ Correct, {solved_question} = {answer}![/bold green]"
                    elif answer is not None:
                        display = f"[bold green]✓ Correct![/bold green] Answer: {answer}"
                    else:
                        display = "[bold green]✓ Correct![/bold green]"
                    if streak > 1:
                        display += f"\nStreak: {streak}"
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
    .app-body {
        height: 1fr;
    }

    .history-container {
        height: 1fr;
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
        background: $surface;
        padding: 0 1;
    }

    Input {
        width: 100%;
    }

    .stats-strip {
        height: 6;
        border: solid $primary;
        background: $surface;
        padding: 0 1;
    }

    .stats-strip .stat-item {
        width: 1fr;
        height: 100%;
        content-align: left middle;
        padding: 0 1;
        background: transparent;
        color: $text;
    }

    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .quiz-item {
        width: 2fr;
    }

    .progress-track {
        width: 2fr;
    }
    """

    TITLE = "🖥️ KidShell"
    SUB_TITLE = "A Terminal experience for your childish expectations!"

    def __init__(self, session: Session | None = None):
        super().__init__()
        self.engine = KidShellEngine(session or Session())
        self.history_items = []
        self._progress_emoji = RNG.choice(MOTION_EMOJIS)
        self._progress_track_length = 18
        self._celebration_timer: Timer | None = None
        self._celebration_ticks_remaining = 0
        self._celebration_frame = 0
        self._celebration_tier = 1
        self._celebration_message = ""
        self._progress_boost_ticks_remaining = 0
        self._progress_boost_velocity = 0
        self._progress_boost_offset = 0
        self._fireworks_timer: Timer | None = None
        self._fireworks_history_block = ""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Vertical(classes="app-body"):
            # Row 1: main history
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

            # Row 2: horizontal stats strip
            with Horizontal(classes="stats-strip"):
                yield Label("", id="current-quiz", classes="stat-item quiz-item")
                yield Label("Problems Solved: 0", id="problems-solved", classes="stat-item")
                yield Label("Current Streak: 0", id="streak", classes="stat-item")
                yield Label("Progress track", id="achievement-progress", classes="stat-item progress-track")
                yield Label("Session Time: 0:00", id="session-time", classes="stat-item")

            # Row 3: input line
            with Horizontal(classes="input-container"):
                yield Input(placeholder="Enter expression, solve the quiz question above, or just type in any number, color, or emoji you know!", id="input")

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
        progress_label = self.query_one("#achievement-progress", Label)
        if self._celebration_ticks_remaining > 0:
            progress_label.update(self._render_celebration_progress())
        else:
            progress_label.update(self._render_achievement_progress(session.problems_solved))

        if session.current_quiz:
            self._display_quiz(session.current_quiz)
        else:
            self.query_one("#current-quiz", Label).update("")

    def _render_achievement_progress(self, solved_count: int) -> str:
        """Render motion-emoji progress lane for solved-problem count."""
        solved = max(0, int(solved_count))
        lane_size = self._progress_track_length + 1
        position = (solved + self._progress_boost_offset) % lane_size
        laps = solved // lane_size
        lane = ["_"] * lane_size
        lane[position] = self._progress_emoji
        lap_suffix = f" (lap {laps + 1})" if laps > 0 else ""
        return f"Progress track\n{''.join(lane)}\nSolved: {solved}{lap_suffix}"

    def _achievement_names(self, achievement_ids: list[str]) -> str:
        """Resolve achievement IDs to user-facing names."""
        names: list[str] = []
        for achievement_id in achievement_ids:
            achievement = get_achievement(str(achievement_id))
            names.append(achievement.name if achievement else str(achievement_id))
        return ", ".join(names)

    def _celebration_tier_for_payload(self, payload: dict[str, Any]) -> int:
        """Map unlocked achievements to a celebration intensity tier."""
        raw_ids = payload.get("achievements", [])
        achievement_ids = [str(achievement_id) for achievement_id in raw_ids] if isinstance(raw_ids, list) else []
        max_stars = 1
        for achievement_id in achievement_ids:
            achievement = get_achievement(achievement_id)
            if achievement is not None:
                max_stars = max(max_stars, achievement.stars)

        total_solved_raw = payload.get("total_solved", 0)
        try:
            total_solved = int(total_solved_raw)
        except (TypeError, ValueError):
            total_solved = 0

        if max_stars >= 3 or total_solved >= 25:
            return 3
        if max_stars >= 2 or total_solved >= 10:
            return 2
        return 1

    def _boost_profile_for_tier(self, tier: int) -> tuple[int, int, int]:
        """Return animation profile values: celebration ticks, boost ticks, boost velocity."""
        if tier >= 3:
            return (24, 20, 3)
        if tier == 2:
            return (18, 14, 2)
        return (14, 8, 1)

    def _render_celebration_progress(self) -> str:
        """Render animated celebration header above the progress lane."""
        lane_lines = self._render_achievement_progress(self.engine.session.problems_solved).splitlines()
        if len(lane_lines) < 3:
            return self._render_achievement_progress(self.engine.session.problems_solved)

        spark = CELEBRATION_SPARKLES[self._celebration_frame % len(CELEBRATION_SPARKLES)]
        width = max(28, len(lane_lines[1]))
        banner = f"{spark} {self._celebration_message} {spark}"
        padded = f"   {banner}   "
        repeated = padded * ((width // max(1, len(padded))) + 3)
        offset = self._celebration_frame % len(padded)
        marquee = repeated[offset : offset + width]
        footer_spark = CELEBRATION_SPARKLES[(self._celebration_frame + 2) % len(CELEBRATION_SPARKLES)]
        return f"{marquee}\n{lane_lines[1]}\n{footer_spark} {lane_lines[2]}"

    def _fireworks_line_for_tier(self, tier: int) -> str:
        """Render one celebratory history line by intensity tier."""
        normalized_tier = 1 if tier < 1 else 3 if tier > 3 else tier
        fireworks = FIREWORKS_BY_TIER[normalized_tier]
        caption = CELEBRATION_CAPTIONS[normalized_tier]
        return f"{fireworks} {caption} {fireworks}"

    def _clear_fireworks_burst(self) -> None:
        """Clear any transient fireworks line from transcript history."""
        if self._fireworks_timer is not None:
            self._fireworks_timer.stop()
            self._fireworks_timer = None

        if not self._fireworks_history_block:
            return

        try:
            history = self.query_one("#history", TextArea)
        except NoMatches:
            self._fireworks_history_block = ""
            return

        current_text = history.text
        if self._fireworks_history_block in current_text:
            history.load_text(current_text.replace(self._fireworks_history_block, "", 1))
            history.scroll_end(animate=False)

        self._fireworks_history_block = ""

    def _start_fireworks_burst(self, tier: int, *, duration_seconds: float = 1.0) -> None:
        """Append a short-lived fireworks line to history."""
        self._clear_fireworks_burst()

        try:
            history = self.query_one("#history", TextArea)
        except NoMatches:
            return

        line = self._fireworks_line_for_tier(tier)
        block = f"{line}\n\n"
        history.insert(block, history.document.end)
        history.scroll_end(animate=False)
        self._fireworks_history_block = block

        if duration_seconds > 0:
            self._fireworks_timer = self.set_timer(duration_seconds, self._clear_fireworks_burst)

    def _stop_celebration_animation(self) -> None:
        """Stop any running celebration animation timer."""
        if self._celebration_timer is not None:
            self._celebration_timer.stop()
            self._celebration_timer = None
        self._celebration_ticks_remaining = 0
        self._progress_boost_ticks_remaining = 0
        self._progress_boost_velocity = 0
        self._progress_boost_offset = 0

    def _advance_progress_boost(self) -> bool:
        """Advance transient progress-lane speed boost after an achievement."""
        if self._progress_boost_ticks_remaining <= 0 or self._progress_boost_velocity <= 0:
            return False

        self._progress_boost_ticks_remaining -= 1
        self._progress_boost_offset += self._progress_boost_velocity

        if self._progress_boost_ticks_remaining <= 0:
            self._progress_boost_velocity = 0
            self._progress_boost_offset = 0

        return True

    def _start_achievement_celebration(self, payload: dict[str, Any]) -> None:
        """Kick off a short animated celebration for unlocked achievements."""
        raw_ids = payload.get("achievements", [])
        achievement_ids = [str(achievement_id) for achievement_id in raw_ids] if isinstance(raw_ids, list) else []
        names = self._achievement_names(achievement_ids) or "New achievement"
        self._celebration_tier = self._celebration_tier_for_payload(payload)
        tier_caption = CELEBRATION_CAPTIONS[self._celebration_tier]
        self._celebration_message = f"{tier_caption} Achievement unlocked: {names}"
        celebration_ticks, boost_ticks, boost_velocity = self._boost_profile_for_tier(self._celebration_tier)
        self._celebration_ticks_remaining = celebration_ticks
        self._celebration_frame = 0
        self._stop_celebration_animation()
        self._celebration_ticks_remaining = celebration_ticks
        self._progress_boost_ticks_remaining = boost_ticks
        self._progress_boost_velocity = boost_velocity

        self.query_one("#achievement-progress", Label).update(self._render_celebration_progress())
        stats_strip = self.query_one(".stats-strip", Horizontal)
        stats_strip.styles.animate("opacity", 0.78, duration=0.12, easing="out_cubic")
        stats_strip.styles.animate("opacity", 1.0, duration=0.40, delay=0.12, easing="in_out_cubic")
        self._start_fireworks_burst(self._celebration_tier)

        self._celebration_timer = self.set_interval(0.12, self._advance_celebration_frame)

    def _start_manual_fireworks_celebration(self) -> None:
        """Run fireworks animation on demand without requiring an achievement."""
        solved = max(0, int(self.engine.session.problems_solved))
        if solved >= 25:
            tier = 3
        elif solved >= 10:
            tier = 2
        else:
            tier = 1

        self._celebration_tier = tier
        self._celebration_message = "Fireworks on demand!"
        celebration_ticks, boost_ticks, boost_velocity = self._boost_profile_for_tier(tier)
        self._stop_celebration_animation()
        self._celebration_ticks_remaining = celebration_ticks
        self._celebration_frame = 0
        self._progress_boost_ticks_remaining = boost_ticks
        self._progress_boost_velocity = boost_velocity

        self.query_one("#achievement-progress", Label).update(self._render_celebration_progress())
        stats_strip = self.query_one(".stats-strip", Horizontal)
        stats_strip.styles.animate("opacity", 0.82, duration=0.10, easing="out_cubic")
        stats_strip.styles.animate("opacity", 1.0, duration=0.35, delay=0.10, easing="in_out_cubic")
        self._start_fireworks_burst(tier)

        self._celebration_timer = self.set_interval(0.12, self._advance_celebration_frame)

    def _advance_celebration_frame(self) -> None:
        """Advance celebration animation frame and restore normal stats when finished."""
        self._advance_progress_boost()

        if self._celebration_ticks_remaining > 0:
            self._celebration_ticks_remaining -= 1
            self._celebration_frame += max(1, self._celebration_tier)

        if self._celebration_ticks_remaining <= 0 and self._progress_boost_ticks_remaining <= 0:
            self._stop_celebration_animation()
            self._update_stats()
            return

        if self._celebration_ticks_remaining > 0:
            self.query_one("#achievement-progress", Label).update(self._render_celebration_progress())
        else:
            self.query_one("#achievement-progress", Label).update(
                self._render_achievement_progress(self.engine.session.problems_solved)
            )

    @staticmethod
    def _blend_rgb(base: tuple[int, int, int], target: tuple[int, int, int], target_ratio: float) -> tuple[int, int, int]:
        """Blend two RGB colors by ratio."""
        ratio = max(0.0, min(1.0, target_ratio))
        return tuple(
            int(round((base[index] * (1.0 - ratio)) + (target[index] * ratio)))
            for index in range(3)
        )

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        """Convert RGB triplet to CSS hex color."""
        red, green, blue = rgb
        return f"#{red:02x}{green:02x}{blue:02x}"

    @staticmethod
    def _text_color_for_background(rgb: tuple[int, int, int]) -> str:
        """Choose readable foreground color for a background."""
        red, green, blue = rgb
        luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
        return "#101418" if luminance > 160 else "#f8fbff"

    def _apply_theme_color(self, color_name: str) -> None:
        """Retheme the app around a recognized color token."""
        try:
            parsed_color = rich_color.Color.parse(color_name)
        except rich_color.ColorParseError:
            return

        true_color = parsed_color.get_truecolor()
        accent_rgb = (true_color.red, true_color.green, true_color.blue)

        background_rgb = self._blend_rgb(accent_rgb, (8, 10, 18), 0.84)
        surface_rgb = self._blend_rgb(accent_rgb, (18, 22, 34), 0.72)
        history_rgb = self._blend_rgb(accent_rgb, (10, 14, 24), 0.78)
        border_rgb = self._blend_rgb(accent_rgb, (245, 247, 255), 0.18)
        accent_text_rgb = self._blend_rgb(accent_rgb, (255, 255, 255), 0.22)

        background_hex = self._rgb_to_hex(background_rgb)
        surface_hex = self._rgb_to_hex(surface_rgb)
        history_hex = self._rgb_to_hex(history_rgb)
        border_hex = self._rgb_to_hex(border_rgb)
        accent_hex = self._rgb_to_hex(accent_text_rgb)
        text_hex = self._text_color_for_background(background_rgb)

        self.styles.background = background_hex
        self.styles.color = text_hex

        history_container = self.query_one(".history-container", Vertical)
        stats_strip = self.query_one(".stats-strip", Horizontal)
        input_container = self.query_one(".input-container", Horizontal)
        history = self.query_one("#history", TextArea)
        input_widget = self.query_one("#input", Input)

        history_container.styles.background = surface_hex
        history_container.styles.border = ("solid", border_hex)
        stats_strip.styles.background = surface_hex
        stats_strip.styles.border = ("solid", border_hex)
        input_container.styles.background = surface_hex

        history.styles.background = history_hex
        history.styles.color = text_hex
        input_widget.styles.background = history_hex
        input_widget.styles.color = text_hex
        input_widget.styles.border = ("solid", border_hex)

        for node in self.query(".stats-strip .stat-item"):
            if isinstance(node, Label):
                node.styles.background = "transparent"
                node.styles.color = text_hex

        for node in self.query(".title"):
            if isinstance(node, Label):
                node.styles.color = accent_hex

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
            line += "\nTheme shifted to match your color."
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
                    solved_quiz = content.get("quiz")
                    solved_question = ""
                    if isinstance(solved_quiz, dict):
                        solved_question = str(solved_quiz.get("question", "")).strip()
                    if not solved_question:
                        solved_question = str(content.get("question", "")).strip()
                    solved_answer = content.get("answer")
                    lines = []
                    if solved_question and solved_answer is not None:
                        lines.append(f"Correct, {solved_question} = {solved_answer}!")
                    elif solved_answer is not None:
                        lines.append(f"Correct! {solved_answer}")
                    else:
                        lines.append("Correct!")
                    if content.get("streak", 0) > 1:
                        lines.append(f"Streak: {content.get('streak', 0)}")
                    next_quiz = content.get("next_quiz")
                    if isinstance(next_quiz, dict) and next_quiz.get("question"):
                        lines.append(f"\n\nNext: {next_quiz['question']}")
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

        if response_type == ResponseType.ACHIEVEMENT:
            achievement_ids = content.get("achievements", [])
            names = self._achievement_names([str(achievement_id) for achievement_id in achievement_ids])
            if not names:
                names = "New achievement"
            line = f"🏆 Achievement unlocked: {names}"
            if content.get("total_solved") is not None:
                line += f"\nTotal solved: {content.get('total_solved')}"
            return line

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

        if normalized_input in FIREWORKS_INPUTS:
            history = self.query_one("#history", TextArea)
            history.insert(
                f"> {input_text}\nBoom! Fireworks celebration launched.\n\n",
                history.document.end,
            )
            history.scroll_end(animate=False)
            self._start_manual_fireworks_celebration()
            event.input.value = ""
            save_persisted_session(self.engine.session)
            return

        if normalized_input == "help":
            self.action_toggle_help_panel()
            event.input.value = ""
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
            if current.type == ResponseType.COLOR and isinstance(current.content, dict):
                color_name = str(current.content.get("color") or current.content.get("name") or "").strip()
                if color_name:
                    self._apply_theme_color(color_name)

            if current.type == ResponseType.ACHIEVEMENT and isinstance(current.content, dict):
                self._start_achievement_celebration(current.content)

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
        self._stop_celebration_animation()
        self._clear_fireworks_burst()
        save_persisted_session(self.engine.session)
        self.exit()

    def action_toggle_help_panel(self) -> None:
        """Toggle the key/help panel."""
        try:
            self.screen.query_one(HelpPanel)
        except NoMatches:
            self.action_show_help_panel()
            return
        self.action_hide_help_panel()

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
