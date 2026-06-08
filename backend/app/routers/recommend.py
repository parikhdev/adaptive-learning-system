# backend/app/routers/recommend.py
import logging
from fastapi import APIRouter, HTTPException

from app.ml import get_embedder
from app.ml.difficulty import next_difficulty, DEFAULT_DIFFICULTY
from app.db.connection import execute_query
from app.db.vector_search import (
    cosine_search_questions,
    get_answered_question_ids,
    get_session_context,
)
from app.schemas.recommendation import (
    RecommendRequest,
    RecommendResponse,
    RecommendedQuestion,
)

router = APIRouter(prefix="/recommend", tags=["Recommendation"])
logger = logging.getLogger(__name__)


@router.post("", response_model=RecommendResponse)
def recommend_question(request: RecommendRequest) -> RecommendResponse:


    # Step 1: Session context
    context = get_session_context(request.session_id)
    if context is None:
        raise HTTPException(status_code=404,
                            detail=f"Session {request.session_id} not found.")

    questions_answered: int       = context.get("total_questions", 0)
    last_difficulty:    str | None = context.get("last_difficulty")

    # Step 2: Direct session row read for difficulty fields
    rows = execute_query(
        "SELECT difficulty_mode, fixed_difficulty FROM sessions WHERE id = %s",
        (request.session_id,),
    )
    db_mode = rows[0].get("difficulty_mode") if rows else None
    db_fd   = rows[0].get("fixed_difficulty") if rows else None

    # Final resolved values — request body takes priority over DB
    mode             = request.difficulty_mode  or db_mode or "adaptive"
    fixed_difficulty = request.fixed_difficulty or db_fd

    # Step 3: Compute target difficulty
    target_difficulty = next_difficulty(
        current_level=last_difficulty,
        questions_answered=questions_answered,
        mode=mode,
        fixed_difficulty=fixed_difficulty,
    )

    # Step 4: Embed
    embedder     = get_embedder()
    query_text   = embedder.build_query(subject=request.subject, topic=request.topic)
    query_vector = embedder.encode(query_text)

    # Step 5: Exclusion list 
    excluded_ids = get_answered_question_ids(request.session_id)

    # Step 6: Vector search
    candidates = cosine_search_questions(
        query_vector=query_vector,
        subject=request.subject,
        difficulty_level=target_difficulty,
        excluded_ids=excluded_ids,
        top_k=10,
    )

    if not candidates:
        logger.warning(f"[Recommend] No candidates at {target_difficulty} — fallback to {DEFAULT_DIFFICULTY}")
        candidates = cosine_search_questions(
            query_vector=query_vector,
            subject=request.subject,
            difficulty_level=DEFAULT_DIFFICULTY,
            excluded_ids=excluded_ids,
            top_k=10,
        )

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No questions available for subject='{request.subject}' at '{target_difficulty}'.",
        )

    best = candidates[0]

    return RecommendResponse(
        session_id=request.session_id,
        student_id=request.student_id,
        recommended_difficulty=target_difficulty,
        difficulty_mode=mode,
        question=RecommendedQuestion(
            id=best["id"],
            original_text=best["original_text"],
            subject=best["subject"],
            topic=best.get("topic"),
            subtopic=best.get("subtopic"),
            difficulty_level=best["difficulty_level"],
            difficulty_score=best.get("difficulty_score"),
            estimated_time=best.get("estimated_time"),
            formula_present=best.get("formula_present"),
            keyword_density=best.get("keyword_density"),
            cosine_distance=float(best["cosine_distance"]),
        ),
        debug={
            "query_text":              query_text,
            "target_difficulty":       target_difficulty,
            "difficulty_mode":         mode,
            "fixed_difficulty":        fixed_difficulty,
            "candidates_evaluated":    len(candidates),
            "excluded_question_count": len(excluded_ids),
            "questions_answered":      questions_answered,
        },
    )