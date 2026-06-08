# backend/app/routers/sessions.py
"""
POST /sessions/start
POST /sessions/answer
GET  /sessions/{session_id}

Changes from v1.0:
  - SessionStartRequest now accepts difficulty_mode and fixed_difficulty.
  - These are stored in the sessions table (new columns added via migration).
  - GET /sessions/{id} echoes them back so /recommend can read them.
"""
from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.db.connection import execute_query, execute_write_returning, execute_write
from app.schemas.session import (
    SessionStartRequest, SessionResponse,
    AnswerRequest, AnswerResponse,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/start", response_model=SessionResponse)
def start_session(body: SessionStartRequest):
    """
    Create a new session.  Stores difficulty_mode and fixed_difficulty so that
    /recommend can retrieve them without needing them in every request body.

    NOTE: If your Supabase sessions table does not yet have the two new columns,
    run this migration first:

        ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS difficulty_mode   TEXT DEFAULT 'adaptive',
            ADD COLUMN IF NOT EXISTS fixed_difficulty  TEXT DEFAULT NULL;
    """
    row = execute_write_returning(
        """
        INSERT INTO sessions
            (student_id, subject, difficulty_mode, fixed_difficulty)
        VALUES (%s, %s, %s, %s)
        RETURNING
            id, student_id, subject, started_at,
            total_questions, correct_answers, avg_difficulty,
            difficulty_mode, fixed_difficulty
        """,
        (
            body.student_id,
            body.subject,
            body.difficulty_mode or "adaptive",
            body.fixed_difficulty,
        ),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return row


@router.post("/answer", response_model=AnswerResponse)
def record_answer(body: AnswerRequest):
    # Insert response
    execute_write(
        """
        INSERT INTO student_responses
            (session_id, question_id, is_correct, time_taken, skipped)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(body.session_id), str(body.question_id),
         body.is_correct, body.time_taken, body.skipped),
    )

    # Update session stats
    execute_write(
        """
        UPDATE sessions SET
            total_questions = total_questions + 1,
            correct_answers = correct_answers + %s
        WHERE id = %s
        """,
        (1 if body.is_correct else 0, str(body.session_id)),
    )

    rows = execute_query(
        """
        SELECT total_questions, correct_answers, avg_difficulty
        FROM sessions WHERE id = %s
        """,
        (str(body.session_id),),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    session = rows[0]
    total   = session["total_questions"]
    correct = session["correct_answers"]
    accuracy = round(correct / total, 4) if total > 0 else 0.0

    current_diff = session["avg_difficulty"]
    if accuracy > 0.8:
        next_diff = min(current_diff + 0.1, 1.0)
    elif accuracy < 0.4:
        next_diff = max(current_diff - 0.1, 0.0)
    else:
        next_diff = current_diff

    return AnswerResponse(
        recorded=True,
        session_id=body.session_id,
        total_questions=total,
        correct_answers=correct,
        accuracy=accuracy,
        next_difficulty=round(next_diff, 4),
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: UUID):
    rows = execute_query(
        """
        SELECT
            id, student_id, subject, started_at,
            total_questions, correct_answers, avg_difficulty,
            difficulty_mode, fixed_difficulty
        FROM sessions WHERE id = %s
        """,
        (str(session_id),),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    return rows[0]