from fastapi import APIRouter, HTTPException
from app.models import PARequest, PAResponse
from app.rag_engine import retrieve_criteria
from app.form_generator import generate_pa_form
from app.payer_config import PAYERS
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-pa", response_model=PAResponse)
async def generate_prior_auth(request: PARequest) -> PAResponse:
    """
    Core endpoint: generate a complete prior authorization form.
    
    Input:  clinical note + payer ID + optional procedure type
    Output: structured PA form with sections and policy citations
    """
    # Validate payer
    if request.payer not in PAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payer '{request.payer}'. Valid payers: {list(PAYERS.keys())}"
        )

    # Validate clinical note
    if not request.clinical_note or len(request.clinical_note.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Clinical note is too short. Please provide a complete clinical note."
        )

    # Retrieve relevant payer criteria via RAG
    procedure_type = request.procedure_type or "general"
    logger.info(f"PA request: payer={request.payer}, procedure={procedure_type}")

    payer_criteria = retrieve_criteria(
        payer_id=request.payer,
        procedure_type=procedure_type,
        clinical_note=request.clinical_note,
    )

    # Generate PA form
    result = generate_pa_form(request, payer_criteria)

    if not result.success:
        raise HTTPException(status_code=500, detail="Form generation failed.")

    return result
