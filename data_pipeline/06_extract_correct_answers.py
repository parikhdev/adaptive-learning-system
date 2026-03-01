# data_pipeline/06_extract_correct_answers.py
# Extracts correct answers from all questions using Groq
# Optimized: 5 questions per API call → ~13 hours runtime
# Safe to interrupt and resume — skips already-processed questions

import os
import re
import time
import logging
import psycopg2
from groq import Groq
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 6543)),
    "dbname":   os.getenv("DB_NAME", "postgres"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode":  "require",
    "options":  "-c client_encoding=UTF8",
}

GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
MODEL         = "llama-3.1-8b-instant"
QUESTIONS_PER_CALL = 5      # questions batched per single Groq call
FETCH_SIZE    = 100          # rows fetched from DB at once
DELAY_SEC     = 2.0          # delay between Groq calls — stays within free tier


def get_unanswered(conn, limit: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, original_text
            FROM questions
            WHERE correct_answer IS NULL
            LIMIT %s;
        """, (limit,))
        return [{"id": str(row[0]), "text": row[1]} for row in cur.fetchall()]


def build_batch_prompt(questions: list[dict]) -> str:
    """
    Build a single prompt for N questions.
    Response format: one line per question → Q1:A Q2:B Q3:C etc.
    """
    lines = ["You are a JEE/NEET expert. For each question below, respond with ONLY the question number and correct answer letter on separate lines.",
             "Format exactly like this example:",
             "Q1:A",
             "Q2:C",
             "Q3:B",
             "No explanations. No extra text. Just the Q number and letter.",
             ""]

    for i, q in enumerate(questions, 1):
        lines.append(f"Q{i}:")
        lines.append(q["text"].strip())
        lines.append("")

    return "\n".join(lines)


def parse_batch_response(response_text: str, count: int) -> list[str | None]:
    """
    Parse Groq response into list of answers.
    Returns list of length `count` with A/B/C/D or None per question.
    """
    results: list[str | None] = [None] * count
    pattern = re.compile(r"Q(\d+)\s*[:\-]\s*([A-Da-d])")

    for match in pattern.finditer(response_text):
        idx = int(match.group(1)) - 1
        answer = match.group(2).upper()
        if 0 <= idx < count:
            results[idx] = answer

    return results


def batch_extract_answers(client: Groq, questions: list[dict]) -> list[str | None]:
    """Send batch of questions to Groq, return list of answers."""
    prompt = build_batch_prompt(questions)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,       # 5 questions × ~5 tokens each
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()
        return parse_batch_response(raw, len(questions))
    except Exception as e:
        logger.error(f"Groq batch call failed: {e}")
        return [None] * len(questions)


def update_answers(conn, updates: list[tuple[str, str]]):
    """Bulk update correct_answer for a list of (answer, id) tuples."""
    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE questions SET correct_answer = %s WHERE id = %s;",
            updates
        )
    conn.commit()


def get_remaining_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM questions WHERE correct_answer IS NULL;")
        return cur.fetchone()[0]


def main():
    logger.info("=" * 60)
    logger.info("Correct Answer Extraction — Optimized Batch Mode")
    logger.info("5 questions per Groq call | 2s delay between calls")
    logger.info("Safe to Ctrl+C and resume — skips processed questions")
    logger.info("=" * 60)

    client = Groq(api_key=GROQ_API_KEY)
    conn = psycopg2.connect(**DB_CONFIG)

    remaining = get_remaining_count(conn)
    logger.info(f"Questions remaining: {remaining:,}")
    estimated_hours = (remaining / QUESTIONS_PER_CALL * DELAY_SEC) / 3600
    logger.info(f"Estimated runtime: {estimated_hours:.1f} hours")
    logger.info("Starting... safe to leave running overnight.")
    logger.info("-" * 60)

    total_processed = 0
    total_failed    = 0

    try:
        while True:
            rows = get_unanswered(conn, FETCH_SIZE)
            if not rows:
                break

            # Split fetch into batches of QUESTIONS_PER_CALL
            for i in range(0, len(rows), QUESTIONS_PER_CALL):
                batch = rows[i : i + QUESTIONS_PER_CALL]
                answers = batch_extract_answers(client, batch)

                updates = []
                for q, answer in zip(batch, answers):
                    if answer:
                        updates.append((answer, q["id"]))
                        total_processed += 1
                    else:
                        total_failed += 1

                if updates:
                    update_answers(conn, updates)

                time.sleep(DELAY_SEC)

            logger.info(
                f"Progress: {total_processed:,} processed | "
                f"{total_failed} failed | "
                f"{get_remaining_count(conn):,} remaining"
            )

    except KeyboardInterrupt:
        logger.info(f"Interrupted safely. {total_processed:,} questions processed.")
    finally:
        conn.close()

    logger.info("=" * 60)
    logger.info(f"COMPLETE — Processed: {total_processed:,} | Failed: {total_failed}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()