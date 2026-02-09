"""Persistence helpers for restoring the latest interactive session."""

from __future__ import annotations

import json
from pathlib import Path

from kidshell.core.config import get_config_manager
from kidshell.core.models import Session

SESSION_STATE_FILENAME = "session_state.json"


def get_session_state_path() -> Path:
    """Return location of persisted session state."""
    return get_config_manager().config_dir / SESSION_STATE_FILENAME


def load_persisted_session() -> Session | None:
    """Load previously persisted session, if available."""
    path = get_session_state_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return Session.from_dict(payload)
    except Exception:
        return None


def save_persisted_session(session: Session) -> bool:
    """Persist current session state atomically."""
    path = get_session_state_path()
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(
            json.dumps(session.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(path)
        return True
    except OSError:
        return False
