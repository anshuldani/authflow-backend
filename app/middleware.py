"""
Custom middleware utilities for AuthFlow backend.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response

logger = logging.getLogger(__name__)


async def timeout_middleware(request: Request, call_next: Callable, timeout_secs: float = 30.0) -> Response:
    """Enforce a hard timeout on all requests."""
    import asyncio
    try:
        return await asyncio.wait_for(call_next(request), timeout=timeout_secs)
    except asyncio.TimeoutError:
        logger.warning(f"Request timed out after {timeout_secs}s: {request.url.path}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Request timed out"}, status_code=504)
