import base64

from fastapi import APIRouter, HTTPException, Depends, Request
from app.models import PARequest, PAResponse
from app.rag_engine import retrieve_criteria
from app.form_generator import generate_pa_form
from app.payer_config import PAYERS
from app.auth import verify_token
from app.rate_limit import limiter
from app.ocr_engine import extract_text_from_image
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
            Optionally accepts image_base64 — OCR runs first, extracted text is combined
            with any typed clinical_note before form generation.
    Output: structured PA form with sections, policy citations, and top-level clinical fields
    """
    if body.payer not in PAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payer '{body.payer}'. Valid payers: {list(PAYERS.keys())}",
        )

    clinical_note = body.clinical_note or ""

    # ── OCR: extract text from image if provided ──────────────────────────────
    if body.image_base64:
        try:
            image_bytes = base64.b64decode(body.image_base64)
            ocr_result = extract_text_from_image(image_bytes)
            extracted = ocr_result.get("text", "")
            if extracted:
                clinical_note = (extracted + "\n" + clinical_note).strip() if clinical_note else extracted
                logger.info(
                    "PA request: OCR extracted %d chars via %s (confidence=%s)",
                    len(extracted),
                    ocr_result.get("method"),
                    ocr_result.get("confidence"),
                )
            else:
                logger.warning("PA request: OCR returned empty text — using typed note only")
        except Exception as e:
            logger.warning(f"PA request: OCR failed, using typed note only: {e}")

    if not clinical_note or len(clinical_note.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Clinical note is too short. Please provide a complete clinical note (or a readable image).",
        )

    # Mutate body so form_generator receives the final note
    body = body.model_copy(update={"clinical_note": clinical_note})

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
