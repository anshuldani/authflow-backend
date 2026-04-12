from pydantic import BaseModel
from typing import Optional, List


# ── Shared sub-models ────────────────────────────────────────────────────────

class PatientInfo(BaseModel):
    """Patient demographics and service details — never stored in logs."""
    patient_name: Optional[str] = None
    patient_dob: Optional[str] = None           # MM/DD/YYYY
    patient_member_id: Optional[str] = None
    patient_group_number: Optional[str] = None
    patient_plan_name: Optional[str] = None
    requested_service_date: Optional[str] = None
    urgency: str = "routine"                     # "routine" | "urgent" | "emergent"
    rendering_provider_name: Optional[str] = None
    rendering_facility_name: Optional[str] = None


class FormSection(BaseModel):
    label: str
    content: str
    policy_citation: Optional[str] = None


class AppealSection(BaseModel):
    label: str
    content: str
    policy_citation: Optional[str] = None


class CriterionDetail(BaseModel):
    """One payer criterion with met/unmet status and supporting evidence."""
    criterion: str
    met: bool
    evidence: str


# ── PA Request / Response ────────────────────────────────────────────────────

class PARequest(BaseModel):
    clinical_note: str = ""
    payer: str                               # payer ID e.g. "bcbs_il", "uhc"
    procedure_type: Optional[str] = None     # "imaging" | "surgery" | "medication"
    procedure_category: Optional[str] = None # e.g. "imaging_ct", "surgery_orthopedic"
    patient_info: Optional[PatientInfo] = None
    image_base64: Optional[str] = None       # base64-encoded image — optional


class PAResponse(BaseModel):
    """
    Response shape is intentionally a superset of the frontend's GeneratedForm type.
    All GeneratedForm fields are present as top-level fields so the frontend can use
    this response directly without parsing form_sections.

    Frontend GeneratedForm ↔ PAResponse field mapping:
      icd10_code            → icd10_code
      icd10_description     → icd10_description
      cpt_code              → cpt_code
      cpt_description       → cpt_description
      clinical_justification→ clinical_justification
      medical_necessity     → medical_necessity
      supporting_evidence   → supporting_evidence
      policy_sections_cited → policy_sections_cited
      criteria_met          → criteria_met
      criteria_total        → criteria_total
      criteria_details      → criteria_details
      approval_likelihood   → approval_likelihood
      approval_reasoning    → approval_reasoning
      missing_information   → missing_information
    """
    success: bool
    payer_name: str
    procedure: Optional[str] = None
    form_sections: List[FormSection]         # Rich display blocks (keep for existing UI)
    raw_justification: str
    confidence: str                          # "high" | "medium" | "low"
    processing_time_ms: Optional[int] = None
    demo_mode: bool = False

    # ── GeneratedForm-compatible flat fields ──────────────────────────────────
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    cpt_code: Optional[str] = None
    cpt_description: Optional[str] = None
    clinical_justification: Optional[str] = None
    medical_necessity: Optional[str] = None
    supporting_evidence: Optional[str] = None
    policy_sections_cited: List[str] = []
    criteria_met: Optional[int] = None
    criteria_total: Optional[int] = None
    criteria_details: List[CriterionDetail] = []
    approval_likelihood: Optional[str] = None  # "high" | "medium" | "low"
    approval_reasoning: Optional[str] = None
    missing_information: List[str] = []


# ── Appeal Request / Response ────────────────────────────────────────────────

class AppealRequest(BaseModel):
    clinical_note: str
    payer: str
    denial_reason: str
    original_pa_form: Optional[str] = None


class AppealResponse(BaseModel):
    success: bool
    payer_name: str
    denial_reason: str
    appeal_sections: List[AppealSection]
    key_citations: List[str]
    demo_mode: bool = False


# ── Payer List ───────────────────────────────────────────────────────────────

class PayerInfo(BaseModel):
    id: str
    name: str
    short_name: str
    market_share: str
    logo_placeholder: str


class PayersResponse(BaseModel):
    payers: List[PayerInfo]


# ── Simple OCR response (ocr_engine.py / brief-compatible shape) ────────────

class NoteExtractionResponse(BaseModel):
    success: bool
    extracted_text: str
    confidence: str          # "high" | "medium" | "low"
    method: str              # "gemini_vision" | "tesseract" | "failed"
    raw_text: Optional[str] = None


# ── Note Extraction (OCR) ────────────────────────────────────────────────────

class ExtractNoteRequest(BaseModel):
    image_base64: str
    mime_type: str = "image/jpeg"
    procedure_type: str = "general"


class ExtractedClinicalData(BaseModel):
    patient_name: Optional[str] = None
    patient_dob: Optional[str] = None
    diagnosis: Optional[str] = None
    icd10_codes: List[str] = []
    procedure_requested: Optional[str] = None
    cpt_codes: List[str] = []
    symptoms: Optional[str] = None
    duration_of_symptoms: Optional[str] = None
    treatments_tried: List[str] = []
    clinical_findings: Optional[str] = None
    ordering_provider: Optional[str] = None
    visit_date: Optional[str] = None
    raw_text: Optional[str] = None
    extraction_confidence: str = "low"


class ExtractNoteResponse(BaseModel):
    success: bool
    extraction: ExtractedClinicalData


# ── System ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    rag_loaded: bool
    demo_mode: bool


# ── Validator helpers ────────────────────────────────────────────────────────
from pydantic import field_validator
import re

CPT_PATTERN = re.compile(r'^\d{5}$')
ICD10_PATTERN = re.compile(r'^[A-Z]\d{2}(\.\d+)?$')

def validate_cpt_code(v: str) -> str:
    if v and not CPT_PATTERN.match(v.strip()):
        raise ValueError(f"Invalid CPT code format: {v}")
    return v.strip()

def validate_icd10_code(v: str) -> str:
    if v and not ICD10_PATTERN.match(v.strip().upper()):
        raise ValueError(f"Invalid ICD-10 code format: {v}")
    return v.strip().upper()
