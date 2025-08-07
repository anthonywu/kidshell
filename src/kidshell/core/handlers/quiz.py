"""
Quiz handler for answering quiz questions.
"""

from kidshell.core.handlers.base import Handler
from kidshell.core.models import Session
from kidshell.core.services import QuizService
from kidshell.core.types import Response, ResponseType


class QuizHandler(Handler):
    """Handle quiz answer checking."""

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if there's an active quiz and input could be an answer."""
        if session.current_quiz is None:
            return False

        # Only handle if input looks like a quiz answer:
        # - Pure number
        # - Single word that's not a known command/color/emoji trigger
        # - Or explicitly "answer: X"

        # Allow other handlers to take precedence for their specific patterns
        # Check if it's a pure number answer
        if input_text.replace("-", "").replace(".", "").isdigit():
            return True

        # Check for explicit answer format
        if input_text.startswith(("answer:", "ans:")):
            return True

        # Don't capture math expressions, colors, emojis, etc.
        # Let those handlers work even during quiz
        return False

    def handle(self, input_text: str, session: Session) -> Response:
        """Check quiz answer."""

        quiz = session.current_quiz

        # Extract answer if using explicit format
        answer = input_text
        if input_text.startswith("answer:"):
            answer = input_text[7:].strip()
        elif input_text.startswith("ans:"):
            answer = input_text[4:].strip()

        is_correct = QuizService.check_answer(quiz, answer)

        # Track attempts
        quiz_id = quiz.get("id", "unknown")
        session.quiz_attempts[quiz_id] = session.quiz_attempts.get(quiz_id, 0) + 1

        if is_correct:
            session.problems_solved += 1
            session.current_streak += 1
            session.current_quiz = None

            # Record success
            session.add_activity("quiz", input_text, quiz["answer"], success=True)

            # Generate next quiz
            next_quiz = QuizService.generate_math_question(
                difficulty=self._get_difficulty_level(session),
            )
            session.current_quiz = next_quiz

            return Response(
                type=ResponseType.QUIZ,
                content={
                    "correct": True,
                    "answer": quiz["answer"],
                    "next_quiz": next_quiz,
                    "streak": session.current_streak,
                    "total_solved": session.problems_solved,
                },
                metadata={"quiz_id": quiz_id},
            )
        # Record failure
        session.add_activity("quiz", input_text, f"Expected: {quiz['answer']}", success=False)
        session.current_streak = 0

        # Provide hint after 3 attempts
        attempts = session.quiz_attempts[quiz_id]
        hint = None
        if attempts >= 3:
            answer = quiz["answer"]
            if isinstance(answer, int):
                if answer < 10:
                    hint = "The answer is less than 10"
                elif answer < 50:
                    hint = f"The answer is between {(answer // 10) * 10} and {((answer // 10) + 1) * 10}"
                else:
                    hint = f"The answer starts with {str(answer)[0]}"

        return Response(
            type=ResponseType.QUIZ,
            content={
                "correct": False,
                "user_answer": input_text,
                "hint": hint or f"Try again! {input_text} is not correct",
                "quiz": quiz,
                "attempts": attempts,
            },
            metadata={"quiz_id": quiz_id},
        )

    def _get_difficulty_level(self, session: Session) -> int:
        """Determine difficulty based on problems solved."""
        if session.problems_solved < 5:
            return 1
        if session.problems_solved < 15:
            return 2
        if session.problems_solved < 30:
            return 3
        return 4
