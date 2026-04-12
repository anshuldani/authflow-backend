"""
Payer-specific PA form filler.

BCBS IL / Aetna  — have real AcroForm fields → fill directly with pypdf.
Cigna / Humana / UHC — flat scanned forms → overlay text at exact coordinates
                        using reportlab, then merge with pypdf.

Usage:
    pdf_bytes = fill_pa_form(payer_id, data_dict)
"""

import io
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FORM_PATHS = {
    "bcbs_il": os.path.join(BASE_DIR, "data", "payer_policies", "blue cross blue shield.pdf"),
    "aetna":   os.path.join(BASE_DIR, "data", "payer_policies", "aetna .pdf"),
    "cigna":   os.path.join(BASE_DIR, "data", "payer_policies", "cigna.pdf"),
    "humana":  os.path.join(BASE_DIR, "data", "payer_policies", "humana health.pdf"),
    "uhc":     os.path.join(BASE_DIR, "data", "payer_policies", "united healthcare.pdf"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  AcroForm filler (BCBS + Aetna)
# ─────────────────────────────────────────────────────────────────────────────

def _fill_acroform(pdf_path: str, field_values: dict[str, str],
                   checkbox_values: dict[str, bool] | None = None) -> bytes:
    """Fill a fillable PDF's AcroForm fields and return bytes."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, create_string_object, BooleanObject

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    # Fill text fields
    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values)

    # Fix font sizes + handle checkboxes
    for page in writer.pages:
        if "/Annots" not in page:
            continue
        for annot_ref in page["/Annots"]:
            annot = annot_ref.get_object()
            ft = annot.get("/FT")
            field_name = annot.get("/T", "")
            if isinstance(field_name, bytes):
                field_name = field_name.decode("utf-8", errors="replace")

            # Force consistent 9pt Helvetica on all text fields so nothing overflows
            if ft == NameObject("/Tx"):
                annot[NameObject("/DA")] = create_string_object("/Helvetica 9 Tf 0 g")

            # Set checkboxes — detect the "on" state name from AP/N dict
            if checkbox_values and ft == NameObject("/Btn") and field_name in checkbox_values:
                checked = checkbox_values[field_name]
                # Find the actual "on" state name (/Yes, /On, or custom)
                on_state = "/Yes"
                ap = annot.get("/AP")
                if ap:
                    ap_obj = ap.get_object() if hasattr(ap, 'get_object') else ap
                    n = ap_obj.get("/N")
                    if n:
                        n_obj = n.get_object() if hasattr(n, 'get_object') else n
                        if hasattr(n_obj, 'keys'):
                            states = [k for k in n_obj.keys() if k != "/Off"]
                            if states:
                                on_state = states[0]
                val = on_state if checked else "/Off"
                annot[NameObject("/V")] = NameObject(val)
                annot[NameObject("/AS")] = NameObject(val)

    # NeedAppearances = True so Preview/Acrobat renders values
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  Coordinate overlay (Cigna / Humana / UHC)
# ─────────────────────────────────────────────────────────────────────────────

def _overlay_text(base_pdf_path: str, overlays: list[dict]) -> bytes:
    """
    overlays: list of { page:int, x:float, y_top:float, text:str, size:float }
    y_top is pdfplumber-style (from top of page).  We convert to PDF coords.
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import letter

    reader = PdfReader(base_pdf_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    # Group overlays by page
    by_page: dict[int, list] = {}
    for o in overlays:
        by_page.setdefault(o["page"], []).append(o)

    for page_idx, page_overlays in by_page.items():
        page = reader.pages[page_idx]
        page_h = float(page.mediabox.height)
        page_w = float(page.mediabox.width)

        # Build overlay canvas
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))
        c.setFont("Helvetica", 9)

        for o in page_overlays:
            txt = str(o.get("text", "")).strip()
            if not txt:
                continue
            size = o.get("size", 9)
            x = o["x"]
            # Convert pdfplumber top-from-top to PDF bottom-from-bottom
            pdf_y = page_h - o["y_top"] - size
            c.setFont("Helvetica", size)
            c.drawString(x, pdf_y, txt)

        c.save()
        buf.seek(0)

        # Merge overlay onto page
        from pypdf import PdfReader as PR
        overlay_reader = PR(buf)
        writer_page = writer.pages[page_idx]
        writer_page.merge_page(overlay_reader.pages[0])

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  BCBS IL field map  (90 AcroForm fields)
# ─────────────────────────────────────────────────────────────────────────────

def _split_phone(phone: str) -> tuple[str, str]:
    """Split '(312) 500-5000' → ('312', '5005000') for separate area/number fields."""
    import re
    digits = re.sub(r'\D', '', phone or "")
    if len(digits) == 11 and digits[0] == '1':
        digits = digits[1:]
    if len(digits) == 10:
        return digits[:3], digits[3:]
    return digits[:3] if len(digits) >= 3 else digits, digits[3:] if len(digits) > 3 else ""


def _fill_bcbs(d: dict) -> bytes:
    from datetime import date as _date

    step = d.get("step_therapy") or []
    is_expedited = (d.get("urgency", "routine") or "routine").lower() in ("urgent", "expedited")
    is_renewal = bool(d.get("is_renewal", False))
    today = _date.today().strftime("%m/%d/%Y")

    # Split phone numbers for the separate area-code / number boxes
    p_area, p_num   = _split_phone(d.get("practice_phone", ""))
    f_area, f_num   = _split_phone(d.get("practice_fax", ""))
    pt_area, pt_num = _split_phone(d.get("patient_phone", ""))

    # Section F rationale — split across 3 lines (~200 chars each)
    justification = (d.get("clinical_justification") or "").strip()
    rationale_chunks = [justification[i:i+300] for i in range(0, len(justification), 300)]
    while len(rationale_chunks) < 3:
        rationale_chunks.append("")

    # Section H supporting evidence — concise (not the full justification again)
    evidence = (d.get("supporting_evidence") or d.get("medical_necessity") or "").strip()
    evidence_chunks = [evidence[i:i+300] for i in range(0, len(evidence), 300)]
    while len(evidence_chunks) < 3:
        evidence_chunks.append("")

    fields = {
        # ── Patient (Section B) ─────────────────────────────────────────────
        "Patient Name":                              d.get("patient_name", ""),
        "DOB":                                       d.get("patient_dob", ""),
        "Patient Street Address":                   d.get("patient_address", ""),
        "City":                                      d.get("patient_city", ""),
        "State":                                     d.get("patient_state", ""),
        "ZIP Code":                                  d.get("patient_zip", ""),
        "undefined_3":                               pt_area,
        "undefined_4":                               pt_num,
        "Sex":                                       d.get("patient_sex", ""),
        "Patient Health Plan ID":                   d.get("patient_member_id", ""),
        "Patient Health Plan Group  if applicable": d.get("patient_group_number", ""),

        # ── Provider (Section C) ────────────────────────────────────────────
        "Provider Name":                            _provider_name(d),
        "NPI":                                       d.get("physician_npi", ""),
        "Specialty":                                 d.get("physician_specialty", "") or d.get("physician_credentials", ""),
        "DEA required for controlled substance requests only": d.get("physician_dea", ""),
        "Contact Name":                              d.get("practice_name", ""),
        "undefined_5":                               p_area,        # Contact Phone area code
        "undefined_6":                               p_num,         # Contact Phone number
        "Contact Street Address":                   d.get("practice_address", ""),
        "SuiteRm":                                   "",
        "City_2":                                    d.get("practice_city", ""),
        "State_2":                                   d.get("practice_state", ""),
        "ZIP Code_2":                                d.get("practice_zip", ""),
        "Contact Email optional":                   d.get("practice_email", ""),
        "undefined_7":                               f_area,        # Contact Fax area code
        "undefined_8":                               f_num,         # Contact Fax number
        "Health Plan  Provider ID  if accessible":  "",

        # ── Pharmacy (Section D) — ask user if not provided ──────────────────
        "Pharmacy Name":                             d.get("pharmacy_name", ""),
        "undefined_9":                               d.get("pharmacy_phone_area", ""),
        "undefined_10":                              d.get("pharmacy_phone_num", ""),

        # ── Drug / Procedure (Section E) ────────────────────────────────────
        "E Requested Prescription Drug Information": (
            d.get("drug_brand_name") or d.get("drug_generic_name") or d.get("procedure_name", "")
        ),
        "undefined_11":                              d.get("quantity_requested", ""),  # Qty field (right of drug name)
        "Strength":                                  d.get("dosage_strength", ""),
        "Dosing Schedule":                           d.get("dosing_schedule", ""),
        "Duration":                                  d.get("days_supply", ""),
        # Diagnosis fields:
        # "Diagnosis specific"  = left half of the diagnosis row  → ICD code
        # "undefined_12"        = right half of the same row      → diagnosis description
        # "Place of infusion…"  = the row below (its own named field) → leave blank
        "Diagnosis specific":                        d.get("icd10_code", ""),
        "undefined_12":                              d.get("icd10_description", ""),
        "Place of infusion  injection if applicable": "",

        # ── Section F — Rationale (3 text areas) ────────────────────────────
        "review process 1": rationale_chunks[0],
        "review process 2": rationale_chunks[1],
        "review process 3": rationale_chunks[2],

        # ── Step therapy / failed drugs (Section G) ─────────────────────────
        "Drug Name 1":               step[0].get("drug_name", "") if len(step) > 0 else "",
        "Strength 1":                step[0].get("dose", "")      if len(step) > 0 else "",
        "Dosing Schedule 1":         step[0].get("schedule", "")  if len(step) > 0 else "",
        "Duration 1":                step[0].get("duration", "")  if len(step) > 0 else "",
        "Adverse Event  Specific Failure 1": step[0].get("outcome", "").replace("_", " ") if len(step) > 0 else "",
        "Drug Name 2":               step[1].get("drug_name", "") if len(step) > 1 else "",
        "Strength 2":                step[1].get("dose", "")      if len(step) > 1 else "",
        "Dosing Schedule 2":         step[1].get("schedule", "")  if len(step) > 1 else "",
        "Duration 2":                step[1].get("duration", "")  if len(step) > 1 else "",
        "Adverse Event  Specific Failure 2": step[1].get("outcome", "").replace("_", " ") if len(step) > 1 else "",
        "Drug Name 3":               step[2].get("drug_name", "") if len(step) > 2 else "",
        "Strength 3":                step[2].get("dose", "")      if len(step) > 2 else "",
        "Dosing Schedule 3":         step[2].get("schedule", "")  if len(step) > 2 else "",
        "Duration 3":                step[2].get("duration", "")  if len(step) > 2 else "",
        "Adverse Event  Specific Failure 3": step[2].get("outcome", "").replace("_", " ") if len(step) > 2 else "",

        # ── Section H — Other pertinent info ────────────────────────────────
        "professional opinion is necessary such as relevant diagnostic labs measures response to treatment etc 1": evidence_chunks[0],
        "professional opinion is necessary such as relevant diagnostic labs measures response to treatment etc 2": evidence_chunks[1],
        "professional opinion is necessary such as relevant diagnostic labs measures response to treatment etc 3": evidence_chunks[2],

        # ── Section J — Signature block ─────────────────────────────────────
        "Prescribing Provider":      today,
        "disclosed A person may be committing insurance fraud if false or deceptive information with the intent to": _provider_name(d),
    }

    # Expedited section: only fill phone if expedited
    if is_expedited:
        fields["phone"]   = p_area
        fields["phone_2"] = p_num
        fields["Initials"] = d.get("physician_initials", "")

    checkboxes = {
        "Standard Review Request": not is_expedited,
        "Expedited Review Request I hereby certify that a standard review period may seriously": is_expedited,
        "Initial Authorization Request": not is_renewal,
        "Renewal Request": is_renewal,
        "DAW": False,
    }

    return _fill_acroform(FORM_PATHS["bcbs_il"], fields, checkboxes)


# ─────────────────────────────────────────────────────────────────────────────
#  Aetna field map  (30 AcroForm fields)
# ─────────────────────────────────────────────────────────────────────────────

def _fill_aetna(d: dict) -> bytes:
    from datetime import date
    fields = {
        "Date of Request":                 date.today().strftime("%m/%d/%Y"),
        # Member
        "Name":                            d.get("patient_name", ""),
        "ID Number":                       d.get("patient_member_id", ""),
        "Date of Birth":                   d.get("patient_dob", ""),
        # Requesting provider (Name_2 block)
        "Name_2":                          _provider_name(d),
        "Address":                         _practice_address(d),
        "Telephone":                       d.get("practice_phone", ""),
        "Fax":                             d.get("practice_fax", ""),
        "NPI Number":                      d.get("physician_npi", ""),
        "Contact Person":                  d.get("practice_name", ""),
        # Rendering provider (Name_3 block) — same as requesting for most cases
        "Name_3":                          d.get("rendering_provider", "") or _provider_name(d),
        "Address_2":                       _practice_address(d),
        "Telephone_2":                     d.get("practice_phone", ""),
        "Fax_2":                           d.get("practice_fax", ""),
        "NPI Number_2":                    d.get("physician_npi", ""),
        "Contact Person_2":                d.get("rendering_facility", "") or d.get("practice_name", ""),
        # Facility (Name_4 block) — rendering facility
        "Name_4":                          d.get("rendering_facility", ""),
        "Address_3":                       "",
        "Telephone_3":                     "",
        "Fax_3":                           "",
        "NPI Number_3":                    "",
        "Contact Person_3":                "",
        # Service
        "DiagnosisICD10 Codes":           _icd_line(d),
        "Procedure Item Requested CPTHCPCS CodesRow1":
                                           _cpt_line(d),
        "Date or Span of Appointment or Service Start Date":
                                           d.get("service_date", date.today().strftime("%m/%d/%Y")),
        "End Date":                        "",
        "Number of VisitsQty Required":    d.get("quantity_requested", ""),
    }

    checkboxes = {
        "Check Box1": d.get("urgency", "routine") != "routine",   # Expedited checkbox
    }

    return _fill_acroform(FORM_PATHS["aetna"], fields, checkboxes)


# ─────────────────────────────────────────────────────────────────────────────
#  Cigna overlay  (flat PDF, 612×792)
# ─────────────────────────────────────────────────────────────────────────────

def _fill_cigna(d: dict) -> bytes:
    step = d.get("step_therapy", [])
    overlays = [
        # Physician side (left column)
        {"page": 0, "x": 145, "y_top": 123, "text": _provider_name(d)},
        {"page": 0, "x": 145, "y_top": 144, "text": d.get("physician_specialty", "")},
        {"page": 0, "x": 240, "y_top": 144, "text": d.get("physician_npi", "")},   # DEA/TIN
        {"page": 0, "x": 145, "y_top": 166, "text": d.get("practice_name", "")},   # Contact person
        {"page": 0, "x": 115, "y_top": 187, "text": d.get("practice_phone", "")},  # Office phone
        {"page": 0, "x":  90, "y_top": 208, "text": d.get("practice_fax", "")},    # Office fax
        {"page": 0, "x": 145, "y_top": 229, "text": d.get("practice_address", "")}, # Office addr
        {"page": 0, "x":  75, "y_top": 251, "text": d.get("practice_city", "")},
        {"page": 0, "x": 200, "y_top": 251, "text": d.get("practice_state", "")},
        {"page": 0, "x": 255, "y_top": 251, "text": d.get("practice_zip", "")},
        # Patient side (right column)
        {"page": 0, "x": 380, "y_top": 166, "text": d.get("patient_name", "")},
        {"page": 0, "x": 356, "y_top": 187, "text": d.get("patient_member_id", "")},
        {"page": 0, "x": 520, "y_top": 187, "text": d.get("patient_dob", "")},
        {"page": 0, "x": 415, "y_top": 208, "text": d.get("patient_address", "")},
        {"page": 0, "x": 340, "y_top": 229, "text": d.get("patient_city", "")},
        {"page": 0, "x": 462, "y_top": 229, "text": d.get("patient_state", "")},
        {"page": 0, "x": 526, "y_top": 229, "text": d.get("patient_zip", "")},
        # Urgency row (Standard checkbox area)
        {"page": 0, "x": 130, "y_top": 273, "text": d.get("urgency", "routine").capitalize()},
        # Drug requested
        {"page": 0, "x": 200, "y_top": 313, "text": d.get("drug_brand_name") or d.get("procedure_name", "")},
        {"page": 0, "x": 200, "y_top": 331, "text": d.get("dosage_strength", "")},
        {"page": 0, "x": 380, "y_top": 349, "text": d.get("quantity_requested", "")},
        # Diagnosis
        {"page": 0, "x": 145, "y_top": 367, "text": _icd_line(d)},
        # Clinical justification
        {"page": 0, "x":  36, "y_top": 421, "text": d.get("clinical_justification", "")[:150]},
        {"page": 0, "x":  36, "y_top": 440, "text": d.get("clinical_justification", "")[150:300]},
        # Step therapy drug 1
        {"page": 0, "x": 100, "y_top": 527, "text": step[0]["drug_name"] if step else ""},
        {"page": 0, "x": 230, "y_top": 527, "text": step[0].get("dose", "") if step else ""},
        {"page": 0, "x": 100, "y_top": 550, "text": step[0].get("outcome", "").replace("_", " ") if step else ""},
        # Step therapy drug 2
        {"page": 0, "x": 100, "y_top": 666, "text": step[1]["drug_name"] if len(step) > 1 else ""},
        {"page": 0, "x": 230, "y_top": 666, "text": step[1].get("dose", "") if len(step) > 1 else ""},
        {"page": 0, "x": 100, "y_top": 689, "text": step[1].get("outcome", "").replace("_", " ") if len(step) > 1 else ""},
    ]
    return _overlay_text(FORM_PATHS["cigna"], overlays)


# ─────────────────────────────────────────────────────────────────────────────
#  Humana overlay  (flat PDF, 612×792)
# ─────────────────────────────────────────────────────────────────────────────

def _fill_humana(d: dict) -> bytes:
    overlays = [
        # Header
        {"page": 0, "x": 350, "y_top": 54,  "text": d.get("patient_member_id", "")},   # EOC ID
        # Patient info (left)
        {"page": 0, "x": 145, "y_top": 178, "text": d.get("patient_name", "")},
        {"page": 0, "x": 145, "y_top": 198, "text": d.get("patient_member_id", "")},
        {"page": 0, "x": 145, "y_top": 213, "text": d.get("patient_dob", "")},
        {"page": 0, "x":  80, "y_top": 228, "text": d.get("patient_group_number", "")},
        {"page": 0, "x":  90, "y_top": 243, "text": d.get("patient_address", "")},
        {"page": 0, "x":  90, "y_top": 258, "text": d.get("patient_zip", "")},
        # Provider info (right)
        {"page": 0, "x": 420, "y_top": 178, "text": _provider_name(d)},
        {"page": 0, "x": 360, "y_top": 198, "text": d.get("practice_fax", "")},
        {"page": 0, "x": 510, "y_top": 198, "text": d.get("practice_phone", "")},
        {"page": 0, "x": 400, "y_top": 213, "text": d.get("practice_name", "")},   # Contact
        {"page": 0, "x": 360, "y_top": 228, "text": d.get("physician_npi", "")},
        {"page": 0, "x": 505, "y_top": 228, "text": d.get("physician_npi", "")},   # Payer ID
        {"page": 0, "x": 360, "y_top": 243, "text": d.get("practice_address", "")},
        {"page": 0, "x": 360, "y_top": 258, "text": d.get("practice_zip", "")},
        # Drug info
        {"page": 0, "x": 155, "y_top": 429, "text": d.get("drug_brand_name") or d.get("procedure_name", "")},
        {"page": 0, "x": 170, "y_top": 409, "text": d.get("patient_height", "")},
        {"page": 0, "x": 240, "y_top": 409, "text": d.get("patient_weight", "")},
        {"page": 0, "x": 380, "y_top": 409, "text": d.get("allergies", "")},
        # Diagnosis
        {"page": 0, "x": 145, "y_top": 539, "text": _icd_line(d)},
        # ICD codes
        {"page": 0, "x": 145, "y_top": 616, "text": d.get("icd10_code", "")},
        # Clinical justification (page 1 bottom / page 2)
        {"page": 0, "x":  36, "y_top": 577, "text": d.get("clinical_justification", "")[:200]},
    ]
    return _overlay_text(FORM_PATHS["humana"], overlays)


# ─────────────────────────────────────────────────────────────────────────────
#  UHC overlay  (flat PDF, 612×792)
# ─────────────────────────────────────────────────────────────────────────────

def _fill_uhc(d: dict) -> bytes:
    overlays = [
        # Member info (left column)
        {"page": 0, "x": 120, "y_top": 127, "text": d.get("patient_name", "")},
        {"page": 0, "x":  90, "y_top": 145, "text": d.get("patient_member_id", "")},
        {"page": 0, "x":  95, "y_top": 163, "text": d.get("patient_dob", "")},
        {"page": 0, "x": 110, "y_top": 177, "text": d.get("patient_address", "")},
        {"page": 0, "x":  56, "y_top": 194, "text": d.get("patient_city", "")},
        {"page": 0, "x": 168, "y_top": 194, "text": d.get("patient_state", "")},
        {"page": 0, "x": 245, "y_top": 194, "text": d.get("patient_zip", "")},
        {"page": 0, "x":  80, "y_top": 213, "text": d.get("practice_phone", "")},   # Patient phone
        # Prescriber info (right column)
        {"page": 0, "x": 395, "y_top": 127, "text": _provider_name(d)},
        {"page": 0, "x": 370, "y_top": 145, "text": d.get("physician_npi", "")},
        {"page": 0, "x": 510, "y_top": 145, "text": d.get("physician_specialty", "")},
        {"page": 0, "x": 393, "y_top": 163, "text": d.get("practice_phone", "")},
        {"page": 0, "x": 370, "y_top": 177, "text": d.get("practice_fax", "")},
        {"page": 0, "x": 395, "y_top": 193, "text": d.get("practice_address", "")},
        {"page": 0, "x": 345, "y_top": 213, "text": d.get("practice_city", "")},
        {"page": 0, "x": 445, "y_top": 213, "text": d.get("practice_state", "")},
        {"page": 0, "x": 520, "y_top": 213, "text": d.get("practice_zip", "")},
        # Medication
        {"page": 0, "x": 115, "y_top": 236, "text": d.get("drug_brand_name") or d.get("procedure_name", "")},
        {"page": 0, "x":  75, "y_top": 299, "text": d.get("drug_brand_name") or d.get("procedure_name", "")},
        {"page": 0, "x": 470, "y_top": 298, "text": d.get("dosage_strength", "")},
        {"page": 0, "x":  95, "y_top": 314, "text": "Once daily"},
        {"page": 0, "x": 470, "y_top": 313, "text": d.get("quantity_requested", "")},
        # ICD-10 / Diagnosis
        {"page": 0, "x": 110, "y_top": 402, "text": _icd_line(d)},
    ]
    return _overlay_text(FORM_PATHS["uhc"], overlays)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _provider_name(d: dict) -> str:
    name = d.get("physician_name", "")
    creds = d.get("physician_credentials", "")
    return f"{name}, {creds}".strip(", ") if creds else name


def _practice_address(d: dict) -> str:
    parts = [
        d.get("practice_address", ""),
        d.get("practice_city", ""),
        d.get("practice_state", ""),
        d.get("practice_zip", ""),
    ]
    return ", ".join(p for p in parts if p)


def _icd_line(d: dict) -> str:
    code = d.get("icd10_code", "")
    desc = d.get("icd10_description", "")
    return f"{code} - {desc}".strip(" -") if code else desc


def _cpt_line(d: dict) -> str:
    code = d.get("cpt_code", "")
    desc = d.get("cpt_description", "") or d.get("procedure_name", "")
    return f"{code} - {desc}".strip(" -") if code else desc


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def fill_pa_form(payer_id: str, data: dict) -> bytes:
    """
    Fill the payer's actual PA form with the provided data dict.
    Falls back to None if the payer form PDF is missing.

    data keys (all optional, use whatever is available):
        patient_name, patient_dob, patient_member_id, patient_group_number,
        patient_sex, patient_address, patient_city, patient_state, patient_zip,
        physician_name, physician_npi, physician_credentials, physician_specialty, physician_dea,
        practice_name, practice_address, practice_city, practice_state, practice_zip,
        practice_phone, practice_fax,
        rendering_provider, rendering_facility,
        procedure_name, cpt_code, cpt_description,
        icd10_code, icd10_description,
        drug_brand_name, drug_generic_name, dosage_strength, quantity_requested, days_supply,
        dosing_schedule, allergies, patient_height, patient_weight,
        clinical_justification, medical_necessity, supporting_evidence,
        step_therapy (list of {drug_name, dose, duration, outcome}),
        urgency, is_renewal, service_date, generated_date,
    """
    payer_id = payer_id.lower()
    form_path = FORM_PATHS.get(payer_id)
    if not form_path or not os.path.exists(form_path):
        logger.warning(f"No form PDF for payer {payer_id}")
        return b""

    try:
        if payer_id == "bcbs_il":
            return _fill_bcbs(data)
        elif payer_id == "aetna":
            return _fill_aetna(data)
        elif payer_id == "cigna":
            return _fill_cigna(data)
        elif payer_id == "humana":
            return _fill_humana(data)
        elif payer_id == "uhc":
            return _fill_uhc(data)
        else:
            return b""
    except Exception as e:
        logger.error(f"PDF fill failed for {payer_id}: {e}", exc_info=True)
        return b""


# ─────────────────────────────────────────────────────────────────────────────
#  Missing fields detector
# ─────────────────────────────────────────────────────────────────────────────

# Fields that can't be auto-filled from clinical notes — need the practitioner
MISSING_FIELDS_SPEC = {
    "bcbs_il": [
        {"key": "patient_address",   "label": "Patient street address",   "type": "text",   "section": "Patient"},
        {"key": "patient_city",      "label": "Patient city",             "type": "text",   "section": "Patient"},
        {"key": "patient_state",     "label": "Patient state",            "type": "text",   "section": "Patient", "maxLength": 2},
        {"key": "patient_zip",       "label": "Patient ZIP code",         "type": "text",   "section": "Patient", "maxLength": 10},
        {"key": "patient_phone",     "label": "Patient phone number",     "type": "tel",    "section": "Patient"},
        {"key": "patient_sex",       "label": "Patient sex",              "type": "select", "section": "Patient", "options": ["Male", "Female", "Other"]},
        {"key": "physician_specialty","label": "Physician specialty",     "type": "text",   "section": "Provider"},
        {"key": "practice_fax",      "label": "Practice fax number",      "type": "tel",    "section": "Provider"},
        {"key": "pharmacy_name",     "label": "Pharmacy name",            "type": "text",   "section": "Pharmacy"},
        {"key": "pharmacy_phone",    "label": "Pharmacy phone",           "type": "tel",    "section": "Pharmacy"},
    ],
    "aetna": [
        {"key": "patient_address",   "label": "Patient street address",   "type": "text",   "section": "Patient"},
        {"key": "patient_phone",     "label": "Patient phone number",     "type": "tel",    "section": "Patient"},
        {"key": "practice_fax",      "label": "Practice fax number",      "type": "tel",    "section": "Provider"},
    ],
}


def get_missing_fields(payer_id: str, data: dict) -> list[dict]:
    """
    Return list of fields that are required on the payer form but not present in data.
    Each entry: {key, label, type, section, options?, maxLength?}
    """
    specs = MISSING_FIELDS_SPEC.get(payer_id.lower(), [])
    missing = []
    for spec in specs:
        val = data.get(spec["key"], "")
        if not val or not str(val).strip():
            missing.append(spec)
    return missing
