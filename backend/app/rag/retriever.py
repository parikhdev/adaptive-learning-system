import logging
import psycopg2.extras

from app.db.connection import get_connection
from app.ml import get_embedder

logger = logging.getLogger(__name__)


def fetch_question_text(question_id: str) -> str | None:
    sql = "SELECT original_text FROM questions WHERE id = %s LIMIT 1;"
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (question_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"[Retriever] fetch_question_text failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def retrieve_context(
    question_text: str,
    subject: str,
    exclude_id: str,
    difficulty_level: str | None = None,
    top_k: int = 3,
) -> list[str]:
    embedder = get_embedder()
    query_vector = embedder.encode(question_text)

    difficulty_clause = ""
    difficulty_params: list = []
    if difficulty_level:
        difficulty_clause = "AND q.difficulty_level = %s"
        difficulty_params = [difficulty_level]

    sql = f"""
        SELECT
            q.original_text,
            (qe.embedding <=> %s::vector) AS cosine_distance
        FROM questions q
        JOIN question_embeddings qe ON qe.question_id = q.id
        WHERE
            q.subject = %s
            AND q.id != %s
            {difficulty_clause}
        ORDER BY cosine_distance ASC
        LIMIT %s;
    """

    params: list = [
        str(query_vector),
        subject,
        exclude_id,
        *difficulty_params,
        top_k,
    ]

    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            chunks = [row["original_text"] for row in rows]
            logger.info(
                f"[Retriever] subject={subject} difficulty={difficulty_level} "
                f"top_k={top_k} → {len(chunks)} chunks retrieved"
            )
            return chunks
    except Exception as e:
        logger.error(f"[Retriever] retrieve_context failed: {e}")
        raise
    finally:
        if conn:
            conn.close()
