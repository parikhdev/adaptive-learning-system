# backend/app/schemas/session.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional
from datetime import datetime


class SessionStartRequest(BaseModel):
    student_id: str
    subject:    Optional[str] = None

    # NEW 
    difficulty_mode:     Optional[str] = "adaptive"   # "adaptive" | "fixed"
    fixed_difficulty:    Optional[str] = None          # "Beginner" | "Intermediate" | "Advanced"



class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               UUID
    student_id:       str
    subject:          Optional[str]
    started_at:       datetime
    total_questions:  int
    correct_answers:  int
    avg_difficulty:   float

    # NEW (optional — only present if DB column exists) 
    difficulty_mode:     Optional[str] = "adaptive"
    fixed_difficulty:    Optional[str] = None


class AnswerRequest(BaseModel):
    session_id:  UUID
    question_id: UUID
    is_correct:  bool
    time_taken:  Optional[int] = None   # seconds
    skipped:     bool = False


class AnswerResponse(BaseModel):
    recorded:         bool
    session_id:       UUID
    total_questions:  int
    correct_answers:  int
    accuracy:         float
    next_difficulty:  float             # seeds adaptive engine Phase 7