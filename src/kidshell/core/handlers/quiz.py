"""
Quiz handler for answering quiz questions.
"""

import re

from kidshell.core.handlers.base import Handler
from kidshell.core.handlers.number_tree import build_number_tree_content, can_build_number_tree
from kidshell.core.models import Session
from kidshell.core.services import QuizService
from kidshell.core.types import Response, ResponseType


class QuizHandler(Handler):
    """Handle quiz answer checking."""

    ANSWER_PATTERN = re.compile(r"^[+-]?\d+(?:\.\d+)?$")

    def can_handle(self, input_text: str, session: Session) -> bool:
        """Check if there's an active quiz and input could be an answer."""
        if session.current_quiz is None:
            return False

        # Only handle if input looks like a quiz answer:
        # - Pure number
        # - Single word that's not a known command/color/emoji trigger
        # - Or explicitly "answer: X"

        # Allow other handlers to take precedence for their specific patterns
        # Check if it's a plain numeric answer (avoid matching loop syntax like 0...10...1).
        if self.ANSWER_PATTERN.fullmatch(input_text):
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
        if quiz is None:
            return Response(
                type=ResponseType.ERROR,
                content="No active quiz.",
                metadata={"input": input_text},
            )

        # Extract answer if using explicit format
        answer = input_text
        if input_text.startswith("answer:"):
            answer = input_text[7:].strip()
        elif input_text.startswith("ans:"):
            answer = input_text[4:].strip()
        user_answer_text = answer if isinstance(answer, str) else str(answer)

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
                    "question": quiz.get("question"),
                    "answer": quiz["answer"],
                    "quiz": quiz,
                    "next_quiz": next_quiz,
                    "streak": session.current_streak,
                    "total_solved": session.problems_solved,
                },
                metadata={"quiz_id": quiz_id},
            )
        # Record failure
        session.add_activity("quiz", input_text, f"Expected: {quiz['answer']}", success=False)
        session.current_streak = 0

        # Keep coaching encouraging and optionally provide number exploration.
        attempts = session.quiz_attempts[quiz_id]
        clue = None
        if attempts >= 3:
            correct_answer = quiz["answer"]
            if isinstance(correct_answer, int):
                if correct_answer < 10:
                    clue = "The answer is less than 10."
                elif correct_answer < 50:
                    clue = (
                        f"The answer is between {(correct_answer // 10) * 10} and "
                        f"{((correct_answer // 10) + 1) * 10}."
                    )
                else:
                    clue = f"The answer starts with {str(correct_answer)[0]}."

        number_facts = None
        numeric_answer = user_answer_text.strip()
        if can_build_number_tree(numeric_answer):
            number_facts = build_number_tree_content(int(numeric_answer))

        if clue:
            hint = f"Great persistence! Helpful clue: {clue}"
        else:
            hint = "Great attempt! Keep going on this one."

        encouragement = "Nice thinking."
        if number_facts is not None:
            encouragement = f"Nice thinking with {number_facts['number']}! Let's explore it while we keep going."

        return Response(
            type=ResponseType.QUIZ,
            content={
                "correct": False,
                "user_answer": input_text,
                "hint": hint,
                "encouragement": encouragement,
                "quiz": quiz,
                "attempts": attempts,
                "number_facts": number_facts,
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
