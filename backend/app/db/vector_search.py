# backend/app/db/vector_search.py

import logging
from typing import Any
import psycopg2.extras

from app.db.connection import get_connection

logger = logging.getLogger(__name__)


def cosine_search_questions(
    query_vector: list[float],
    subject: str,
    difficulty_level: str,
    excluded_ids: list[int],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    exclusion_clause = ""
    exclusion_params: list = []

    if excluded_ids:
        placeholders = ",".join(["%s"] * len(excluded_ids))
        exclusion_clause = f"AND q.id NOT IN ({placeholders})"
        exclusion_params = excluded_ids

    sql = f"""
        SELECT
            q.id,
            q.original_text,
            q.subject,
            q.topic,
            q.subtopic,
            q.difficulty_level,
            q.difficulty_score,
            q.estimated_time,
            q.formula_present,
            q.keyword_density,
            (qe.embedding <=> %s::vector) AS cosine_distance
        FROM questions q
        JOIN question_embeddings qe ON qe.question_id = q.id
        WHERE
            q.subject = %s
            AND q.difficulty_level = %s
            AND q.original_text NOT LIKE '%%nan%%'
            {exclusion_clause}
            AND (
            q.original_text LIKE '%%A.%%'
            OR q.original_text LIKE '%%A)%%'
            OR q.original_text LIKE '%%A .%%'
        )
        ORDER BY cosine_distance ASC
        LIMIT %s;
    """

    # Parameters in order 
    params: list = [
        str(query_vector),   
        subject,
        difficulty_level,
        *exclusion_params,
        top_k,
    ]

    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            results = [dict(row) for row in rows]
            logger.debug(
                f"[VectorSearch] subject={subject} difficulty={difficulty_level} "
                f"excluded={len(excluded_ids)} → {len(results)} candidates returned"
            )
            return results
    except Exception as e:
        logger.error(f"[VectorSearch] Query failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_answered_question_ids(session_id: str) -> list[int]:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (session_id,))
            rows = cur.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"[VectorSearch] get_answered_question_ids failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_session_context(session_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT
            s.subject,
            s.avg_difficulty,
            s.correct_answers,
            s.total_questions,
            sr.is_correct AS last_correct,
            q.difficulty_level AS last_difficulty
        FROM sessions s
        LEFT JOIN student_responses sr ON sr.session_id = s.id
        LEFT JOIN questions q ON q.id = sr.question_id
        WHERE s.id = %s
        ORDER BY sr.answered_at DESC
        LIMIT 1;
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (session_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"[VectorSearch] get_session_context failed: {e}")
        raise
    finally:
        if conn:
            conn.close()