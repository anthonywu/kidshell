"""
Achievement definitions and tracking.
"""

from dataclasses import dataclass
from enum import Enum


class AchievementType(Enum):
    """Types of achievements."""

    PROBLEMS = "problems"
    STREAK = "streak"
    MASTERY = "mastery"
    EXPLORATION = "exploration"
    SPEED = "speed"


@dataclass
class Achievement:
    """Achievement definition."""

    id: str
    name: str
    description: str
    type: AchievementType
    icon: str
    requirement: int
    stars: int = 1

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "icon": self.icon,
            "requirement": self.requirement,
            "stars": self.stars,
        }


# Achievement definitions
ACHIEVEMENTS = {
    "first_five": Achievement(
        id="first_five",
        name="First Steps",
        description="Solve your first 5 problems",
        type=AchievementType.PROBLEMS,
        icon="👣",
        requirement=5,
        stars=1,
    ),
    "first_ten": Achievement(
        id="first_ten",
        name="Getting Started",
        description="Solve 10 problems",
        type=AchievementType.PROBLEMS,
        icon="🚀",
        requirement=10,
        stars=2,
    ),
    "math_master": Achievement(
        id="math_master",
        name="Math Master",
        description="Solve 25 problems",
        type=AchievementType.MASTERY,
        icon="🧮",
        requirement=25,
        stars=3,
    ),
    "streak_5": Achievement(
        id="streak_5",
        name="On Fire",
        description="Get 5 correct answers in a row",
        type=AchievementType.STREAK,
        icon="🔥",
        requirement=5,
        stars=2,
    ),
    "streak_10": Achievement(
        id="streak_10",
        name="Unstoppable",
        description="Get 10 correct answers in a row",
        type=AchievementType.STREAK,
        icon="⚡",
        requirement=10,
        stars=3,
    ),
    "explorer": Achievement(
        id="explorer",
        name="Explorer",
        description="Try all different features",
        type=AchievementType.EXPLORATION,
        icon="🗺️",
        requirement=5,
        stars=2,
    ),
    "speed_demon": Achievement(
        id="speed_demon",
        name="Speed Demon",
        description="Solve 5 problems in under a minute",
        type=AchievementType.SPEED,
        icon="⚡",
        requirement=5,
        stars=3,
    ),
}


def get_achievement(achievement_id: str) -> Achievement | None:
    """Get achievement by ID."""
    return ACHIEVEMENTS.get(achievement_id)


def get_all_achievements() -> list[Achievement]:
    """Get all available achievements."""
    return list(ACHIEVEMENTS.values())


def get_achievements_by_type(achievement_type: AchievementType) -> list[Achievement]:
    """Get achievements of a specific type."""
    return [a for a in ACHIEVEMENTS.values() if a.type == achievement_type]
