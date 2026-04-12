import base64
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from app.models import PARequest, PAResponse
from app.rag_engine import retrieve_criteria
from app.form_generator import generate_pa_form
from app.pdf_generator import generate_pa_pdf
from app.pdf_filler import fill_pa_form, get_missing_fields
from app.payer_config import PAYERS
from app.auth import verify_token
from app.rate_limit import limiter
from app.ocr_engine import extract_text_from_image
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class CriterionDetailPDF(BaseModel):
    criterion: str
    met: bool
    evidence: str = ""


class StepTherapyEntryPDF(BaseModel):
    drug_name: str = ""
    dose: str = ""
    schedule: str = ""
    duration: str = ""
    outcome: str = ""


class ExportPDFRequest(BaseModel):
    payer_id: str
    # Patient
    patient_name: Optional[str] = ""
    patient_dob: Optional[str] = ""
    patient_member_id: Optional[str] = ""
    patient_group_number: Optional[str] = ""
    patient_plan_name: Optional[str] = ""
    patient_address: Optional[str] = ""
    patient_city: Optional[str] = ""
    patient_state: Optional[str] = ""
    patient_zip: Optional[str] = ""
    patient_phone: Optional[str] = ""
    patient_sex: Optional[str] = ""
    # Provider
    physician_name: Optional[str] = ""
    physician_npi: Optional[str] = ""
    physician_credentials: Optional[str] = ""
    physician_specialty: Optional[str] = ""
    practice_name: Optional[str] = ""
    practice_address: Optional[str] = ""
    practice_city: Optional[str] = ""
    practice_state: Optional[str] = ""
    practice_zip: Optional[str] = ""
    practice_phone: Optional[str] = ""
    practice_fax: Optional[str] = ""
    # Pharmacy
    pharmacy_name: Optional[str] = ""
    pharmacy_phone: Optional[str] = ""
    # Service
    procedure_name: Optional[str] = ""
    drug_brand_name: Optional[str] = ""
    drug_generic_name: Optional[str] = ""
    dosage_strength: Optional[str] = ""
    quantity_requested: Optional[str] = ""
    days_supply: Optional[str] = ""
    cpt_code: Optional[str] = ""
    cpt_description: Optional[str] = ""
    icd10_code: Optional[str] = ""
    icd10_description: Optional[str] = ""
    service_date: Optional[str] = ""
    urgency: Optional[str] = "routine"
    rendering_provider: Optional[str] = ""
    rendering_facility: Optional[str] = ""
    # Step therapy (Section G on BCBS / equivalent on other payers)
    step_therapy: Optional[List[StepTherapyEntryPDF]] = []
    # Clinical
    clinical_justification: Optional[str] = ""
    medical_necessity: Optional[str] = ""
    supporting_evidence: Optional[str] = ""
    policy_sections_cited: Optional[List[str]] = []
    criteria_details: Optional[List[CriterionDetailPDF]] = []
    criteria_met: Optional[int] = 0
    criteria_total: Optional[int] = 0
    approval_likelihood: Optional[str] = ""
    missing_information: Optional[List[str]] = []


