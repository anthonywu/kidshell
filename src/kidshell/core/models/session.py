"""
Session model for tracking user state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class Activity:
    """Record of a user activity."""

    timestamp: datetime
    type: str
    input: str
    output: Any
    success: bool = True

    def to_dict(self) -> dict:
        """Serialize activity to dict."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "input": self.input,
            "output": str(self.output),
            "success": self.success,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Activity":
        """Deserialize activity from dict."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=data["type"],
            input=data["input"],
            output=data["output"],
            success=data.get("success", True),
        )


@dataclass
class Session:
    """User session state - platform agnostic."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    math_env: dict[str, Any] = field(default_factory=dict)
    symbols_env: dict[str, Any] = field(default_factory=dict)
    achievements: list[str] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    problems_solved: int = 0
    current_streak: int = 0
    current_quiz: dict | None = None
    quiz_attempts: dict[str, int] = field(default_factory=dict)
    pending_response: Any = None
    custom_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default math environment."""
        import math

        self.math_env.update(
            {
                "e": math.e,
                "pi": math.pi,
                "tau": math.tau,
                "last_number": 0,
            }
        )

        # Add scipy constants if available
        try:
            import scipy.constants

            self.math_env.update(
                {
                    "c": scipy.constants.c,
                    "g": scipy.constants.g,
                    "G": scipy.constants.G,
                    "h": scipy.constants.h,
                    "k": scipy.constants.k,
                }
            )
        except ImportError:
            pass

    def add_activity(self, activity_type: str, user_input: str, output: Any, success: bool = True):
        """Add an activity to the session."""
        self.activities.append(
            Activity(
                timestamp=datetime.now(),
                type=activity_type,
                input=user_input,
                output=output,
                success=success,
            )
        )

    def check_achievements(self) -> list[str]:
        """Check for new achievements based on current state."""
        new_achievements = []

        # First 5 problems
        if self.problems_solved >= 5 and "first_five" not in self.achievements:
            new_achievements.append("first_five")
            self.achievements.append("first_five")

        # First 10 problems
        if self.problems_solved >= 10 and "first_ten" not in self.achievements:
            new_achievements.append("first_ten")
            self.achievements.append("first_ten")

        # Streak achievements
        if self.current_streak >= 5 and "streak_5" not in self.achievements:
            new_achievements.append("streak_5")
            self.achievements.append("streak_5")

        if self.current_streak >= 10 and "streak_10" not in self.achievements:
            new_achievements.append("streak_10")
            self.achievements.append("streak_10")

        # Math master
        if self.problems_solved >= 25 and "math_master" not in self.achievements:
            new_achievements.append("math_master")
            self.achievements.append("math_master")

        return new_achievements

    def get_stats(self) -> dict:
        """Get session statistics."""
        total_activities = len(self.activities)
        successful = sum(1 for a in self.activities if a.success)

        return {
            "session_id": self.session_id,
            "duration": (datetime.now() - self.created_at).total_seconds(),
            "total_activities": total_activities,
            "successful_activities": successful,
            "success_rate": successful / total_activities if total_activities > 0 else 0,
            "problems_solved": self.problems_solved,
            "current_streak": self.current_streak,
            "achievements_earned": len(self.achievements),
        }

    def to_dict(self) -> dict:
        """Serialize session to dict for persistence."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "math_env": {
                k: v for k, v in self.math_env.items() if k not in ["e", "pi", "tau", "c", "g", "G", "h", "k"]
            },
            "symbols_env": {k: str(v) for k, v in self.symbols_env.items()},
            "achievements": self.achievements,
            "activities": [a.to_dict() for a in self.activities[-100:]],  # Keep last 100
            "problems_solved": self.problems_solved,
            "current_streak": self.current_streak,
            "current_quiz": self.current_quiz,
            "quiz_attempts": self.quiz_attempts,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Deserialize session from dict."""
        session = cls()
        session.session_id = data["session_id"]
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.math_env.update(data.get("math_env", {}))

        # Restore symbols (as strings for now)
        session.symbols_env = data.get("symbols_env", {})

        session.achievements = data.get("achievements", [])
        session.activities = [Activity.from_dict(a) for a in data.get("activities", [])]
        session.problems_solved = data.get("problems_solved", 0)
        session.current_streak = data.get("current_streak", 0)
        session.current_quiz = data.get("current_quiz")
        session.quiz_attempts = data.get("quiz_attempts", {})
        session.custom_data = data.get("custom_data", {})

        return session
