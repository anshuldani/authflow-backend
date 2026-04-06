"""
AuthFlow Backend — FastAPI application entry point.

Run: uvicorn app.main:app --port 8001 --reload
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import pa, appeal, payers
from app.rag_engine import ingest_synthetic_policies, is_rag_loaded

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"


# ── Startup / shutdown ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG engine on startup."""
    logger.info("=" * 50)
    logger.info("AuthFlow Backend starting up")
    logger.info(f"Demo mode: {DEMO_MODE}")

    if not DEMO_MODE:
        logger.info("Initializing RAG engine...")
        try:
            ingest_synthetic_policies()
            logger.info(f"RAG ready. Loaded: {is_rag_loaded()}")
        except Exception as e:
            logger.warning(f"RAG init failed (will use fallback): {e}")
    else:
        logger.info("Demo mode: skipping RAG init, using hardcoded responses")

    logger.info("AuthFlow Backend ready")
    logger.info("=" * 50)
    yield
    logger.info("AuthFlow Backend shutting down")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AuthFlow API",
    description="TurboTax for Prior Authorization — AI-powered PA form generation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Anshul's frontend at localhost:3000 and any deployed URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://authflow.vercel.app",  # Update when deployed
        "*",  # For demo weekend — tighten for production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(pa.router, tags=["Prior Authorization"])
app.include_router(appeal.router, tags=["Appeals"])
app.include_router(payers.router, tags=["Payers"])


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "rag_loaded": is_rag_loaded(),
        "demo_mode": DEMO_MODE,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "AuthFlow API is running",
        "docs": "/docs",
        "health": "/health",
    }
