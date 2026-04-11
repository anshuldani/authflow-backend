"""
AuthFlow Backend — FastAPI application entry point.

Run: uvicorn app.main:app --port 8001 --reload
"""

# Load .env before any module that reads env vars (e.g. form_generator.py reads DEMO_MODE
# and GOOGLE_API_KEY at import time as module-level constants)
from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routes import pa, appeal, payers, extract_note
from app.rag_engine import ingest_synthetic_policies, is_rag_loaded
from app.cpt_engine import is_cpt_loaded
from app.rate_limit import limiter

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"


# ── Startup / shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
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

    cpt_ready = is_cpt_loaded()
    if cpt_ready:
        logger.info("CPT code database ready (semantic lookup enabled)")
    else:
        logger.warning(
            "CPT code database not loaded — run: python scripts/ingest_cpt_codes.py"
        )

    logger.info("AuthFlow Backend ready")
    logger.info("=" * 50)
    yield
    logger.info("AuthFlow Backend shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AuthFlow API",
    description="TurboTax for Prior Authorization — AI-powered PA form generation",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://authflow.vercel.app",
        "*",  # Tighten for production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Structured request/response logging (no PHI) ─────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """
    Log every request and response with timing — no PHI in output.
    PHI details (clinical notes, patient data) are logged only at the route
    level after redaction — see routes/pa.py and routes/appeal.py.
    """
    start = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - start) * 1000)

    log_entry = {
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": elapsed_ms,
    }
    logger.info("http | %s", json.dumps(log_entry))
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(pa.router, tags=["Prior Authorization"])
app.include_router(appeal.router, tags=["Appeals"])
app.include_router(payers.router, tags=["Payers"])
app.include_router(extract_note.router, tags=["Note Extraction"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "rag_loaded": is_rag_loaded(),
        "cpt_loaded": is_cpt_loaded(),
        "demo_mode": DEMO_MODE,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "AuthFlow API is running",
        "docs": "/docs",
        "health": "/health",
    }
