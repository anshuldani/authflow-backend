from fastapi import APIRouter, HTTPException, Depends, Request
from app.models import AppealRequest, AppealResponse
from app.rag_engine import retrieve_criteria
from app.appeal_generator import generate_appeal
from app.payer_config import PAYERS
from app.auth import verify_token
from app.rate_limit import limiter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-appeal", response_model=AppealResponse)
@limiter.limit("10/minute")
async def generate_appeal_letter(
    request: Request,
    body: AppealRequest,
    _user: dict = Depends(verify_token),
) -> AppealResponse:
    """
    Generate an appeal letter for a denied prior authorization.
    Quotes the payer's own policy language against their denial.
    """
    if body.payer not in PAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payer '{body.payer}'. Valid: {list(PAYERS.keys())}",
        )

    if not body.denial_reason or len(body.denial_reason.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Please provide the denial reason from the payer's denial letter.",
        )

    # Log without PHI
    logger.info(
        "Appeal request | payer=%s denial_reason_len=%d",
        body.payer,
        len(body.denial_reason),
    )

    payer_criteria = retrieve_criteria(
        payer_id=body.payer,
        procedure_type="general",
        clinical_note=body.clinical_note,
    )

    result = generate_appeal(body, payer_criteria)

    if not result.success:
        raise HTTPException(status_code=500, detail="Appeal generation failed.")

    logger.info(
        "Appeal response | payer=%s sections=%d citations=%d demo=%s",
        body.payer,
        len(result.appeal_sections),
        len(result.key_citations),
        result.demo_mode,
    )

    return result


# ── Input sanitization ───────────────────────────────────────────────────────
def _sanitize_appeal_input(text: str) -> str:
    """Strip leading/trailing whitespace and collapse internal whitespace runs."""
    import re
    return re.sub(r'\s+', ' ', text.strip())
