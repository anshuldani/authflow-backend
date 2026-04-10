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


# ── PA Request / Response ────────────────────────────────────────────────────

class PARequest(BaseModel):
    clinical_note: str
    payer: str                          # payer ID e.g. "bcbs_il", "uhc"
    procedure_type: Optional[str] = None        # "imaging" | "surgery" | "medication"
    procedure_category: Optional[str] = None    # e.g. "imaging_ct", "surgery_orthopedic"
    patient_info: Optional[PatientInfo] = None  # patient demographics (not logged)


class PAResponse(BaseModel):
    success: bool
    payer_name: str
    procedure: Optional[str] = None
    form_sections: List[FormSection]
    raw_justification: str
    confidence: str                      # "high" | "medium" | "low"
    processing_time_ms: Optional[int] = None
    demo_mode: bool = False

    # Top-level fields for frontend display (no parsing of form_sections needed)
    icd10_code: Optional[str] = None
    cpt_code: Optional[str] = None
    criteria_met: Optional[int] = None
    criteria_total: Optional[int] = None
    approval_likelihood: Optional[str] = None   # "high" | "medium" | "low"


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


# ── Note Extraction (OCR) ────────────────────────────────────────────────────

class ExtractNoteRequest(BaseModel):
    image_base64: str                    # base64-encoded image data
    mime_type: str = "image/jpeg"        # "image/jpeg" | "image/png" | "image/webp"
    procedure_type: str = "general"      # hint for extraction context


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
    extraction_confidence: str = "low"   # "high" | "medium" | "low"


class ExtractNoteResponse(BaseModel):
    success: bool
    extraction: ExtractedClinicalData


# ── System ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    rag_loaded: bool
    demo_mode: bool
