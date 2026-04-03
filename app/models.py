from pydantic import BaseModel
from typing import Optional, List


class PARequest(BaseModel):
    clinical_note: str
    payer: str                  # payer ID e.g. "bluecross_il"
    procedure_type: Optional[str] = None  # e.g. "imaging", "surgery", "medication"


class FormSection(BaseModel):
    label: str
    content: str
    policy_citation: Optional[str] = None


class PAResponse(BaseModel):
    success: bool
    payer_name: str
    procedure: Optional[str]
    form_sections: List[FormSection]
    raw_justification: str
    confidence: str             # "high" | "medium" | "low"
    processing_time_ms: Optional[int] = None
    demo_mode: bool = False


class AppealRequest(BaseModel):
    clinical_note: str
    payer: str
    denial_reason: str
    original_pa_form: Optional[str] = None


class AppealSection(BaseModel):
    label: str
    content: str
    policy_citation: Optional[str] = None


class AppealResponse(BaseModel):
    success: bool
    payer_name: str
    denial_reason: str
    appeal_sections: List[AppealSection]
    key_citations: List[str]
    demo_mode: bool = False


class PayerInfo(BaseModel):
    id: str
    name: str
    short_name: str
    market_share: str
    logo_placeholder: str


class PayersResponse(BaseModel):
    payers: List[PayerInfo]


class HealthResponse(BaseModel):
    status: str
    version: str
    rag_loaded: bool
    demo_mode: bool
