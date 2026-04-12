"""
PA Form PDF Generator — produces a filled-out, fax-ready prior authorization form.

One PDF per payer, pre-populated with all patient/clinical/AI-generated data.
Layout mirrors the real BCBS IL / Aetna / UHC / Cigna / Humana PA request forms.
"""

import io
from datetime import date
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import BalancedColumns


# ── Payer visual identity ─────────────────────────────────────────────────────

PAYER_THEME = {
    "bcbs_il": {
        "name": "Blue Cross Blue Shield of Illinois",
        "short": "BCBS of Illinois",
        "primary": HexColor("#003087"),   # BCBS navy blue
        "accent":  HexColor("#0099CC"),
        "pa_phone": "1-800-972-8088",
        "pa_fax":   "1-800-972-8088",
        "form_title": "Prior Authorization Request",
        "form_number": "BCBS-IL-PA-2024",
    },
    "aetna": {
        "name": "Aetna",
        "short": "Aetna",
        "primary": HexColor("#7D1935"),   # Aetna burgundy
        "accent":  HexColor("#C8102E"),
        "pa_phone": "1-800-624-0756",
        "pa_fax":   "1-888-238-6279",
        "form_title": "Prior Authorization / Precertification Request",
        "form_number": "AET-PA-2024",
    },
    "uhc": {
        "name": "UnitedHealthcare",
        "short": "UnitedHealthcare",
        "primary": HexColor("#002677"),   # UHC blue
        "accent":  HexColor("#00AEEF"),
        "pa_phone": "1-866-889-8054",
        "pa_fax":   "1-866-889-8054",
        "form_title": "Prior Authorization Request Form",
        "form_number": "UHC-PAR-2024",
    },
    "cigna": {
        "name": "Cigna",
        "short": "Cigna",
        "primary": HexColor("#006D9F"),   # Cigna blue
        "accent":  HexColor("#00A8E0"),
        "pa_phone": "1-800-244-6224",
        "pa_fax":   "1-800-390-3071",
        "form_title": "Prior Authorization Request",
        "form_number": "CIG-PA-2024",
    },
    "humana": {
        "name": "Humana",
        "short": "Humana",
        "primary": HexColor("#006241"),   # Humana green
        "accent":  HexColor("#78BE20"),
        "pa_phone": "1-800-523-0023",
        "pa_fax":   "1-800-523-0023",
        "form_title": "Prior Authorization Request",
        "form_number": "HUM-PA-2024",
    },
}

DEFAULT_THEME = {
    "name": "Insurance Payer",
    "short": "Payer",
    "primary": HexColor("#1B4FD8"),
    "accent": HexColor("#3B82F6"),
    "pa_phone": "See payer website",
    "pa_fax": "See payer website",
    "form_title": "Prior Authorization Request",
    "form_number": "PA-2024",
}


# ── Style helpers ─────────────────────────────────────────────────────────────

def make_styles(primary_color):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=14,
                                 textColor=white, alignment=TA_CENTER, leading=18),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=8,
                                    textColor=white, alignment=TA_CENTER, leading=10),
        "section_hdr": ParagraphStyle("section_hdr", fontName="Helvetica-Bold", fontSize=9,
                                       textColor=white, alignment=TA_LEFT, leading=12),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=7.5,
                                 textColor=HexColor("#374151"), leading=10),
        "value": ParagraphStyle("value", fontName="Helvetica", fontSize=8.5,
                                 textColor=black, leading=11),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.5,
                                textColor=black, leading=12, spaceAfter=3),
        "body_bold": ParagraphStyle("body_bold", fontName="Helvetica-Bold", fontSize=8.5,
                                     textColor=black, leading=12),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.5,
                                  textColor=HexColor("#6B7280"), leading=10),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=8.5,
                                  textColor=black, leading=12, leftIndent=12, bulletIndent=0),
        "criteria_met": ParagraphStyle("criteria_met", fontName="Helvetica-Bold", fontSize=8,
                                        textColor=HexColor("#15803D"), leading=11),
        "criteria_unmet": ParagraphStyle("criteria_unmet", fontName="Helvetica-Bold", fontSize=8,
                                          textColor=HexColor("#DC2626"), leading=11),
        "highlight": ParagraphStyle("highlight", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=primary_color, leading=12),
        "watermark": ParagraphStyle("watermark", fontName="Helvetica-Bold", fontSize=8,
                                     textColor=HexColor("#DC2626"), alignment=TA_RIGHT),
    }


def section_header(label: str, theme: dict, styles: dict):
    """Colored section header bar."""
    return Table(
        [[Paragraph(label.upper(), styles["section_hdr"])]],
        colWidths=[7.5 * inch],
        rowHeights=[16],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["primary"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]),
    )


def field_row(label: str, value: str, styles: dict, label_width=1.5 * inch, full_width=7.5 * inch):
    """Single label: value row."""
    value_width = full_width - label_width
    return Table(
        [[Paragraph(label, styles["label"]), Paragraph(value or "—", styles["value"])]],
        colWidths=[label_width, value_width],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#E5E7EB")),
        ]),
    )


