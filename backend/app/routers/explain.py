# backend/app/routers/explain.py

import logging
from fastapi import APIRouter, HTTPException

from app.rag import run_rag_pipeline
from app.rag.retriever import fetch_question_text
from app.schemas.explanation import ExplainRequest, ExplainResponse

router = APIRouter(prefix="/explain", tags=["RAG Explanation"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ExplainResponse)
async def explain_answer(request: ExplainRequest) -> ExplainResponse:
    # Step 1: Resolve question text from ID
    question_text = fetch_question_text(request.question_id)

    if question_text is None:
        raise HTTPException(
            status_code=404,
            detail=f"Question {request.question_id} not found."
        )
    # Step 2: Run RAG pipeline
    try:
        result = await run_rag_pipeline(
            question_id=request.question_id,
            question_text=question_text,
            subject=request.subject,
            topic=request.topic,
            student_answer=request.student_answer,
            difficulty_level=request.difficulty_level,
            top_k=3,
        )
    except Exception as e:
        logger.error(f"[Explain] RAG pipeline failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Explanation generation failed. Please try again."
        )
    # Step 3: Return structured response
    return ExplainResponse(
        question_id=request.question_id,
        subject=request.subject,
        topic=request.topic,
        student_answer=request.student_answer,
        explanation=result["explanation"],
        similar_questions_used=result["similar_questions_used"],
        latency_ms=result["latency_ms"],
    )