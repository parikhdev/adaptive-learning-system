# backend/app/schemas/recommendation.py
from pydantic import BaseModel, Field
from typing import Literal

DifficultyLevel = Literal["Beginner", "Intermediate", "Advanced"]
DifficultyMode  = Literal["adaptive", "fixed"]


class RecommendRequest(BaseModel):
    session_id: str  = Field(..., description="Active session UUID")
    student_id: str  = Field(..., description="Student UUID")
    subject:    str  = Field(..., description="e.g. Physics, Chemistry, Mathematics, Biology")
    topic:      str | None = Field(default=None, description="Optional topic for focused retrieval")

    # NEW
    difficulty_mode:     DifficultyMode    = Field(
        default="adaptive",
        description=(
            "'adaptive' — escalates Beginner→Intermediate→Advanced every 3 Qs; "
            "'fixed' — stays at fixed_difficulty for the whole session"
        ),
    )
    fixed_difficulty: DifficultyLevel | None = Field(
        default=None,
        description="Required when difficulty_mode='fixed'. Ignored in adaptive mode.",
    )


class RecommendedQuestion(BaseModel):
    id:               str
    original_text:    str
    subject:          str
    topic:            str | None
    subtopic:         str | None
    difficulty_level: DifficultyLevel
    difficulty_score: float | None
    estimated_time:   float | None
    formula_present:  bool | None
    keyword_density:  float | None
    cosine_distance:  float = Field(..., description="Lower = more relevant")


class RecommendResponse(BaseModel):
    session_id:              str
    student_id:              str
    recommended_difficulty:  DifficultyLevel
    difficulty_mode:         DifficultyMode          # echoed back for frontend
    question:                RecommendedQuestion
    debug:                   dict | None = Field(default=None)