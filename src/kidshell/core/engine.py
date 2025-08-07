"""
Core KidShell engine - processes input and returns structured responses.
Platform-agnostic, no UI dependencies.
"""

from kidshell.core.handlers import (
    ColorHandler,
    EmojiHandler,
    LoopHandler,
    MathHandler,
    NumberTreeHandler,
    QuizHandler,
    SymbolHandler,
)
from kidshell.core.models import Session
from kidshell.core.types import Response, ResponseType


class KidShellEngine:
    """Core processing engine - no UI dependencies."""

    def __init__(self, session: Session | None = None):
        """Initialize the engine with optional session."""
        self.session = session or Session()
        self.handlers = self._initialize_handlers()

    def _initialize_handlers(self) -> list:
        """Initialize all input handlers in priority order."""
        return [
            # Quiz answers (should check first when quiz is active)
            QuizHandler(),
            # Number properties tree (pure number input)
            NumberTreeHandler(),
            # Math expressions
            MathHandler(),
            # Symbols and algebra
            SymbolHandler(),
            # Loops (e.g., "0...10...1")
            LoopHandler(),
            # Colors
            ColorHandler(),
            # Emojis
            EmojiHandler(),
        ]

    def process_input(self, user_input: str) -> Response:
        """
        Process user input and return structured response.

        Args:
            user_input: Raw user input string

        Returns:
            Response object with type and content
        """
        if not user_input:
            # Empty input - generate a quiz
            return self._generate_quiz()

        normalized = user_input.lower().strip()

        # Try each handler
        for handler in self.handlers:
            if handler.can_handle(normalized, self.session):
                try:
                    response = handler.handle(normalized, self.session)

                    # Check for achievements after successful handling
                    new_achievements = self.session.check_achievements()
                    if new_achievements:
                        # Return achievement notification
                        # (Next call will return the actual response)
                        self.session.pending_response = response
                        return Response(
                            type=ResponseType.ACHIEVEMENT,
                            content={
                                "achievements": new_achievements,
                                "total_solved": self.session.problems_solved,
                            },
                        )

                    return response

                except Exception as e:
                    return Response(
                        type=ResponseType.ERROR,
                        content=str(e),
                        metadata={"handler": handler.__class__.__name__},
                    )

        # No handler found
        return Response(
            type=ResponseType.TEXT,
            content="I don't understand that yet! Try a math problem or type a color name!",
            metadata={"input": normalized},
        )

    def _generate_quiz(self) -> Response:
        """Generate a new quiz question."""
        from .services import QuizService

        quiz = QuizService.generate_math_question(
            difficulty=self._get_difficulty_level(),
        )
        self.session.current_quiz = quiz

        return Response(
            type=ResponseType.QUIZ,
            content=quiz,
            metadata={"new_quiz": True},
        )

    def _get_difficulty_level(self) -> int:
        """Determine difficulty based on problems solved."""
        if self.session.problems_solved < 5:
            return 1
        if self.session.problems_solved < 15:
            return 2
        return 3

    def get_session_state(self) -> dict:
        """Get current session state for persistence."""
        return self.session.to_dict()

    def restore_session_state(self, state: dict):
        """Restore session from saved state."""
        self.session = Session.from_dict(state)

    def get_pending_response(self) -> Response | None:
        """Get any pending response (e.g., after achievement)."""
        if self.session.pending_response:
            response = self.session.pending_response
            self.session.pending_response = None
            return response
        return None
