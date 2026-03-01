import time
import logging
from app.rag.retriever import retrieve_context
from app.rag.prompt_builder import build_prompt
from app.rag.generator import generate_explanation

logger = logging.getLogger(__name__)


async def run_rag_pipeline(
    question_id: str,
    question_text: str,
    subject: str,
    topic: str | None,
    student_answer: str,
    difficulty_level: str | None = None,
    top_k: int = 3,
) -> dict:
    t0 = time.perf_counter()

    context_chunks = retrieve_context(
        question_text=question_text,
        subject=subject,
        exclude_id=question_id,
        difficulty_level=difficulty_level,
        top_k=top_k,
    )
    logger.info(
        f"[RAG] Retrieved {len(context_chunks)} context chunks "
        f"for question_id={question_id}"
    )

    system_prompt, user_prompt = build_prompt(
        question_text=question_text,
        subject=subject,
        topic=topic,
        student_answer=student_answer,
        context_chunks=context_chunks,
    )

    explanation = await generate_explanation(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    latency_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"[RAG] Pipeline complete in {latency_ms:.1f}ms")

    return {
        "explanation": explanation,
        "similar_questions_used": len(context_chunks),
        "latency_ms": round(latency_ms, 2),
    }
