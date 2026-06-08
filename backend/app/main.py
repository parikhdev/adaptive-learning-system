import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import questions, sessions, students
from app.routers.recommend import router as recommend_router
from app.routers.explain import router as explain_router
from app.ml import get_embedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Startup] Warming up embedding model...")
    embedder = get_embedder()
    _ = embedder.encode("warmup")
    logger.info("[Startup] Embedding model ready.")
    yield
    logger.info("[Shutdown] Cleanup complete.")


app = FastAPI(redirect_slashes=False, 
    title="Adaptive Learning System API",
    version="5.0.0",
    description="JEE/NEET Adaptive Question Recommendation + RAG Explanation Engine",
    lifespan=lifespan,
)

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://adaptive-learning-system-six.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers 
app.include_router(questions.router)
app.include_router(sessions.router)
app.include_router(students.router)
app.include_router(recommend_router)
app.include_router(explain_router)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
def health():
    return {"status": "ok"}
