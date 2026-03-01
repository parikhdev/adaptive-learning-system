"""
05_upload_supabase.py
Adaptive Learning System — Phase 2 Final Upload
Direct Postgres via psycopg2 (bypasses REST API / 525 SSL issues)
CSV    : data/processed/topics_extracted.csv
Matrix : data/processed/embeddings_matrix.npy
Tables : questions, question_embeddings
"""

import os
import time
import logging
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

DB_URL          = os.environ["SUPABASE_DB_URL"]
CSV_PATH        = "data/processed/topics_extracted.csv"
EMBEDDINGS_PATH = "data/processed/embeddings_matrix.npy"

BATCH_SIZE  = 500   # psycopg2 handles large batches fine — no REST overhead
MAX_RETRIES = 3
BACKOFF     = [2, 4, 8]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("upload.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(DB_URL)

# ── Utilities ─────────────────────────────────────────────────────────────────

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# ── Stage 1: Upload Questions ─────────────────────────────────────────────────

def fetch_uploaded_source_row_ids(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT source_row_id FROM questions;")
        rows = cur.fetchall()
    uploaded = {int(r[0]) for r in rows}
    log.info(f"Questions already uploaded: {len(uploaded)}")
    return uploaded


def upload_questions(conn, df: pd.DataFrame):
    already = fetch_uploaded_source_row_ids(conn)
    pending = df[~df["row_id"].isin(already)]
    log.info(f"Questions to upload: {len(pending)} / {len(df)}")

    if len(pending) == 0:
        log.info("Questions already complete. Skipping.")
        return

    INSERT_SQL = """
        INSERT INTO questions (
            source_row_id,
            original_text,
            subject,
            topic,
            subtopic,
            difficulty_level,
            difficulty_score,
            estimated_time,
            formula_present,
            keyword_density
        ) VALUES %s
        ON CONFLICT (source_row_id) DO NOTHING;
    """

    success, fail = 0, 0

    for i, batch in enumerate(chunked(range(len(pending)), BATCH_SIZE)):
        rows = pending.iloc[batch]
        records = []
        for _, r in rows.iterrows():
            records.append((
                int(r["row_id"]),
                str(r["eng"]),
                str(r["Subject"]),
                str(r["topic"]),
                str(r["subtopic"]),
                str(r["difficulty_level"]),
                float(r["difficulty_score"]),
                int(r["estimated_time"]),
                bool(r["has_latex"]),
                float(r["score_keyword"]),
            ))

        for attempt in range(MAX_RETRIES):
            try:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_values(cur, INSERT_SQL, records)
                conn.commit()
                success += len(records)
                break
            except Exception as e:
                conn.rollback()
                wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                log.warning(f"Questions batch {i+1} failed: {e} | Retry in {wait}s")
                time.sleep(wait)
        else:
            fail += len(records)
            log.error(f"Questions batch {i+1} failed permanently.")

        if (i + 1) % 10 == 0:
            log.info(f"Questions progress: {success} uploaded | {fail} failed")

    log.info(f"Questions done — Success: {success} | Failed: {fail}")


# ── Stage 2: Build UUID Map ───────────────────────────────────────────────────

def fetch_id_map(conn) -> dict:
    """Returns {source_row_id (int) -> question uuid (str)}"""
    log.info("Building source_row_id → UUID map...")
    with conn.cursor() as cur:
        cur.execute("SELECT source_row_id, id FROM questions;")
        rows = cur.fetchall()
    id_map = {int(r[0]): str(r[1]) for r in rows}
    assert len(id_map) == 121557, f"UUID map incomplete: {len(id_map)} / 121557"
    log.info(f"UUID map ready: {len(id_map)} entries")
    return id_map


# ── Stage 3: Upload Embeddings ────────────────────────────────────────────────

def fetch_uploaded_question_ids(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT question_id FROM question_embeddings;")
        rows = cur.fetchall()
    uploaded = {str(r[0]) for r in rows}
    log.info(f"Embeddings already uploaded: {len(uploaded)}")
    return uploaded


def upload_embeddings(conn, df: pd.DataFrame, embeddings: np.ndarray, id_map: dict):
    already = fetch_uploaded_question_ids(conn)

    # Build pending list
    pending = []
    for _, r in df.iterrows():
        sid  = int(r["row_id"])
        uuid = id_map.get(sid)
        if uuid is None:
            log.warning(f"No UUID for source_row_id={sid}, skipping")
            continue
        if uuid in already:
            continue
        pending.append((sid, uuid))

    log.info(f"Embeddings to upload: {len(pending)} / {len(df)}")

    if len(pending) == 0:
        log.info("Embeddings already complete. Skipping.")
        return

    INSERT_SQL = """
        INSERT INTO question_embeddings (question_id, embedding)
        VALUES %s
        ON CONFLICT (question_id) DO NOTHING;
    """

    success, fail = 0, 0

    for i, batch in enumerate(chunked(pending, BATCH_SIZE)):
        records = []
        for sid, uuid in batch:
            vector = embeddings[sid].tolist()
            records.append((uuid, vector))

        for attempt in range(MAX_RETRIES):
            try:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_values(cur, INSERT_SQL, records)
                conn.commit()
                success += len(records)
                break
            except Exception as e:
                conn.rollback()
                wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                log.warning(f"Embeddings batch {i+1} failed: {e} | Retry in {wait}s")
                time.sleep(wait)
        else:
            fail += len(records)
            log.error(f"Embeddings batch {i+1} failed permanently.")

        if (i + 1) % 10 == 0:
            total_done = len(already) + success
            pct = (total_done / 121557) * 100
            log.info(f"Embeddings progress: {total_done} / 121557 ({pct:.1f}%) | Failed: {fail}")

    log.info(f"Embeddings done — Success: {success} | Failed: {fail}")
    if fail > 0:
        log.info("Rerun script to resume failed batches. Fully idempotent.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Phase 2 Upload | Direct Postgres | Adaptive Learning System")
    log.info("=" * 60)

    # Load data
    df = pd.read_csv(CSV_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)

    # Hard assertions
    assert len(df) == 121557,                   f"CSV row mismatch: {len(df)}"
    assert embeddings.shape == (121557, 384),   f"Embedding shape mismatch: {embeddings.shape}"
    assert df["row_id"].is_monotonic_increasing, "row_id not sorted — alignment risk"

    log.info(f"CSV: {df.shape} | Embeddings: {embeddings.shape} | Assertions passed")

    # Single persistent connection for entire upload
    conn = get_connection()
    log.info("Postgres connection established.")

    try:
        upload_questions(conn, df)
        id_map = fetch_id_map(conn)
        upload_embeddings(conn, df, embeddings, id_map)
    finally:
        conn.close()
        log.info("Connection closed.")

    log.info("=" * 60)
    log.info("Phase 2 Complete. Run HNSW index SQL next.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()