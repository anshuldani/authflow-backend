"""
JWT verification for Supabase Bearer tokens.

Every protected route depends on verify_token().
DEMO_MODE bypasses verification so the demo works without Supabase.
If SUPABASE_JWT_SECRET is not set, verification is skipped with a warning.
"""

import os
import logging
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

_security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(_security),
) -> dict:
    """
    FastAPI dependency — validates the Supabase JWT in the Authorization header.

    Returns the decoded payload dict on success.
    Raises HTTP 401 on invalid/expired token.
    """
    # DEMO_MODE: bypass auth entirely for demo / local testing
    if DEMO_MODE:
        return {"sub": "demo-user", "role": "authenticated"}

    # No JWT secret configured: warn once and let through (dev convenience)
    if not SUPABASE_JWT_SECRET:
        logger.warning(
            "SUPABASE_JWT_SECRET not set — JWT verification disabled. "
            "Set this env var in production."
        )
        return {"sub": "anonymous", "role": "authenticated"}

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header with Bearer token required.",
        )

    try:
        from jose import jwt, JWTError

        payload = jwt.decode(
            credentials.credentials,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload

    except Exception as exc:
        # Covers JWTError, ImportError (jose not installed), etc.
        logger.warning(f"JWT verification failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


# ── Token expiry check ───────────────────────────────────────────────────────
import time as _time

def is_token_expired(token_payload: dict, clock_skew_secs: int = 30) -> bool:
    """Return True if JWT exp claim indicates the token has expired."""
    exp = token_payload.get("exp")
    if exp is None:
        return True
    return _time.time() > (exp + clock_skew_secs)