def two_col_fields(pairs: list[tuple[str, str]], styles: dict):
    """Two-column field grid."""
    rows = []
    for i in range(0, len(pairs), 2):
        left_label, left_val = pairs[i]
        right_label, right_val = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        rows.append([
            Paragraph(left_label, styles["label"]),
            Paragraph(left_val or "—", styles["value"]),
            Paragraph(right_label, styles["label"]),
            Paragraph(right_val or "—", styles["value"]),
        ])
    return Table(
        rows,
        colWidths=[1.2 * inch, 2.4 * inch, 1.2 * inch, 2.4 * inch],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#E5E7EB")),
        ]),
    )


def checkbox_row(label: str, checked: bool, styles: dict):
    mark = "☑" if checked else "☐"
    color_style = styles["criteria_met"] if checked else styles["criteria_unmet"]
    return Table(
        [[Paragraph(f"{mark}  {label}", color_style)]],
        colWidths=[7.5 * inch],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]),
    )


# ── Main generator ────────────────────────────────────────────────────────────

def generate_pa_pdf(
    payer_id: str,
    # Patient
    patient_name: str = "",
    patient_dob: str = "",
    patient_member_id: str = "",
    patient_group_number: str = "",
    patient_plan_name: str = "",
    # Provider
    physician_name: str = "",
    physician_npi: str = "",
    physician_credentials: str = "",
    practice_name: str = "",
    practice_address: str = "",
    practice_city: str = "",
    practice_state: str = "",
    practice_zip: str = "",
    practice_phone: str = "",
    practice_fax: str = "",
    # Service
    procedure_name: str = "",
    cpt_code: str = "",
    cpt_description: str = "",
    icd10_code: str = "",
    icd10_description: str = "",
    service_date: str = "",
    urgency: str = "routine",
    rendering_provider: str = "",
    rendering_facility: str = "",
    # Clinical
    clinical_justification: str = "",
    medical_necessity: str = "",
    supporting_evidence: str = "",
    policy_sections_cited: Optional[list[str]] = None,
    criteria_details: Optional[list[dict]] = None,
    criteria_met: int = 0,
    criteria_total: int = 0,
    approval_likelihood: str = "",
    missing_information: Optional[list[str]] = None,
) -> bytes:
    """
    Generate a complete, filled-out PA form PDF.
    Returns raw PDF bytes for streaming to the client.
    """
    theme = PAYER_THEME.get(payer_id, DEFAULT_THEME)
    styles = make_styles(theme["primary"])
    policy_sections_cited = policy_sections_cited or []
    criteria_details = criteria_details or []
    missing_information = missing_information or []

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.6 * inch,
    )

    story = []

    # ── Page header ───────────────────────────────────────────────────────────
    header_table = Table(
        [[
            Paragraph(theme["name"].upper(), styles["title"]),
        ]],
        colWidths=[7.5 * inch],
        rowHeights=[28],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["primary"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    )
    story.append(header_table)

    sub_header = Table(
        [[
            Paragraph(theme["form_title"].upper(), styles["section_hdr"]),
            Paragraph(f"Form #{theme['form_number']}  |  Date: {date.today().strftime('%m/%d/%Y')}", styles["subtitle"]),
        ]],
        colWidths=[4.5 * inch, 3.0 * inch],
        rowHeights=[14],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["accent"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    )
    story.append(sub_header)

    # Urgency banner
    if urgency and urgency != "routine":
        urgency_color = HexColor("#DC2626") if urgency == "emergent" else HexColor("#D97706")
        urgency_table = Table(
            [[Paragraph(f"⚠  {urgency.upper()} REQUEST — EXPEDITED REVIEW REQUIRED", styles["watermark"])]],
            colWidths=[7.5 * inch],
            rowHeights=[14],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FEF2F2") if urgency == "emergent" else HexColor("#FFFBEB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BOX", (0, 0), (-1, -1), 1, urgency_color),
            ]),
        )
        story.append(urgency_table)

    story.append(Spacer(1, 6))

    # ── Section 1: Patient Information ───────────────────────────────────────
    story.append(section_header("Section 1 — Member / Patient Information", theme, styles))
    story.append(two_col_fields([
        ("Member Name:", patient_name),
        ("Date of Birth:", patient_dob),
        ("Member ID:", patient_member_id),
        ("Group Number:", patient_group_number),
        ("Plan Name:", patient_plan_name),
        ("Request Date:", date.today().strftime("%m/%d/%Y")),
    ], styles))
    story.append(Spacer(1, 6))

    # ── Section 2: Requesting Provider ───────────────────────────────────────
    story.append(section_header("Section 2 — Requesting / Ordering Provider", theme, styles))
    provider_display = physician_name
    if physician_credentials:
        provider_display += f", {physician_credentials}"
    story.append(two_col_fields([
        ("Provider Name:", provider_display),
        ("NPI:", physician_npi),
        ("Practice / Group:", practice_name),
        ("Phone:", practice_phone),
        ("Address:", f"{practice_address}, {practice_city}, {practice_state} {practice_zip}".strip(", ")),
        ("Fax:", practice_fax),
    ], styles))
    if rendering_provider or rendering_facility:
        story.append(two_col_fields([
            ("Rendering Provider:", rendering_provider),
            ("Rendering Facility:", rendering_facility),
        ], styles))
    story.append(Spacer(1, 6))

    # ── Section 3: Service Requested ─────────────────────────────────────────
    story.append(section_header("Section 3 — Service / Procedure Requested", theme, styles))
    story.append(two_col_fields([
        ("Procedure:", procedure_name),
        ("CPT Code:", cpt_code),
        ("CPT Description:", cpt_description),
        ("Requested Date:", service_date or date.today().strftime("%m/%d/%Y")),
        ("Primary Diagnosis:", icd10_description),
        ("ICD-10 Code:", icd10_code),
        ("Urgency:", urgency.capitalize()),
        ("Place of Service:", "Outpatient"),
    ], styles))
    story.append(Spacer(1, 6))

    # ── Section 4: Clinical Justification ────────────────────────────────────
    story.append(section_header("Section 4 — Clinical Justification", theme, styles))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Clinical Justification:", styles["body_bold"]))
    for para in (clinical_justification or "").split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["body"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Medical Necessity Statement:", styles["body_bold"]))
    for para in (medical_necessity or "").split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["body"]))
    story.append(Spacer(1, 6))

    # ── Section 5: Supporting Evidence ───────────────────────────────────────
    story.append(section_header("Section 5 — Supporting Clinical Evidence", theme, styles))
    story.append(Spacer(1, 3))
    if supporting_evidence:
        for line in supporting_evidence.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip existing bullet chars if present
            clean = line.lstrip("•-– ")
            story.append(Paragraph(f"• {clean}", styles["bullet"]))
    story.append(Spacer(1, 6))

    # ── Section 6: Payer Criteria Checklist ───────────────────────────────────
    story.append(section_header(
        f"Section 6 — Payer Criteria Assessment  ({criteria_met}/{criteria_total} Met)",
        theme, styles
    ))
    story.append(Spacer(1, 3))

    if criteria_details:
        for c in criteria_details:
            met = c.get("met", False)
            criterion = c.get("criterion", "")
            evidence = c.get("evidence", "")
            mark = "☑" if met else "☐"
            color_style = styles["criteria_met"] if met else styles["criteria_unmet"]
            story.append(Paragraph(f"{mark}  {criterion}", color_style))
            if evidence:
                story.append(Paragraph(f"     Evidence: {evidence}", styles["small"]))
    elif criteria_met > 0:
        story.append(Paragraph(f"☑  {criteria_met} of {criteria_total} payer criteria satisfied", styles["criteria_met"]))

    if approval_likelihood:
        likelihood_color = {
            "high": HexColor("#15803D"),
            "medium": HexColor("#D97706"),
            "low": HexColor("#DC2626"),
        }.get(approval_likelihood.lower(), black)
        story.append(Spacer(1, 4))
        likelihood_table = Table(
            [[Paragraph(f"Approval Likelihood: {approval_likelihood.upper()}", ParagraphStyle(
                "likelihood", fontName="Helvetica-Bold", fontSize=9,
                textColor=likelihood_color, alignment=TA_CENTER
            ))]],
            colWidths=[7.5 * inch],
            rowHeights=[16],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F9FAFB")),
                ("BOX", (0, 0), (-1, -1), 1, likelihood_color),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]),
        )
        story.append(likelihood_table)

    story.append(Spacer(1, 6))

    # ── Section 7: Policy Citations ───────────────────────────────────────────
    if policy_sections_cited:
        story.append(section_header("Section 7 — Policy Sections Cited", theme, styles))
        story.append(Spacer(1, 3))
        for citation in policy_sections_cited:
            story.append(Paragraph(f"• {citation}", styles["bullet"]))
        story.append(Spacer(1, 6))

    # ── Section 8: Missing Information ───────────────────────────────────────
    if missing_information:
        story.append(section_header("Section 8 — Additional Information That May Strengthen Request", theme, styles))
        story.append(Spacer(1, 3))
        for item in missing_information:
            story.append(Paragraph(f"• {item}", styles["bullet"]))
        story.append(Spacer(1, 6))

    # ── Signature block ───────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#D1D5DB")))
    story.append(Spacer(1, 4))
    sig_table = Table(
        [[
            Paragraph("Ordering Provider Signature: _____________________________", styles["small"]),
            Paragraph(f"Date: _______________", styles["small"]),
        ]],
        colWidths=[5.0 * inch, 2.5 * inch],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]),
    )
    story.append(sig_table)
    story.append(Spacer(1, 4))

    # Footer
    footer_table = Table(
        [[
            Paragraph(f"Submit to: {theme['name']}  |  PA Phone: {theme['pa_phone']}  |  PA Fax: {theme['pa_fax']}", styles["small"]),
            Paragraph("Generated by AuthFlow", styles["small"]),
        ]],
        colWidths=[5.5 * inch, 2.0 * inch],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]),
    )
    story.append(footer_table)

    doc.build(story)
    return buf.getvalue()
