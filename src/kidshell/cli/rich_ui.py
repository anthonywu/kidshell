"""
Rich UI enhancements for KidShell.
Provides visual feedback and engaging displays for children.
"""

import random
import time
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# Child-friendly spinner options
CHILD_FRIENDLY_SPINNERS = [
    "dots",  # Simple dots
    "dots2",  # Variant dots
    "star",  # Rotating star
    "balloon",  # Balloon animation
    "bounce",  # Bouncing dot
    "bouncingBall",  # Bouncing ball
    "arc",  # Arc rotation
    "circle",  # Circle animation
]


class KidShellRichUI:
    """Rich UI components for enhanced child interaction."""

    def __init__(self, console: Console | None = None):
        """Initialize the Rich UI components.

        Args:
            console: Optional Console instance. Creates new one if not provided.
        """
        self.console = console or Console(emoji=True, highlight=True, markup=True)

    def thinking_spinner(self, message: str = "Thinking", duration: float = 2.0) -> None:
        """Show an animated spinner while processing.

        Args:
            message: Message to display with spinner
            duration: How long to show the spinner
        """
        spinner_name = random.choice(CHILD_FRIENDLY_SPINNERS)

        with Live(
            Spinner(spinner_name, text=f"[yellow]{message}...[/yellow]"),
            refresh_per_second=10,
            transient=True,
            console=self.console,
        ):
            time.sleep(duration)

    def show_answer_panel(self, answer: Any, title: str = "Answer") -> None:
        """Display an answer in a colorful panel.

        Args:
            answer: The answer to display
            title: Title for the panel
        """
        content = Text(str(answer), style="bold green", justify="center")
        panel = Panel(
            content,
            title=f"✨ {title} ✨",
            subtitle="[dim]Great job![/dim]",
            border_style="bright_blue",
            expand=False,
            padding=(1, 3),
        )
        self.console.print(panel)

    def show_math_result(self, expression: str, result: Any) -> None:
        """Display a math calculation result in a panel.

        Args:
            expression: The math expression
            result: The calculation result
        """
        content = Text()
        content.append(f"{expression} = ", style="cyan")
        content.append(str(result), style="bold green")

        panel = Panel(
            Align.center(content),
            title="🎯 Math Answer",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_number_tree(self, number: int) -> None:
        """Display number properties in a tree structure.

        Args:
            number: The number to analyze
        """
        tree = Tree(f"[bold magenta]Number: {number}[/bold magenta]")

        # Factors branch
        factors_branch = tree.add("[cyan]Factors[/cyan]")
        factors = self._find_factors(number)
        if factors:
            for a, b in factors:
                factors_branch.add(f"[green]{a} × {b}[/green]")
        else:
            factors_branch.add("[yellow]Prime number![/yellow]")

        # Properties branch
        props_branch = tree.add("[yellow]Properties[/yellow]")

        # Even/Odd
        if number % 2 == 0:
            props_branch.add("[blue]Even number ✓[/blue]")
        else:
            props_branch.add("[orange]Odd number ✓[/orange]")

        # Divisibility checks
        if number % 3 == 0:
            props_branch.add("[green]Divisible by 3 ✓[/green]")
        if number % 5 == 0:
            props_branch.add("[purple]Divisible by 5 ✓[/purple]")
        if number % 10 == 0:
            props_branch.add("[red]Divisible by 10 ✓[/red]")

        # Operations branch
        ops_branch = tree.add("[red]Operations[/red]")
        ops_branch.add(f"[white]Square root: {number**0.5:.2f}[/white]")
        ops_branch.add(f"[white]Squared: {number**2}[/white]")
        ops_branch.add(f"[white]Doubled: {number * 2}[/white]")
        ops_branch.add(f"[white]Halved: {number / 2:.1f}[/white]")

        self.console.print(tree)

    def _find_factors(self, number: int) -> list[tuple[int, int]]:
        """Find all factor pairs of a number.

        Args:
            number: Number to factorize

        Returns:
            List of factor pairs
        """
        factors = []
        for i in range(1, int(number**0.5) + 1):
            if number % i == 0:
                factors.append((i, number // i))
        return factors

    def status_message(self, message: str, task_func=None, duration: float = 2.0) -> Any:
        """Show a status message during a long operation.

        Args:
            message: Status message to display
            task_func: Optional function to execute during status
            duration: Duration if no task_func provided

        Returns:
            Result from task_func if provided
        """
        spinner = random.choice(["dots", "star", "bouncingBall"])

        with self.console.status(
            f"[bold green]{message}[/bold green]",
            spinner=spinner,
        ):
            if task_func:
                result = task_func()
                return result
            time.sleep(duration)
            return None

    def show_emoji_emoji_panel(self, emoji: str, name: str) -> None:
        """Show an emoji with its name in a panel.

        Args:
            emoji: The emoji to display
            name: Name of the emojiqq
        """
        content = Align.center(
            f"{emoji}\n[bold cyan]{name}[/bold cyan]",
            vertical="middle",
        )
        panel = Panel(
            content,
            border_style="bright_magenta",
            padding=(1, 2),
            height=5,
        )
        self.console.print(panel)

    def show_achievement(self, title: str, message: str, stars: int = 1) -> None:
        """Display an achievement notification.

        Args:
            title: Achievement title
            message: Achievement message
            stars: Number of stars earned
        """
        star_display = "⭐" * stars

        content = Align.center(
            f"[bold yellow]{title}[/bold yellow]\n{message}\n\n{star_display}",
            vertical="middle",
        )

        panel = Panel(
            content,
            title="🏆 Achievement Unlocked!",
            border_style="gold1",
            style="on dark_green",
            padding=(1, 3),
            height=7,
        )
        self.console.print(panel)

    # Markdown Engagement Features

    def show_progress_table(self, activities: list[dict]) -> None:
        """Display a progress tracking table.

        Args:
            activities: List of activity dictionaries with keys:
                        'time', 'activity', 'score', 'stars'
        """
        table = Table(title="📊 Today's Progress")
        table.add_column("Time", style="cyan", width=8)
        table.add_column("Activity", style="yellow")
        table.add_column("Score", style="green", width=8)
        table.add_column("Stars", style="bright_yellow", width=10)

        for activity in activities:
            stars = "⭐" * activity.get("stars", 0)
            table.add_row(
                activity.get("time", ""),
                activity.get("activity", ""),
                activity.get("score", ""),
                stars,
            )

        self.console.print(table)

    def show_story_section(self, title: str, content: str, choices: list[str] | None = None) -> None:
        """Display a story section with optional choices.

        Args:
            title: Story chapter/section title
            content: Story content (supports markdown)
            choices: Optional list of choices for the reader
        """
        # Create markdown content
        md_content = f"# {title}\n\n{content}\n"

        if choices:
            md_content += "\n## Your Choices:\n"
            for i, choice in enumerate(choices, 1):
                md_content += f"{i}. **{choice}**\n"

        # Render markdown
        md = Markdown(md_content)
        panel = Panel(
            md,
            title="📚 Story Time",
            border_style="bright_cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_achievement_display(self, achievements: list[dict]) -> None:
        """Display achievements in an organized format.

        Args:
            achievements: List of achievement dicts with 'name', 'earned', 'icon'
        """
        earned = [a for a in achievements if a.get("earned", False)]
        locked = [a for a in achievements if not a.get("earned", False)]

        md_content = "# 🏆 Achievements\n\n"

        if earned:
            md_content += "## Earned ✅\n"
            for achievement in earned:
                icon = achievement.get("icon", "🏅")
                name = achievement.get("name", "Achievement")
                md_content += f"- {icon} **{name}**\n"

        if locked:
            md_content += "\n## Locked 🔒\n"
            for achievement in locked:
                name = achievement.get("name", "Achievement")
                md_content += f"- 🔒 _{name}_\n"

        md = Markdown(md_content)
        self.console.print(md)

    def show_learning_tip(self, tip: str, category: str = "Tip") -> None:
        """Display a learning tip with emoji and formatting.

        Args:
            tip: The tip content
            category: Category of the tip
        """
        emoji_map = {
            "Tip": "💡",
            "Hint": "🔍",
            "Warning": "⚠️",
            "Success": "✅",
            "Info": "ℹ️",
            "Math": "🔢",
            "Fun Fact": "🌟",
        }

        emoji = emoji_map.get(category, "💭")

        panel = Panel(
            f"[yellow]{tip}[/yellow]",
            title=f"{emoji} {category}",
            border_style="bright_yellow",
            padding=(1, 2),
        )
        self.console.print(panel)


# Convenience functions for standalone use


def create_rich_ui() -> KidShellRichUI:
    """Create a new Rich UI instance.

    Returns:
        KidShellRichUI instance
    """
    return KidShellRichUI()


def demo_rich_features():
    """Demonstrate all Rich UI features."""
    ui = create_rich_ui()

    ui.console.print("[bold cyan]Rich UI Features Demo[/bold cyan]\n")

    # 1. Animated spinner
    ui.console.print("1. Thinking spinner:")
    ui.thinking_spinner("Calculating", 1.5)
    ui.console.print("[green]✓ Done![/green]\n")

    # 2. Colorful panels
    ui.console.print("2. Answer panel:")
    ui.show_answer_panel(42, "The Ultimate Answer")
    ui.console.print()

    # 3. Tree display
    ui.console.print("3. Number properties tree:")
    ui.show_number_tree(12)
    ui.console.print()

    # 4. Status messages
    ui.console.print("4. Status message:")
    ui.status_message("Processing data", duration=0.5)
    ui.console.print("[green]✓ Complete![/green]\n")

    # 5. Progress tracking
    ui.console.print("5. Progress table:")
    activities = [
        {"time": "9:00", "activity": "Math Practice", "score": "10/10", "stars": 3},
        {"time": "9:30", "activity": "Color Quiz", "score": "8/10", "stars": 2},
        {"time": "10:00", "activity": "Counting", "score": "Done!", "stars": 3},
    ]
    ui.show_progress_table(activities)
    ui.console.print()

    # 6. Story section
    ui.console.print("6. Story with choices:")
    ui.show_story_section(
        "The Magic Door",
        "You find three colored doors: red, blue, and green.\nEach one glows with mysterious light.",
        ["Open the red door", "Open the blue door", "Open the green door"],
    )
    ui.console.print()

    # 7. Achievement display
    ui.console.print("7. Achievements:")
    achievements = [
        {"name": "First Steps", "earned": True, "icon": "👣"},
        {"name": "Math Master", "earned": True, "icon": "🧮"},
        {"name": "Speed Demon", "earned": False},
        {"name": "Perfect Score", "earned": False},
    ]
    ui.show_achievement_display(achievements)
    ui.console.print()

    # 8. Learning tip
    ui.console.print("8. Learning tip:")
    ui.show_learning_tip(
        "When adding numbers, you can count on your fingers to help!",
        "Math",
    )


if __name__ == "__main__":
    demo_rich_features()
