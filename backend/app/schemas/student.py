"""
app/schemas/student.py
Pydantic V2 schemas for student stats
"""

from pydantic import BaseModel
from typing import Optional


class TopicStat(BaseModel):
    subject:        str
    topic:          str
    total:          int
    correct:        int
    accuracy:       float
    avg_difficulty: float


class StudentStatsResponse(BaseModel):
    student_id:      str
    total_sessions:  int
    total_questions: int
    total_correct:   int
    overall_accuracy: float
    topic_breakdown: list[TopicStat]