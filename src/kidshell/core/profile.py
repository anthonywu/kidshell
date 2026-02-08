"""Profile onboarding and birthday math for personalized KidShell greetings."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MIN_BIRTH_YEAR = 1900
MAX_NAME_LENGTH = 40

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .'-]{0,39}$")
_YEAR_PATTERN = re.compile(r"^\d{4}$")
_FULL_DATE_PATTERN = re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$")
_MONTH_DAY_PATTERN = re.compile(r"^\d{1,2}[-/.]\d{1,2}$")


@dataclass(frozen=True)
class ChildProfile:
    """Persisted child profile used for startup greetings."""

    name: str
    birth_year: int
    birthday: str | None = None


def sanitize_name(raw_name: str) -> str:
    """Normalize and validate names before persisting/echoing in terminal output."""
    # Drop control characters so untrusted profile text cannot inject terminal escapes.
    printable_only = "".join(ch for ch in raw_name if ch.isprintable() and ch not in "\r\n\t")
    collapsed = " ".join(printable_only.strip().split())
    trimmed = collapsed[:MAX_NAME_LENGTH].rstrip()
    if not trimmed or not _NAME_PATTERN.fullmatch(trimmed):
        return ""
    return trimmed


def _validate_birth_year(year: int, today: date) -> int:
    if not (MIN_BIRTH_YEAR <= year <= today.year):
        raise ValueError(f"Birth year must be between {MIN_BIRTH_YEAR} and {today.year}.")
    return year


def parse_birth_value(raw_value: str, today: date | None = None) -> tuple[int, date | None]:
    """Parse either YYYY or YYYY-MM-DD input into validated birth data."""
    today_value = today or date.today()
    normalized = re.sub(r"[/.]", "-", raw_value.strip())

    if _YEAR_PATTERN.fullmatch(normalized):
        return _validate_birth_year(int(normalized), today_value), None

    if _FULL_DATE_PATTERN.fullmatch(normalized):
        year_str, month_str, day_str = normalized.split("-")
        year = _validate_birth_year(int(year_str), today_value)
        try:
            birthday = date(year, int(month_str), int(day_str))
        except ValueError as exc:
            raise ValueError("Birthday must be a real calendar date.") from exc
        if birthday > today_value:
            raise ValueError("Birthday cannot be in the future.")
        return year, birthday

    raise ValueError("Enter birth year as YYYY or full birthday as YYYY-MM-DD.")


def parse_month_day_value(raw_value: str, birth_year: int, today: date | None = None) -> date:
    """Parse MM-DD style input into a concrete birth date using known birth year."""
    today_value = today or date.today()
    normalized = re.sub(r"[/.]", "-", raw_value.strip())
    if not _MONTH_DAY_PATTERN.fullmatch(normalized):
        raise ValueError("Enter month/day as MM-DD.")

    month_str, day_str = normalized.split("-")
    try:
        birthday = date(birth_year, int(month_str), int(day_str))
    except ValueError as exc:
        raise ValueError("Month/day must be a real calendar date.") from exc

    if birthday > today_value:
        raise ValueError("Birthday cannot be in the future.")
    return birthday


def load_profile(profile_path: Path, today: date | None = None) -> ChildProfile | None:
    """Load and validate a persisted profile file."""
    if not profile_path.exists():
        return None

    today_value = today or date.today()
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Treat malformed/unreadable profile data as absent so startup can recover cleanly.
        return None

    if not isinstance(data, dict):
        return None

    name = sanitize_name(str(data.get("name", "")))
    if not name:
        return None

    birthday_value = data.get("birthday")
    if isinstance(birthday_value, str) and birthday_value.strip():
        try:
            parsed_year, parsed_birthday = parse_birth_value(birthday_value, today_value)
        except ValueError:
            return None
        if parsed_birthday is None:
            return None
        return ChildProfile(name=name, birth_year=parsed_year, birthday=parsed_birthday.isoformat())

    birth_year_value = data.get("birth_year")
    if not isinstance(birth_year_value, (int, str)):
        # Reject non-scalar JSON values so profile data cannot smuggle structured objects.
        return None
    try:
        birth_year = _validate_birth_year(int(birth_year_value), today_value)
    except (TypeError, ValueError):
        return None

    return ChildProfile(name=name, birth_year=birth_year)


def save_profile(profile_path: Path, profile: ChildProfile) -> None:
    """Persist profile atomically so interrupted writes do not corrupt startup state."""
    payload = {
        "name": profile.name,
        "birth_year": profile.birth_year,
        **({"birthday": profile.birthday} if profile.birthday else {}),
    }

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = profile_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(profile_path)


def calculate_age(profile: ChildProfile, today: date | None = None) -> int:
    """Calculate current age in whole years."""
    today_value = today or date.today()

    if profile.birthday:
        birthday = date.fromisoformat(profile.birthday)
        age = today_value.year - birthday.year
        if (today_value.month, today_value.day) < (birthday.month, birthday.day):
            age -= 1
        return max(age, 0)

    return max(today_value.year - profile.birth_year, 0)


def _birthday_for_year(month: int, day: int, year: int) -> date:
    """Build birthday for a target year, including leap-day fallback."""
    try:
        return date(year, month, day)
    except ValueError as exc:
        if month == 2 and day == 29:
            # Keep leap-day birthdays usable in non-leap years without crashing startup.
            return date(year, 2, 28)
        raise ValueError("Birthday must be a real calendar date.") from exc


def next_birthday_details(profile: ChildProfile, today: date | None = None) -> tuple[int, int] | None:
    """Return `(days_until_next_birthday, next_age)` when full birthday is available."""
    if not profile.birthday:
        return None

    today_value = today or date.today()
    birthday = date.fromisoformat(profile.birthday)
    age_now = calculate_age(profile, today_value)

    this_year_birthday = _birthday_for_year(birthday.month, birthday.day, today_value.year)
    if this_year_birthday < today_value:
        next_birthday = _birthday_for_year(birthday.month, birthday.day, today_value.year + 1)
    else:
        next_birthday = this_year_birthday

    days_until = (next_birthday - today_value).days
    next_age = age_now if days_until == 0 else age_now + 1
    return days_until, next_age


def onboarding_intro_lines() -> list[str]:
    """Static onboarding text shown once before collecting profile info."""
    return [
        "Welcome to KidShell! Let's set up your profile.",
        "This helps me greet you by name and celebrate your birthday countdown.",
    ]
