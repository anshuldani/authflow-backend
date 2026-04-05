from fastapi import APIRouter, HTTPException
from app.models import AppealRequest, AppealResponse
from app.rag_engine import retrieve_criteria
from app.appeal_generator import generate_appeal
from app.payer_config import PAYERS
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-appeal", response_model=AppealResponse)
async def generate_appeal_letter(request: AppealRequest) -> AppealResponse:
    """
    Generate an appeal letter for a denied prior authorization.
    Quotes the payer's own policy language against their denial.
    """
    if request.payer not in PAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payer '{request.payer}'. Valid: {list(PAYERS.keys())}"
        )

    if not request.denial_reason or len(request.denial_reason.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Please provide the denial reason from the payer's denial letter."
        )

    logger.info(f"Appeal request: payer={request.payer}, denial='{request.denial_reason[:50]}'")

    # Retrieve payer criteria to quote against denial
    payer_criteria = retrieve_criteria(
        payer_id=request.payer,
        procedure_type="general",
        clinical_note=request.clinical_note,
    )

    result = generate_appeal(request, payer_criteria)

    if not result.success:
        raise HTTPException(status_code=500, detail="Appeal generation failed.")

    return result
