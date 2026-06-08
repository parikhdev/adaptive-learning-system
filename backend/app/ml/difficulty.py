# backend/app/ml/difficulty.py

from typing import Literal

DifficultyLevel = Literal["Beginner", "Intermediate", "Advanced"]
DifficultyMode  = Literal["adaptive", "fixed"]

DEFAULT_DIFFICULTY: DifficultyLevel = "Beginner"
DEFAULT_MODE: DifficultyMode = "adaptive"

_LEVELS = ["Beginner", "Intermediate", "Advanced"]


def next_difficulty(
    current_level: DifficultyLevel | None,
    questions_answered: int,
    mode: DifficultyMode = "adaptive",
    fixed_difficulty: DifficultyLevel | None = None,
) -> DifficultyLevel:
    """
    Return the difficulty level to use for the next question.

    FIXED mode (mode="fixed"):
        Always returns fixed_difficulty.
        Falls back to DEFAULT_DIFFICULTY if fixed_difficulty is None / invalid.

    ADAPTIVE mode (mode="adaptive"):
        Uses fixed_difficulty as the STARTING level, then escalates upward
        by one tier every 3 questions answered.

        Formula:
            start_index = index of fixed_difficulty in [B, I, A]
            steps       = questions_answered // 3
            result      = _LEVELS[min(start_index + steps, 2)]
    """
    # FIXED 
    if mode == "fixed":
        if fixed_difficulty in _LEVELS:
            return fixed_difficulty          # type: ignore[return-value]
        return DEFAULT_DIFFICULTY

    # ADAPTIVE 
    # Determine where to START escalation from
    if fixed_difficulty in _LEVELS:
        start_index = _LEVELS.index(fixed_difficulty)
    else:
        start_index = 0  # default: start at Beginner

    steps       = questions_answered // 3
    final_index = min(start_index + steps, len(_LEVELS) - 1)
    return _LEVELS[final_index]             # type: ignore[return-value]


def difficulty_to_score_range(level: DifficultyLevel) -> tuple[float, float]:
    ranges: dict[DifficultyLevel, tuple[float, float]] = {
        "Beginner":     (0.0,  0.33),
        "Intermediate": (0.34, 0.66),
        "Advanced":     (0.67, 1.0),
    }
    return ranges[level]