"""
app/schemas/question.py
Pydantic V2 schemas for question request/response
"""

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               UUID
    source_row_id:    int
    original_text:    str
    subject:          str
    topic:            str
    subtopic:         str
    difficulty_level: str
    difficulty_score: float
    estimated_time:   int
    formula_present:  bool
    keyword_density:  float


class QuestionFilterParams(BaseModel):
    subject:      Optional[str]   = None
    topic:        Optional[str]   = None
    subtopic:     Optional[str]   = None
    diff_min:     Optional[float] = 0.0
    diff_max:     Optional[float] = 1.0
    limit:        Optional[int]   = 20
    offset:       Optional[int]   = 0