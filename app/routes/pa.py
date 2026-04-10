from fastapi import APIRouter, HTTPException, Depends, Request
from app.models import PARequest, PAResponse
from app.rag_engine import retrieve_criteria
from app.form_generator import generate_pa_form
from app.payer_config import PAYERS
from app.auth import verify_token
from app.rate_limit import limiter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-pa", response_model=PAResponse)
@limiter.limit("20/minute")
async def generate_prior_auth(
    request: Request,
    body: PARequest,
    _user: dict = Depends(verify_token),
) -> PAResponse:
    """
    Core endpoint: generate a complete prior authorization form.

    Input:  clinical note + payer ID + optional procedure type + optional patient info
    Output: structured PA form with sections, policy citations, and top-level clinical fields
    """
    if body.payer not in PAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payer '{body.payer}'. Valid payers: {list(PAYERS.keys())}",
        )

    if not body.clinical_note or len(body.clinical_note.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Clinical note is too short. Please provide a complete clinical note.",
        )

    # Resolve procedure type from category if not explicitly set
    procedure_type = body.procedure_type or _category_to_type(body.procedure_category) or "general"

    # Log without PHI — no clinical note content
    logger.info(
        "PA request | payer=%s procedure_type=%s procedure_category=%s has_patient_info=%s",
        body.payer,
        procedure_type,
        body.procedure_category or "none",
        bool(body.patient_info),
    )

    payer_criteria = retrieve_criteria(
        payer_id=body.payer,
        procedure_type=procedure_type,
        clinical_note=body.clinical_note,
    )

    result = generate_pa_form(body, payer_criteria)

    if not result.success:
        raise HTTPException(status_code=500, detail="Form generation failed.")

    logger.info(
        "PA response | payer=%s confidence=%s icd10=%s cpt=%s criteria=%s/%s demo=%s time_ms=%s",
        body.payer,
        result.confidence,
        result.icd10_code or "none",
        result.cpt_code or "none",
        result.criteria_met,
        result.criteria_total,
        result.demo_mode,
        result.processing_time_ms,
    )

    return result


def _category_to_type(category: str | None) -> str | None:
    """Map procedure_category (frontend convention) to procedure_type (RAG convention)."""
    if not category:
        return None
    prefix = category.split("_")[0]
    return {
        "imaging": "imaging",
        "surgery": "surgery",
        "drug": "medication",
        "therapy": "medication",
        "procedure": "general",
    }.get(prefix)
