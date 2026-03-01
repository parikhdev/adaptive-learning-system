# backend/app/rag/generator.py

import logging
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)


async def generate_explanation(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Call Groq API with the assembled prompt.
    Uses AsyncGroq for non-blocking FastAPI compatibility.

    Model   : llama-3.1-8b-instant (from config)
    Target  : <800ms end-to-end
    """
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=settings.GROQ_MAX_TOKENS,
            temperature=settings.GROQ_TEMPERATURE,
        )

        explanation = response.choices[0].message.content.strip()
        logger.debug(
            f"[Generator] Groq response: "
            f"{response.usage.completion_tokens} tokens, "
            f"model={response.model}"
        )
        return explanation

    except Exception as e:
        logger.error(f"[Generator] Groq API call failed: {e}")
        raise