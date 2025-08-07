"""
Quiz generation and validation service.
"""

import random
from uuid import uuid4

from kidshell.core.safe_math import SafeMathError, safe_math_operation


class QuizService:
    """Generate and validate quiz questions."""

    @staticmethod
    def generate_math_question(difficulty: int = 1) -> dict:
        """
        Generate a math question based on difficulty.

        Args:
            difficulty: 1-4 (easy to hard)

        Returns:
            Quiz dictionary with question, answer, etc.
        """
        quiz_id = str(uuid4())[:8]

        if difficulty == 1:
            # Easy: addition/subtraction with small numbers
            x = random.randint(1, 10)
            y = random.randint(1, 10)
            op = random.choice(["+", "-"])

            if op == "-":
                # Ensure positive result
                x, y = max(x, y), min(x, y)

        elif difficulty == 2:
            # Medium: larger numbers, multiplication
            x = random.randint(1, 20)
            y = random.randint(1, 20)
            op = random.choice(["+", "-", "*"])

            if op == "-":
                x, y = max(x, y), min(x, y)
            elif op == "*":
                # Keep multiplication manageable
                x = random.randint(1, 10)
                y = random.randint(1, 10)

        elif difficulty == 3:
            # Hard: division, larger multiplication
            op = random.choice(["+", "-", "*", "/"])

            if op == "/":
                # Create division that results in whole number
                y = random.randint(1, 10)
                result = random.randint(1, 10)
                x = y * result
            else:
                x = random.randint(10, 50)
                y = random.randint(1, 20)
                if op == "-":
                    x, y = max(x, y), min(x, y)

        else:  # difficulty >= 4
            # Expert: complex operations
            op = random.choice(["+", "-", "*", "/"])
            x = random.randint(10, 100)
            y = random.randint(10, 50)

            if op == "-":
                x, y = max(x, y), min(x, y)
            elif op == "/":
                # Ensure clean division
                y = random.randint(2, 12)
                result = random.randint(2, 20)
                x = y * result

        # Calculate answer safely
        try:
            if op == "/":
                answer = x // y  # Integer division
                question = f"{x} ÷ {y}"
            else:
                # Use safe math operation instead of eval
                answer = safe_math_operation(x, op, y)
                # Pretty print operators
                pretty_op = {"*": "×", "-": "−"}.get(op, op)
                question = f"{x} {pretty_op} {y}"
        except SafeMathError:
            # Fallback to simpler question if calculation fails
            return QuizService.generate_math_question(difficulty=1)

        # Ensure integer result for division
        if isinstance(answer, float) and answer.is_integer():
            answer = int(answer)

        return {
            "id": quiz_id,
            "question": question,
            "answer": answer,
            "difficulty": difficulty,
            "type": "math",
            "operation": op,
            "operands": [x, y],
        }

    @staticmethod
    def check_answer(quiz: dict, user_answer: str) -> bool:
        """
        Check if user answer is correct.

        Args:
            quiz: Quiz dictionary
            user_answer: User's answer as string

        Returns:
            True if correct, False otherwise
        """
        try:
            # Clean up answer
            user_answer = user_answer.strip().lower()

            # Remove common mistakes
            user_answer = user_answer.replace(",", "")
            user_answer = user_answer.replace(" ", "")

            # Try to convert to number
            if "." in user_answer:
                user_value = float(user_answer)
            else:
                user_value = int(user_answer)

            correct_answer = quiz["answer"]

            # Check equality (with tolerance for floats)
            if isinstance(correct_answer, float) or isinstance(user_value, float):
                return abs(user_value - correct_answer) < 0.001
            return user_value == correct_answer

        except (ValueError, TypeError):
            # Can't parse answer
            return False

    @staticmethod
    def generate_pattern_question() -> dict:
        """Generate a pattern recognition question."""
        patterns = [
            {
                "sequence": [2, 4, 6, 8],
                "answer": 10,
                "rule": "add 2",
            },
            {
                "sequence": [5, 10, 15, 20],
                "answer": 25,
                "rule": "add 5",
            },
            {
                "sequence": [1, 2, 4, 8],
                "answer": 16,
                "rule": "multiply by 2",
            },
            {
                "sequence": [10, 9, 8, 7],
                "answer": 6,
                "rule": "subtract 1",
            },
        ]

        pattern = random.choice(patterns)
        quiz_id = str(uuid4())[:8]

        return {
            "id": quiz_id,
            "question": f"What comes next? {', '.join(map(str, pattern['sequence']))}, ?",
            "answer": pattern["answer"],
            "type": "pattern",
            "sequence": pattern["sequence"],
            "rule": pattern["rule"],
        }
