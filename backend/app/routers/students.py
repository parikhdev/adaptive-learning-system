"""
app/routers/students.py
GET /students/{student_id}/stats
"""

from fastapi import APIRouter, HTTPException
from app.db.connection import execute_query
from app.schemas.student import StudentStatsResponse, TopicStat

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/{student_id}/stats", response_model=StudentStatsResponse)
def get_student_stats(student_id: str):
    # Overall stats
    overall = execute_query(
        """
        SELECT
            COUNT(*)                    AS total_sessions,
            SUM(total_questions)        AS total_questions,
            SUM(correct_answers)        AS total_correct
        FROM sessions
        WHERE student_id = %s
        """,
        (student_id,)
    )

    if not overall or overall[0]["total_sessions"] == 0:
        raise HTTPException(status_code=404, detail="No data found for student")

    o             = overall[0]
    total_q       = int(o["total_questions"] or 0)
    total_correct = int(o["total_correct"] or 0)
    accuracy      = round(total_correct / total_q, 4) if total_q > 0 else 0.0

    # Topic breakdown
    topic_rows = execute_query(
        """
        SELECT
            q.subject,
            q.topic,
            COUNT(*)                        AS total,
            SUM(CASE WHEN sr.is_correct THEN 1 ELSE 0 END) AS correct,
            AVG(q.difficulty_score)         AS avg_difficulty
        FROM student_responses sr
        JOIN sessions s   ON sr.session_id  = s.id
        JOIN questions q  ON sr.question_id = q.id
        WHERE s.student_id = %s
        GROUP BY q.subject, q.topic
        ORDER BY q.subject, q.topic
        """,
        (student_id,)
    )

    topic_breakdown = [
        TopicStat(
            subject=row["subject"],
            topic=row["topic"],
            total=int(row["total"]),
            correct=int(row["correct"]),
            accuracy=round(int(row["correct"]) / int(row["total"]), 4),
            avg_difficulty=round(float(row["avg_difficulty"]), 4),
        )
        for row in topic_rows
    ]

    return StudentStatsResponse(
        student_id=student_id,
        total_sessions=int(o["total_sessions"]),
        total_questions=total_q,
        total_correct=total_correct,
        overall_accuracy=accuracy,
        topic_breakdown=topic_breakdown,
    )