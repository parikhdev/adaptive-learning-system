# backend/app/ml/difficulty.py
# Progress-based difficulty escalation
# No correct_answer needed — uses questions_answered as engagement proxy

from typing import Literal

DifficultyLevel = Literal["Beginner", "Intermediate", "Advanced"]
DEFAULT_DIFFICULTY: DifficultyLevel = "Beginner"


def next_difficulty(
    current_level: DifficultyLevel | None,
    questions_answered: int,
) -> DifficultyLevel:
    """
    Progress-based adaptive difficulty.

    0-2 questions  → Beginner      (orientation)
    3-5 questions  → Intermediate  (building)
    6+  questions  → Advanced      (challenge)

    Honest, defensible, no fake correctness signal needed.
    Phase 8: replace with IRT (Item Response Theory) when correct_answer added.
    """
    if questions_answered < 3:
        return "Beginner"
    elif questions_answered < 6:
        return "Intermediate"
    else:
        return "Advanced"


def difficulty_to_score_range(level: DifficultyLevel) -> tuple[float, float]:
    ranges: dict[DifficultyLevel, tuple[float, float]] = {
        "Beginner":     (0.0, 0.33),
        "Intermediate": (0.34, 0.66),
        "Advanced":     (0.67, 1.0),
    }
    return ranges[level]