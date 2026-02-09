"""Tests for persisted interactive session storage."""

from __future__ import annotations

from pathlib import Path

import pytest

import kidshell.core.config as config_module
from kidshell.core.models import Session
from kidshell.core.session_store import get_session_state_path, load_persisted_session, save_persisted_session


@pytest.fixture
def isolated_kidshell_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate config/session paths per test."""
    monkeypatch.setenv("KIDSHELL_HOME", str(tmp_path / ".kidshell"))
    config_module._config_manager = None
    yield
    config_module._config_manager = None


def test_session_store_roundtrip(isolated_kidshell_home):
    """Persisted session should reload with key multi-turn state intact."""
    session = Session()
    session.problems_solved = 3
    session.current_streak = 2
    session.current_quiz = {"id": "q1", "question": "2 + 2", "answer": 4}
    session.quiz_attempts = {"q1": 1}
    session.math_env["last_number"] = 42

    assert save_persisted_session(session) is True
    assert get_session_state_path().exists()

    restored = load_persisted_session()
    assert restored is not None
    assert restored.problems_solved == 3
    assert restored.current_streak == 2
    assert restored.current_quiz is not None
    assert restored.current_quiz["id"] == "q1"
    assert restored.quiz_attempts["q1"] == 1
    assert restored.math_env["last_number"] == 42


def test_session_store_returns_none_on_invalid_json(isolated_kidshell_home):
    """Invalid persisted payload should fail closed without crashing startup."""
    state_path = get_session_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{bad json", encoding="utf-8")

    assert load_persisted_session() is None
