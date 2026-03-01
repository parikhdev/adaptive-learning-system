from pydantic import BaseModel, Field
from typing import Literal

DifficultyLevel = Literal["Beginner", "Intermediate", "Advanced"]


class ExplainRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    question_id: str = Field(..., description="UUID of the question answered incorrectly")
    student_answer: str = Field(..., description="Option selected by student e.g. A, B, C, D")
    subject: str = Field(..., description="e.g. Physics, Chemistry, Mathematics, Biology")
    topic: str | None = Field(default=None, description="Optional topic for prompt context")
    difficulty_level: DifficultyLevel | None = Field(
        default=None,
        description="Optional — narrows retrieval scan to same difficulty band"
    )


class ExplainResponse(BaseModel):
    question_id: str
    subject: str
    topic: str | None
    student_answer: str
    explanation: str = Field(..., description="LLM-generated conceptual explanation")
    similar_questions_used: int = Field(..., description="Number of RAG context chunks used")
    latency_ms: float = Field(..., description="Total pipeline latency in milliseconds")
