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
import asyncio
import threading
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
def _background_init():
    """Run heavy startup work in a background thread so the server accepts requests immediately."""
    if not DEMO_MODE:
        if is_rag_loaded():
            logger.info("Background: RAG already populated — skipping ingestion")
        else:
            logger.info("Background: initializing RAG engine...")
            try:
                ingest_synthetic_policies()
                logger.info(f"Background: RAG ready. Loaded: {is_rag_loaded()}")
            except Exception as e:
                logger.warning(f"Background: RAG init failed (will use fallback): {e}")
    else:
        logger.info("Demo mode: skipping RAG init, using hardcoded responses")

    if is_cpt_loaded():
        logger.info("Background: CPT code database ready")
    else:
        logger.warning("Background: CPT database not loaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("AuthFlow Backend starting up")
    logger.info(f"Demo mode: {DEMO_MODE}")

    # Start heavy init in background so healthcheck passes immediately
    thread = threading.Thread(target=_background_init, daemon=True)
    thread.start()

    logger.info("AuthFlow Backend ready (init running in background)")
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
_allowed_origins = [
    o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://authflow.vercel.app"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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


# ── Request ID middleware ─────────────────────────────────────────────────────
import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health/v2", tags=["System"])
async def health_check_v2():
    """Extended health check with component status breakdown."""
    from app.cpt_engine import is_cpt_loaded
    from app.rag_engine import is_rag_loaded
    import psutil
    return {
        "status": "ok",
        "version": "1.1.0",
        "components": {
            "rag": "ready" if is_rag_loaded() else "loading",
            "cpt": "ready" if is_cpt_loaded() else "unavailable",
            "api": "ready",
        },
        "demo_mode": DEMO_MODE,
    }
