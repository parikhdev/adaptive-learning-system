"""
app/routers/questions.py
GET /questions/
GET /questions/{id}
GET /questions/filter
"""

from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import Optional
from app.db.connection import execute_query
from app.schemas.question import QuestionResponse, QuestionFilterParams

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("/", response_model=list[QuestionResponse])
def list_questions(
    limit:  int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    rows = execute_query(
        """
        SELECT id, source_row_id, original_text, subject, topic, subtopic,
               difficulty_level, difficulty_score, estimated_time,
               formula_present, keyword_density
        FROM questions
        ORDER BY source_row_id
        LIMIT %s OFFSET %s
        """,
        (limit, offset)
    )
    return rows


@router.get("/filter", response_model=list[QuestionResponse])
def filter_questions(
    subject:  Optional[str]   = Query(default=None),
    topic:    Optional[str]   = Query(default=None),
    subtopic: Optional[str]   = Query(default=None),
    diff_min: Optional[float] = Query(default=0.0, ge=0.0, le=1.0),
    diff_max: Optional[float] = Query(default=1.0, ge=0.0, le=1.0),
    limit:    Optional[int]   = Query(default=20, ge=1, le=100),
    offset:   Optional[int]   = Query(default=0, ge=0),
):
    filters = ["difficulty_score BETWEEN %s AND %s"]
    params  = [diff_min, diff_max]

    if subject:
        filters.append("subject = %s")
        params.append(subject)
    if topic:
        filters.append("topic = %s")
        params.append(topic)
    if subtopic:
        filters.append("subtopic = %s")
        params.append(subtopic)

    where = " AND ".join(filters)
    params += [limit, offset]

    rows = execute_query(
        f"""
        SELECT id, source_row_id, original_text, subject, topic, subtopic,
               difficulty_level, difficulty_score, estimated_time,
               formula_present, keyword_density
        FROM questions
        WHERE {where}
        ORDER BY difficulty_score
        LIMIT %s OFFSET %s
        """,
        tuple(params)
    )
    return rows


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: UUID):
    rows = execute_query(
        """
        SELECT id, source_row_id, original_text, subject, topic, subtopic,
               difficulty_level, difficulty_score, estimated_time,
               formula_present, keyword_density
        FROM questions
        WHERE id = %s
        """,
        (str(question_id),)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Question not found")
    return rows[0]