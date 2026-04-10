"""
/extract-note — OCR + structured extraction from a clinical note image.

Accepts a base64-encoded image (JPEG/PNG/WebP) and returns structured
clinical data suitable for pre-filling a prior authorization form.

LLM: Gemini 2.0 Flash (multimodal vision)
Fallback: structured empty response with low confidence
"""

import os
import json
import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import ExtractNoteRequest, ExtractNoteResponse, ExtractedClinicalData
from app.auth import verify_token
from app.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

EXTRACT_PROMPT = """Extract all clinical information from this medical document image.
Focus on information needed for a prior authorization request.
Procedure context: {procedure_type}

Return ONLY this exact JSON with no markdown, no explanation:
{{
  "patient_name": "string or null",
  "patient_dob": "MM/DD/YYYY or null",
  "visit_date": "MM/DD/YYYY or null",
  "ordering_provider": "string or null",
  "diagnosis": "primary diagnosis as written in the document",
  "icd10_codes": ["array of ICD-10 codes mentioned, or empty array"],
  "procedure_requested": "string or null",
  "cpt_codes": ["array of CPT codes mentioned, or empty array"],
  "symptoms": "description of all symptoms documented",
  "duration_of_symptoms": "e.g. 6 weeks, 3 months, or null",
  "treatments_tried": ["array of treatments mentioned with duration where stated"],
  "clinical_findings": "exam findings, vital signs, test results",
  "raw_text": "full verbatim text extracted from the document",
  "extraction_confidence": "high if printed/typed clearly, medium if partially handwritten, low if mostly handwritten or unclear"
}}"""


def _demo_extraction() -> ExtractedClinicalData:
    return ExtractedClinicalData(
        patient_name=None,
        patient_dob=None,
        diagnosis="Demo mode — connect Gemini API key for live OCR extraction",
        icd10_codes=[],
        procedure_requested=None,
        cpt_codes=[],
        symptoms="Document extraction requires a configured API key",
        duration_of_symptoms=None,
        treatments_tried=[],
        clinical_findings=None,
        ordering_provider=None,
        visit_date=None,
        raw_text="Demo mode: live document extraction not available without GOOGLE_API_KEY.",
        extraction_confidence="low",
    )


def _extract_via_gemini(image_base64: str, mime_type: str, procedure_type: str) -> ExtractedClinicalData:
    """Use Gemini vision to extract clinical data from an image."""
    google_key = os.getenv("GOOGLE_API_KEY", "")
    if not google_key:
        logger.warning("GOOGLE_API_KEY not set — returning empty extraction")
        return _demo_extraction()

    try:
        import google.generativeai as genai

        genai.configure(api_key=google_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Decode and re-encode to confirm valid base64
        image_bytes = base64.b64decode(image_base64)

        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        }

        prompt = EXTRACT_PROMPT.format(procedure_type=procedure_type)
        response = model.generate_content([image_part, prompt])
        text = response.text.strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```").strip()

        raw = json.loads(text)

        return ExtractedClinicalData(
            patient_name=raw.get("patient_name"),
            patient_dob=raw.get("patient_dob"),
            diagnosis=raw.get("diagnosis"),
            icd10_codes=raw.get("icd10_codes") or [],
            procedure_requested=raw.get("procedure_requested"),
            cpt_codes=raw.get("cpt_codes") or [],
            symptoms=raw.get("symptoms"),
            duration_of_symptoms=raw.get("duration_of_symptoms"),
            treatments_tried=raw.get("treatments_tried") or [],
            clinical_findings=raw.get("clinical_findings"),
            ordering_provider=raw.get("ordering_provider"),
            visit_date=raw.get("visit_date"),
            raw_text=raw.get("raw_text"),
            extraction_confidence=raw.get("extraction_confidence", "low"),
        )

    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        return ExtractedClinicalData(
            extraction_confidence="low",
            raw_text="Extraction failed — please type or paste the clinical note manually.",
        )


@router.post("/extract-note", response_model=ExtractNoteResponse)
@limiter.limit("10/minute")
async def extract_note(
    request: Request,
    body: ExtractNoteRequest,
    _user: dict = Depends(verify_token),
) -> ExtractNoteResponse:
    """
    OCR endpoint: extract structured clinical data from a document image.

    Input:  base64-encoded image + mime_type + procedure_type hint
    Output: ExtractedClinicalData for pre-filling the PA form
    """
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required.")

    # Validate base64 can be decoded
    try:
        base64.b64decode(body.image_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="image_base64 is not valid base64.")

    if DEMO_MODE:
        logger.info("extract-note: demo mode — returning mock extraction")
        return ExtractNoteResponse(success=True, extraction=_demo_extraction())

    logger.info(f"extract-note: mime={body.mime_type}, procedure={body.procedure_type}")
    extraction = _extract_via_gemini(body.image_base64, body.mime_type, body.procedure_type)

    return ExtractNoteResponse(success=True, extraction=extraction)
