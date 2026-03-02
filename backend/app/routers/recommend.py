# backend/app/routers/recommend.py

import logging
from fastapi import APIRouter, HTTPException

from app.ml import get_embedder
from app.ml.difficulty import next_difficulty, DEFAULT_DIFFICULTY
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
    """
    POST /recommend/

    Flow:
    1. Fetch session context (total_questions answered so far)
    2. Compute next_difficulty via progress-based escalation
    3. Build query text from subject + topic
    4. Embed query → 384-dim vector
    5. pgvector cosine search with subject + difficulty + exclusion filters
    6. Return best (most similar, correct difficulty) question
    """

    # Step 1: Session context 
    context = get_session_context(request.session_id)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found."
        )

    questions_answered: int = context.get("total_questions", 0)
    last_difficulty: str | None = context.get("last_difficulty")

    # Step 2: Progress-based difficulty 
    target_difficulty = next_difficulty(
        current_level=last_difficulty,        # type: ignore[arg-type]
        questions_answered=questions_answered,
    )

    logger.info(
        f"[Recommend] session={request.session_id} "
        f"questions_answered={questions_answered} "
        f"→ target_difficulty={target_difficulty}"
    )

    # Step 3: Build query text 
    embedder = get_embedder()
    query_text = embedder.build_query(
        subject=request.subject,
        topic=request.topic,
    )

    # Step 4: Embed 
    query_vector = embedder.encode(query_text)

    # Step 5: Fetch answered IDs (exclusion set) 
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
        logger.warning(
            f"[Recommend] No candidates at {target_difficulty} "
            f"for subject={request.subject}. "
            f"Falling back to {DEFAULT_DIFFICULTY}."
        )
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
            detail=(
                f"No questions available for subject='{request.subject}' "
                f"at difficulty='{target_difficulty}'. "
                f"All questions may have been answered."
            )
        )

    best = candidates[0]

    return RecommendResponse(
        session_id=request.session_id,
        student_id=request.student_id,
        recommended_difficulty=target_difficulty,
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
            "query_text": query_text,
            "target_difficulty": target_difficulty,
            "candidates_evaluated": len(candidates),
            "excluded_question_count": len(excluded_ids),
            "questions_answered": questions_answered,
        }
    )