@router.post("/export-pdf")
@limiter.limit("30/minute")
async def export_pa_pdf(
    request: Request,
    body: ExportPDFRequest,
    _user: dict = Depends(verify_token),
):
    """
    Generate a filled-out, fax-ready PA form PDF.
    Tries the real payer form first (AcroForm fill or coordinate overlay).
    Falls back to the AuthFlow-generated template if the payer form is unavailable.
    """
    try:
        # Build unified data dict
        data = {
            "patient_name":          body.patient_name or "",
            "patient_dob":           body.patient_dob or "",
            "patient_member_id":     body.patient_member_id or "",
            "patient_group_number":  body.patient_group_number or "",
            "patient_plan_name":     body.patient_plan_name or "",
            "patient_address":       body.patient_address or "",
            "patient_city":          body.patient_city or "",
            "patient_state":         body.patient_state or "",
            "patient_zip":           body.patient_zip or "",
            "patient_phone":         body.patient_phone or "",
            "patient_sex":           body.patient_sex or "",
            "physician_name":        body.physician_name or "",
            "physician_npi":         body.physician_npi or "",
            "physician_credentials": body.physician_credentials or "",
            "physician_specialty":   body.physician_specialty or "",
            "practice_name":         body.practice_name or "",
            "practice_address":      body.practice_address or "",
            "practice_city":         body.practice_city or "",
            "practice_state":        body.practice_state or "",
            "practice_zip":          body.practice_zip or "",
            "practice_phone":        body.practice_phone or "",
            "practice_fax":          body.practice_fax or "",
            "pharmacy_name":         body.pharmacy_name or "",
            "pharmacy_phone":        body.pharmacy_phone or "",
            "rendering_provider":    body.rendering_provider or "",
            "rendering_facility":    body.rendering_facility or "",
            "procedure_name":        body.procedure_name or "",
            "drug_brand_name":       body.drug_brand_name or "",
            "drug_generic_name":     body.drug_generic_name or "",
            "dosage_strength":       body.dosage_strength or "",
            "quantity_requested":    body.quantity_requested or "",
            "days_supply":           body.days_supply or "",
            "cpt_code":              body.cpt_code or "",
            "cpt_description":       body.cpt_description or "",
            "icd10_code":            body.icd10_code or "",
            "icd10_description":     body.icd10_description or "",
            "service_date":          body.service_date or "",
            "urgency":               body.urgency or "routine",
            "clinical_justification": body.clinical_justification or "",
            "medical_necessity":     body.medical_necessity or "",
            "supporting_evidence":   body.supporting_evidence or "",
            # Step therapy — structured drug history for Section G (BCBS etc.)
            "step_therapy": [
                {
                    "drug_name": e.drug_name,
                    "dose":      e.dose,
                    "schedule":  e.schedule,
                    "duration":  e.duration,
                    "outcome":   e.outcome,
                }
                for e in (body.step_therapy or [])
            ],
        }

        # Try filling the actual payer form
        pdf_bytes = fill_pa_form(body.payer_id, data)

        # Fall back to AuthFlow-generated template if filler returns empty
        if not pdf_bytes:
            pdf_bytes = generate_pa_pdf(
                payer_id=body.payer_id,
                patient_name=body.patient_name or "",
                patient_dob=body.patient_dob or "",
                patient_member_id=body.patient_member_id or "",
                patient_group_number=body.patient_group_number or "",
                patient_plan_name=body.patient_plan_name or "",
                physician_name=body.physician_name or "",
                physician_npi=body.physician_npi or "",
                physician_credentials=body.physician_credentials or "",
                practice_name=body.practice_name or "",
                practice_address=body.practice_address or "",
                practice_city=body.practice_city or "",
                practice_state=body.practice_state or "",
                practice_zip=body.practice_zip or "",
                practice_phone=body.practice_phone or "",
                practice_fax=body.practice_fax or "",
                procedure_name=body.procedure_name or "",
                cpt_code=body.cpt_code or "",
                cpt_description=body.cpt_description or "",
                icd10_code=body.icd10_code or "",
                icd10_description=body.icd10_description or "",
                service_date=body.service_date or "",
                urgency=body.urgency or "routine",
                rendering_provider=body.rendering_provider or "",
                rendering_facility=body.rendering_facility or "",
                clinical_justification=body.clinical_justification or "",
                medical_necessity=body.medical_necessity or "",
                supporting_evidence=body.supporting_evidence or "",
                policy_sections_cited=body.policy_sections_cited or [],
                criteria_details=[c.model_dump() for c in (body.criteria_details or [])],
                criteria_met=body.criteria_met or 0,
                criteria_total=body.criteria_total or 0,
                approval_likelihood=body.approval_likelihood or "",
                missing_information=body.missing_information or [],
            )

        payer_name = PAYERS.get(body.payer_id, {}).get("short_name", body.payer_id)
        patient_slug = (body.patient_name or "patient").replace(" ", "_").lower()
        filename = f"PA_{payer_name}_{patient_slug}.pdf".replace(" ", "_")

        logger.info(f"PDF exported | payer={body.payer_id} patient={bool(body.patient_name)} size={len(pdf_bytes)}b")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


class MissingFieldsRequest(BaseModel):
    payer_id: str
    patient_address: Optional[str] = ""
    patient_city: Optional[str] = ""
    patient_state: Optional[str] = ""
    patient_zip: Optional[str] = ""
    patient_phone: Optional[str] = ""
    patient_sex: Optional[str] = ""
    physician_specialty: Optional[str] = ""
    practice_fax: Optional[str] = ""
    pharmacy_name: Optional[str] = ""
    pharmacy_phone: Optional[str] = ""


@router.post("/missing-fields")
async def get_form_missing_fields(
    body: MissingFieldsRequest,
    _user: dict = Depends(verify_token),
):
    """Return which payer form fields are still empty given the current data."""
    data = body.model_dump()
    missing = get_missing_fields(body.payer_id, data)
    return {"payer_id": body.payer_id, "missing_fields": missing}


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
