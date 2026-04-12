"""
Payer configuration — IDs, display names, policy PDF paths,
and procedure-specific PA criteria used as RAG fallback.

Payer ID conventions (match frontend lib/types.ts PAYERS array):
  bcbs_il, aetna, uhc, cigna, humana
"""

PAYERS = {
    "bcbs_il": {
        "name": "Blue Cross Blue Shield of Illinois",
        "short_name": "Blue Cross IL",
        "market_share": "~35% IL market",
        "policy_pdf_paths": [
            "data/payer_policies/bcbs_il_imaging.pdf",
            "data/payer_policies/bcbs_il_surgery.pdf",
            "data/payer_policies/bcbs_il_pt.pdf",
            "data/payer_policies/bcbs_il_biologics.pdf",
        ],
        "logo_placeholder": "BCBS",
    },
    "aetna": {
        "name": "Aetna",
        "short_name": "Aetna",
        "market_share": "~14% national",
        "policy_pdf_paths": [
            "data/payer_policies/aetna_imaging.pdf",
            "data/payer_policies/aetna_surgery.pdf",
            "data/payer_policies/aetna_biologics.pdf",
        ],
        "logo_placeholder": "AET",
    },
    "uhc": {
        "name": "UnitedHealthcare",
        "short_name": "UHC",
        "market_share": "~15% national",
        "policy_pdf_paths": [
            "data/payer_policies/uhc_imaging.pdf",
            "data/payer_policies/uhc_surgery.pdf",
        ],
        "logo_placeholder": "UHC",
    },
    "cigna": {
        "name": "Cigna",
        "short_name": "Cigna",
        "market_share": "~10% national",
        "policy_pdf_paths": [
            "data/payer_policies/cigna_imaging.pdf",
            "data/payer_policies/cigna_surgery.pdf",
        ],
        "logo_placeholder": "CIG",
    },
    "humana": {
        "name": "Humana",
        "short_name": "Humana",
        "market_share": "~9% national",
        "policy_pdf_paths": [
            "data/payer_policies/humana_imaging.pdf",
            "data/payer_policies/humana_biologics.pdf",
        ],
        "logo_placeholder": "HUM",
    },
}

# ── Synthetic policy criteria ──────────────────────────────────────────────
# Used as RAG content when real PDFs are not yet ingested.

SYNTHETIC_POLICIES = {

    "bcbs_il": {
        "imaging": """
BLUE CROSS BLUE SHIELD OF ILLINOIS — IMAGING PRIOR AUTHORIZATION CRITERIA
Policy Section 4.1 — Advanced Diagnostic Imaging (MRI, CT, CT Myelogram)

COVERED INDICATIONS — MRI Lumbar Spine (CPT 72148, 72149, 72158):
- Low back pain persisting ≥6 weeks despite conservative treatment
- Conservative treatment defined as: minimum 4 weeks of NSAIDs AND physical therapy
- Neurological deficit present (radiculopathy, motor weakness, sensory loss)
- Red flag symptoms: bowel/bladder dysfunction, unexplained weight loss, fever, history of malignancy
- Failed previous imaging if clinically indicated

COVERED INDICATIONS — CT Myelogram Lumbar Spine (CPT 72265):
- Contraindication to MRI (pacemaker, cochlear implant, certain metallic implants)
- Inconclusive MRI results requiring further characterization
- Pre-surgical planning when MRI is nondiagnostic
- Documented MRI contraindication required in clinical notes

REQUIRED DOCUMENTATION:
1. Duration of symptoms (minimum 6 weeks for non-urgent)
2. Conservative treatment attempted and duration (minimum 4 weeks)
3. Current medications and duration
4. Neurological examination findings
5. Clinical indication and specific diagnostic question
6. MRI contraindication documentation if CT Myelogram requested

CLINICAL NECESSITY STATEMENT LANGUAGE:
"The requested imaging is medically necessary to evaluate [specific clinical question] in a patient with [diagnosis] who has failed conservative management consisting of [treatments] over [duration]. Neurological examination demonstrates [findings]. The imaging will directly inform treatment planning and management."

DENIAL CRITERIA:
- Conservative treatment < 4 weeks (unless red flags present)
- Routine screening without specific clinical indication
- Duplicate imaging within 6 months without change in clinical status
""",
        "surgery": """
BLUE CROSS BLUE SHIELD OF ILLINOIS — SURGICAL PRIOR AUTHORIZATION CRITERIA
Policy Section 6.2 — Elective Orthopedic Surgery

TOTAL KNEE REPLACEMENT (CPT 27447):
REQUIRED CRITERIA (ALL must be met):
1. Moderate to severe osteoarthritis documented on X-ray (Kellgren-Lawrence Grade III or IV)
2. Failure of conservative treatment ≥6 months including:
   - Physical therapy (minimum 6 sessions)
   - NSAIDs or analgesics (unless contraindicated)
   - Activity modification
3. Significant functional impairment documented (walking limitation, ADL impact)
4. BMI <40 preferred (higher BMI requires additional documentation)

CONTRAINDICATIONS THAT SUPPORT SURGICAL APPROVAL:
- NSAID contraindication due to renal disease, GI bleeding history, or cardiovascular risk
- Physical therapy contraindication documented by treating physician

REQUIRED DOCUMENTATION:
1. X-ray report confirming OA grade
2. Conservative treatment log with dates and duration
3. Functional assessment (pain scale, ROM measurements)
4. Physician narrative supporting medical necessity
5. Anesthesia clearance if applicable

MEDICAL NECESSITY LANGUAGE:
"Total knee arthroplasty is medically necessary for this patient with [OA grade] osteoarthritis who has exhausted conservative management including [treatments] over [duration]. Functional assessment demonstrates [findings] impacting activities of daily living."
""",
        "medication": """
BLUE CROSS BLUE SHIELD OF ILLINOIS — SPECIALTY DRUG PRIOR AUTHORIZATION
Policy Section 8.1 — Biologic Agents for Inflammatory Conditions

ADALIMUMAB (HUMIRA) FOR PLAQUE PSORIASIS:
REQUIRED CRITERIA:
1. Diagnosis of moderate-to-severe chronic plaque psoriasis
   - Moderate: BSA 5-10% OR DLQI >10 OR involvement of face/hands/feet/genitalia
   - Severe: BSA >10% OR DLQI >10 significantly impacting quality of life
2. Step therapy — FAILURE of at least ONE conventional systemic agent:
   - Methotrexate (adequate dose ≥15mg/week for minimum 12 weeks)
   - Cyclosporine (adequate dose for minimum 12 weeks)
   - Acitretin (adequate dose for minimum 12 weeks)
   Failure defined as: inadequate response, intolerance, or contraindication
3. Prescriber must be board-certified dermatologist

REQUIRED DOCUMENTATION:
1. BSA or PASI score at baseline
2. DLQI score
3. Prior treatment history with dates, doses, duration, and outcome
4. Reason for step therapy failure (inadequate response / intolerance / contraindication)
5. Current photos or documented clinical description
""",
    },

    "aetna": {
        "imaging": """
AETNA CLINICAL POLICY BULLETIN — DIAGNOSTIC IMAGING
CPB 0609 — Spine MRI and CT Myelography

MRI LUMBAR SPINE — COVERED INDICATIONS:
Aetna considers lumbar spine MRI medically necessary for:
1. Radiculopathy with neurological signs or symptoms persisting after ≥4 weeks conservative therapy
2. Suspected spinal cord compression or cauda equina syndrome (urgent — no conservative therapy wait)
3. Suspected infection, malignancy, or inflammatory arthropathy
4. Pre-operative evaluation for surgical candidates
5. Failure to respond to appropriate conservative therapy with persistent symptoms

CT MYELOGRAM — COVERED INDICATIONS:
1. Contraindication to MRI clearly documented
2. Need for pre-surgical planning when MRI nondiagnostic
3. Evaluation of nerve root compression when MRI findings inconclusive

DOCUMENTATION REQUIREMENTS:
- Clinical notes documenting symptom duration and severity
- Conservative treatment record (type, duration, response)
- Physical examination findings
""",
        "biologics": """
AETNA CLINICAL POLICY BULLETIN — BIOLOGIC AGENTS
CPB 0249 — Psoriasis Biologics

ADALIMUMAB FOR MODERATE-TO-SEVERE PLAQUE PSORIASIS:
Aetna considers adalimumab (Humira) medically necessary when ALL of the following are met:
1. Diagnosis confirmed as moderate-to-severe plaque psoriasis:
   - Moderate: BSA ≥5% or clinically significant involvement of special body areas
   - Severe: BSA ≥10% or PASI ≥12
2. Step therapy requirement — documented failure or contraindication to:
   - Methotrexate: ≥3 months at therapeutic dose OR documented contraindication/intolerance
   - One other conventional systemic agent (cyclosporine, acitretin) OR documented contraindication
3. Prescribed by or in consultation with a dermatologist

AUTHORIZATION PERIOD: 6 months initial; renewal requires documented response
""",
    },

    "uhc": {
        "imaging": """
UNITEDHEALTHCARE MEDICAL POLICY — ADVANCED IMAGING
Policy Number: RAD007.25 — Spine Imaging

LUMBAR SPINE MRI — MEDICAL NECESSITY CRITERIA:
UnitedHealthcare covers lumbar spine MRI when ONE of the following applies:
A. URGENT/EMERGENT (no wait required):
   - Suspected cauda equina syndrome
   - Suspected spinal cord compression
   - New or progressive neurological deficit

B. NON-URGENT (conservative therapy required first):
   - Radiculopathy with/without neurological findings after ≥4 weeks of conservative care
   - Documented failure of: rest, activity modification, analgesics, AND physical therapy

CT MYELOGRAM (CPT 72265) CRITERIA:
1. MRI technically contraindicated
2. MRI technically inadequate or nondiagnostic
3. Pre-surgical planning as adjunct to MRI

DOCUMENTATION TO SUBMIT:
□ Diagnosis with ICD-10 code
□ Symptom onset date and description
□ Conservative treatment with specific dates
□ Neurological exam findings
□ If CT myelogram: MRI contraindication letter or note

TOTAL KNEE REPLACEMENT (CPT 27447):
Required: X-ray OA Grade III-IV, ≥6 months conservative care, documented functional limitation, NSAID trial (or documented contraindication)
""",
        "surgery": """
UNITEDHEALTHCARE MEDICAL POLICY — ORTHOPEDIC SURGERY
Policy Number: ORTH.018 — Total Joint Replacement

TOTAL KNEE ARTHROPLASTY — COVERAGE CRITERIA:
UnitedHealthcare considers total knee replacement medically necessary when:
1. Radiographic evidence of moderate-to-severe osteoarthritis (Kellgren-Lawrence Grade III or IV)
2. Significant pain and functional limitation despite NON-SURGICAL treatment ≥6 months including:
   - Physical therapy/rehabilitation (documented)
   - Pharmacological management: acetaminophen, NSAIDs, or intra-articular injections
   - Activity modification and weight management counseling
3. Functional impairment documented: limited ambulation, inability to perform ADLs
4. Medical and surgical clearance obtained

EXCEPTION — CONSERVATIVE THERAPY NOT REQUIRED when:
- NSAIDs contraindicated (renal insufficiency CKD stage ≥3, GI bleeding history, CV risk)
- Physical therapy medically contraindicated

MEDICAL NECESSITY STATEMENT:
"[Patient] has Kellgren-Lawrence Grade [X] osteoarthritis confirmed by X-ray dated [date]. Conservative treatment including [PT duration], [analgesics] has been exhausted. [NSAIDs contraindicated due to CKD/GI/CV if applicable.] Total knee arthroplasty is medically necessary."
""",
    },

    "cigna": {
        "imaging": """
CIGNA COVERAGE POLICY — DIAGNOSTIC IMAGING
Coverage Policy Number: 0336 — Spine MRI

LUMBAR SPINE MRI — COVERAGE CRITERIA:
Cigna covers lumbar MRI as medically necessary when:
- Patient has low back pain with radicular component AND
- Symptoms persist for 4 or more weeks AND
- Conservative treatment has been tried without adequate improvement:
  * Physical therapy (documented attendance, minimum 4 weeks)
  * Analgesic medications appropriate to presentation
- Neurological signs present on examination OR clinical suspicion of surgical pathology

CIGNA WILL NOT COVER:
- MRI for acute back pain without neurological signs, duration < 4 weeks
- Repeat MRI within 6 months without change in clinical status

REQUIRED CLINICAL INFORMATION:
1. Date of symptom onset
2. Neurological exam findings (including straight leg raise, reflexes, dermatomal deficit)
3. Conservative treatment description with dates
4. Specific clinical question imaging will answer
""",
    },

    "humana": {
        "imaging": """
HUMANA MEDICAL COVERAGE POLICY — DIAGNOSTIC IMAGING
Policy: HUM-DIAG-007 — Advanced Diagnostic Imaging

LUMBAR SPINE MRI (CPT 72148, 72149, 72158):
Humana considers lumbar spine MRI medically necessary for:
1. Radiculopathy after ≥4 weeks of conservative therapy including PT and analgesics
2. Myelopathy (spinal cord compression signs)
3. Suspected malignancy, infection, or inflammatory pathology (no wait required)
4. Pre-operative evaluation prior to planned spinal surgery

CT MYELOGRAM (CPT 72265):
Covered when MRI is contraindicated or when pre-surgical CT myelography is needed.

HUMANA DOCUMENTATION CHECKLIST:
□ Primary diagnosis (ICD-10)
□ Symptom onset date
□ Physical exam findings (motor, sensory, reflexes)
□ Conservative treatment: specify type, start date, end date
□ MRI contraindication if CT Myelogram requested
""",
    },
}

# ── Demo fallback responses ─────────────────────────────────────────────────
# 5 scenarios covering:
#   1. CT Myelogram — Blue Cross IL (bcbs_il)         [approval]
#   2. Adalimumab/Humira — Aetna                       [approval]
#   3. Total Knee Replacement — UHC (uhc)              [approval]
#   4. Lumbar MRI — Cigna                              [denial — insufficient conservative care]
#   5. Humana biologics — Adalimumab                   [approval after step therapy]

DEMO_RESPONSES = {
    # ── Scenario 1: CT Myelogram, bcbs_il ──────────────────────────────────
    "scenario_1": {
        "payer": "bcbs_il",
        "procedure": "CT Myelogram — Lumbar Spine (CPT 72265)",
        "icd10_code": "M54.42",
        "icd10_description": "Lumbago with sciatica, left side",
        "cpt_code": "72265",
        "cpt_description": "Myelography via lumbar injection including radiological supervision and interpretation",
        "criteria_met": 3,
        "criteria_total": 3,
        "approval_likelihood": "high",
        "approval_reasoning": "All 3 criteria met: MRI contraindicated by documented cardiac pacemaker, neurological deficit present at L4-L5, and conservative treatment (NSAIDs + PT ×4 weeks) completed.",
        "missing_information": [],
        "criteria_details": [
            {"criterion": "MRI contraindication documented", "met": True, "evidence": "Cardiac pacemaker implanted March 2019 — documented in chart"},
            {"criterion": "Neurological deficit present", "met": True, "evidence": "Decreased sensation L4-L5 dermatome on examination"},
            {"criterion": "Conservative treatment ≥4 weeks completed", "met": True, "evidence": "NSAIDs (naproxen 500mg BID) + physical therapy ×4 weeks with inadequate response"}
        ],
        "policy_sections_cited": [
            "BCBS IL Policy 4.1 — CT Myelogram: MRI contraindication covered indication",
            "BCBS IL Policy 4.1 — CT Myelogram: 'Contraindication to MRI clearly documented'",
            "BCBS IL Documentation Requirements — Section 4.1.3",
            "BCBS IL Policy 4.1 — Medical Necessity Statement Language"
        ],
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Lumbar radiculopathy with suspected herniated disc at L4-L5 (ICD-10: M54.42 — Lumbago with sciatica, left side). Progressive lower back pain radiating to left leg, duration 6 weeks.",
                "policy_citation": "BCBS IL Policy 4.1 — Advanced Diagnostic Imaging"
            },
            {
                "label": "Requested Procedure",
                "content": "CT Myelogram Lumbar Spine (CPT 72265). MRI is contraindicated due to presence of cardiac pacemaker implanted 2019. CT myelogram is the appropriate alternative imaging modality.",
                "policy_citation": "BCBS IL Policy 4.1 — CT Myelogram: MRI contraindication covered indication"
            },
            {
                "label": "Clinical Justification",
                "content": "Patient is a 52-year-old female with a 6-week history of progressive lower back pain with left leg radiculopathy rated 8/10. Neurological examination demonstrates decreased sensation in the L4-L5 dermatome. Conservative treatment (NSAIDs + physical therapy ×4 weeks) has not provided adequate relief. MRI is contraindicated due to existing cardiac pacemaker (2019). Patient meets all three BCBS IL criteria for CT myelogram: (1) MRI contraindication documented, (2) neurological deficit present, (3) conservative treatment attempted for adequate duration.",
                "policy_citation": "BCBS IL Policy 4.1 — CT Myelogram: 'Contraindication to MRI clearly documented'"
            },
            {
                "label": "Supporting Clinical Evidence",
                "content": "• Symptom duration: 6 weeks (exceeds 4-week minimum threshold)\n• Conservative treatment: NSAIDs + physical therapy ×4 weeks — inadequate response\n• Neurological findings: Decreased sensation L4-L5 dermatome on examination\n• MRI contraindication: Cardiac pacemaker (2019) — documented in chart\n• Pain severity: 8/10 impacting activities of daily living",
                "policy_citation": "BCBS IL Documentation Requirements — Section 4.1.3"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "The requested CT myelogram lumbar spine is medically necessary to evaluate nerve root compression in a patient with lumbar radiculopathy (M54.42) who has failed conservative management consisting of NSAIDs and physical therapy over 4 weeks. Neurological examination demonstrates L4-L5 dermatomal sensory deficit. MRI is contraindicated due to cardiac pacemaker implanted 2019. This imaging will directly inform surgical candidacy and treatment planning.",
                "policy_citation": "BCBS IL Policy 4.1 — Medical Necessity Statement Language"
            }
        ],
        "clinical_justification": "Patient is a 52-year-old female with a 6-week history of progressive lower back pain with left leg radiculopathy rated 8/10. Neurological examination demonstrates decreased sensation in the L4-L5 dermatome. Conservative treatment (NSAIDs + physical therapy ×4 weeks) has not provided adequate relief. MRI is contraindicated due to existing cardiac pacemaker (2019). Patient meets all three BCBS IL criteria for CT myelogram: (1) MRI contraindication documented, (2) neurological deficit present, (3) conservative treatment attempted for adequate duration.",
        "medical_necessity": "The requested CT myelogram lumbar spine is medically necessary to evaluate nerve root compression in a patient with lumbar radiculopathy (M54.42) who has failed conservative management consisting of NSAIDs and physical therapy over 4 weeks. MRI is contraindicated due to cardiac pacemaker implanted 2019. This imaging will directly inform surgical candidacy and treatment planning.",
        "supporting_evidence": "• Symptom duration: 6 weeks (exceeds 4-week minimum threshold)\n• Conservative treatment: NSAIDs + physical therapy ×4 weeks — inadequate response\n• Neurological findings: Decreased sensation L4-L5 dermatome on examination\n• MRI contraindication: Cardiac pacemaker (2019) — documented in chart\n• Pain severity: 8/10 impacting activities of daily living",
        "confidence": "high"
    },

    # ── Scenario 2: Adalimumab / Humira, Aetna ─────────────────────────────
    "scenario_2": {
        "payer": "aetna",
        "procedure": "Adalimumab (Humira) — Moderate-Severe Plaque Psoriasis",
        "icd10_code": "L40.0",
        "icd10_description": "Psoriasis vulgaris (plaque psoriasis)",
        "cpt_code": "J0135",
        "cpt_description": "Injection, adalimumab, 20mg",
        "criteria_met": 3,
        "criteria_total": 3,
        "approval_likelihood": "high",
        "approval_reasoning": "All 3 Aetna CPB 0249 criteria met: severe plaque psoriasis (BSA 15% ≥10%), step therapy failure documented (methotrexate ×16 weeks), and prescriber is board-certified dermatologist.",
        "missing_information": [],
        "criteria_details": [
            {"criterion": "Moderate-to-severe plaque psoriasis (BSA ≥10% or PASI ≥12)", "met": True, "evidence": "BSA 15% — exceeds severe threshold of ≥10% per Aetna CPB 0249"},
            {"criterion": "Step therapy: methotrexate ≥3 months at therapeutic dose", "met": True, "evidence": "Methotrexate 15mg/week ×16 weeks — inadequate response documented"},
            {"criterion": "Prescribed by or in consultation with dermatologist", "met": True, "evidence": "Board-certified dermatologist prescriber documented"}
        ],
        "policy_sections_cited": [
            "Aetna CPB 0249 — Severe: BSA ≥10%",
            "Aetna CPB 0249 — Biologic Agents for Psoriasis",
            "Aetna CPB 0249: 'Methotrexate ≥3 months at therapeutic dose'",
            "Aetna CPB 0249 — Documentation Requirements",
            "Aetna CPB 0249 — Medical Necessity Criteria"
        ],
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Moderate-to-severe chronic plaque psoriasis (ICD-10: L40.0). Body surface area involvement: 15%, consistent with severe classification per Aetna CPB 0249 threshold (BSA ≥10%).",
                "policy_citation": "Aetna CPB 0249 — Severe: BSA ≥10%"
            },
            {
                "label": "Requested Medication",
                "content": "Adalimumab (Humira) 80mg SC initial dose, then 40mg every other week (J0135). Biologic therapy for inadequately controlled moderate-to-severe plaque psoriasis following step therapy failure.",
                "policy_citation": "Aetna CPB 0249 — Biologic Agents for Psoriasis"
            },
            {
                "label": "Step Therapy Documentation",
                "content": "Patient has completed required step therapy per Aetna CPB 0249:\n1. Methotrexate: 15mg/week ×16 weeks — inadequate response (BSA remained >10%)\n2. Topical corticosteroids: Extended course — inadequate response for BSA involvement\nBoth agents trialed at therapeutic doses for adequate duration. Step therapy requirement fulfilled.",
                "policy_citation": "Aetna CPB 0249: 'Methotrexate ≥3 months at therapeutic dose'"
            },
            {
                "label": "Supporting Clinical Evidence",
                "content": "• BSA: 15% (severe per Aetna CPB 0249 threshold of ≥10%)\n• DLQI: Significantly impacted\n• Step therapy failure: Methotrexate 15mg/week ×16 weeks — inadequate response\n• Prescriber: Board-certified dermatologist\n• Baseline labs completed (TB test, CBC, LFTs)",
                "policy_citation": "Aetna CPB 0249 — Documentation Requirements"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "Per Aetna CPB 0249, patient has moderate-to-severe plaque psoriasis (BSA 15%, DLQI significantly impacted) with documented failure of step therapy including methotrexate at 15mg/week for 16 weeks. Adalimumab is requested following inadequate response to first-line systemic therapy. Prescriber is board-certified dermatologist. This request meets all criteria outlined in Aetna CPB 0249.",
                "policy_citation": "Aetna CPB 0249 — Medical Necessity Criteria"
            }
        ],
        "clinical_justification": "Patient has severe plaque psoriasis (BSA 15%, exceeding Aetna CPB 0249 severe threshold of ≥10%). Step therapy per CPB 0249 has been completed: methotrexate 15mg/week ×16 weeks with inadequate response (BSA remained >10%). Prescriber is board-certified dermatologist. All three Aetna CPB 0249 criteria are satisfied.",
        "medical_necessity": "Per Aetna CPB 0249, patient has moderate-to-severe plaque psoriasis (BSA 15%, DLQI significantly impacted) with documented failure of step therapy including methotrexate at 15mg/week for 16 weeks. Adalimumab is requested following inadequate response to first-line systemic therapy. Prescriber is board-certified dermatologist.",
        "supporting_evidence": "• BSA: 15% (severe per Aetna CPB 0249 threshold of ≥10%)\n• DLQI: Significantly impacted\n• Step therapy failure: Methotrexate 15mg/week ×16 weeks — inadequate response\n• Prescriber: Board-certified dermatologist\n• Baseline labs completed (TB test, CBC, LFTs)",
        "confidence": "high"
    },

    # ── Scenario 3: Total Knee Replacement, UHC ─────────────────────────────
    "scenario_3": {
        "payer": "uhc",
        "procedure": "Total Knee Arthroplasty — Right Knee (CPT 27447)",
        "icd10_code": "M17.11",
        "icd10_description": "Primary osteoarthritis, right knee",
        "cpt_code": "27447",
        "cpt_description": "Arthroplasty, knee, condyle and plateau; medial and lateral compartments with or without patella resurfacing (total knee arthroplasty)",
        "criteria_met": 4,
        "criteria_total": 4,
        "approval_likelihood": "high",
        "approval_reasoning": "All 4 UHC ORTH.018 criteria met: KL Grade IV confirmed on X-ray, ≥6 months conservative care (8 months), significant functional impairment documented, and NSAIDs now contraindicated by CKD Stage 3 satisfying the exception criterion.",
        "missing_information": [],
        "criteria_details": [
            {"criterion": "Radiographic OA Grade III or IV (Kellgren-Lawrence)", "met": True, "evidence": "KL Grade IV tricompartmental OA on standing AP X-ray"},
            {"criterion": "Conservative treatment ≥6 months (PT, analgesics, injections)", "met": True, "evidence": "8 months: PT ×12 sessions, acetaminophen + NSAIDs + 2 corticosteroid injections"},
            {"criterion": "Functional impairment documented (ADL limitation)", "met": True, "evidence": "Pain 9/10, unable to walk >1 block, unable to climb stairs"},
            {"criterion": "NSAIDs trialed or contraindicated", "met": True, "evidence": "NSAIDs contraindicated due to CKD Stage 3 (GFR 42) — UHC exception criterion satisfied"}
        ],
        "policy_sections_cited": [
            "UHC Policy ORTH.018 — Radiographic evidence required: KL Grade III or IV",
            "UHC Policy ORTH.018 — Total Joint Replacement coverage criteria",
            "UHC Policy ORTH.018 — Functional impairment criteria",
            "UHC ORTH.018 Documentation Requirements",
            "UHC Policy ORTH.018 — Medical Necessity Statement"
        ],
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Primary osteoarthritis, right knee (ICD-10: M17.11). Kellgren-Lawrence Grade IV tricompartmental osteoarthritis confirmed on standing AP X-ray dated 3 weeks ago. Severe functional limitation with inability to walk more than one block.",
                "policy_citation": "UHC Policy ORTH.018 — Radiographic evidence required: KL Grade III or IV"
            },
            {
                "label": "Requested Procedure",
                "content": "Total knee arthroplasty, right knee (CPT 27447). Procedure is indicated for end-stage osteoarthritis refractory to conservative management. Patient is a suitable surgical candidate per orthopedic surgery evaluation.",
                "policy_citation": "UHC Policy ORTH.018 — Total Joint Replacement coverage criteria"
            },
            {
                "label": "Clinical Justification",
                "content": "Patient is a 68-year-old male with Kellgren-Lawrence Grade IV right knee osteoarthritis. Conservative treatment over 8 months has included: physical therapy (12 sessions), acetaminophen 1g TID, naproxen 500mg BID ×3 months, and two intra-articular corticosteroid injections with only temporary relief. NSAIDs have been trialed but are now limited due to CKD Stage 3 (GFR 42). Functional assessment documents pain score 9/10, inability to walk >1 block, inability to climb stairs, and significant ADL impairment. Patient meets all four UHC ORTH.018 criteria.",
                "policy_citation": "UHC Policy ORTH.018 — Functional impairment criteria"
            },
            {
                "label": "Supporting Clinical Evidence",
                "content": "• Imaging: KL Grade IV tricompartmental OA on standing X-ray (date documented)\n• Conservative treatment duration: 8 months (exceeds 6-month requirement)\n• Physical therapy: 12 sessions documented with minimal improvement\n• Pharmacological management: Acetaminophen + NSAIDs + intra-articular injections trialed\n• NSAID limitation: CKD Stage 3 (GFR 42) — NSAIDs now contraindicated\n• Functional impairment: Pain 9/10, walking <1 block, unable to climb stairs\n• Surgical clearance: Cardiology and anesthesia pre-op clearance obtained",
                "policy_citation": "UHC ORTH.018 Documentation Requirements"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "This patient has Kellgren-Lawrence Grade IV osteoarthritis of the right knee confirmed by X-ray. Conservative treatment including 12 sessions of physical therapy, analgesics, and two corticosteroid injections over 8 months has been exhausted without adequate relief. NSAIDs are now contraindicated due to CKD Stage 3 (GFR 42), satisfying the UHC exception criteria for conservative therapy limitation. Functional assessment demonstrates severe impairment affecting ambulation and activities of daily living. Total knee arthroplasty is medically necessary per UHC Policy ORTH.018.",
                "policy_citation": "UHC Policy ORTH.018 — Medical Necessity Statement"
            }
        ],
        "clinical_justification": "Patient is a 68-year-old male with Kellgren-Lawrence Grade IV right knee osteoarthritis. Conservative treatment over 8 months has included physical therapy (12 sessions), acetaminophen 1g TID, naproxen 500mg BID ×3 months, and two intra-articular corticosteroid injections with only temporary relief. NSAIDs are now contraindicated due to CKD Stage 3 (GFR 42). Functional assessment documents pain score 9/10, inability to walk >1 block, and significant ADL impairment. Patient meets all four UHC ORTH.018 criteria.",
        "medical_necessity": "This patient has KL Grade IV osteoarthritis of the right knee confirmed by X-ray. Conservative treatment including PT ×12 sessions, analgesics, and two corticosteroid injections over 8 months has been exhausted. NSAIDs are now contraindicated due to CKD Stage 3 (GFR 42), satisfying the UHC exception criteria. Total knee arthroplasty is medically necessary per UHC Policy ORTH.018.",
        "supporting_evidence": "• Imaging: KL Grade IV tricompartmental OA on standing X-ray\n• Conservative treatment duration: 8 months (exceeds 6-month requirement)\n• Physical therapy: 12 sessions with minimal improvement\n• Pharmacological management: Acetaminophen + NSAIDs + 2 intra-articular injections trialed\n• NSAID limitation: CKD Stage 3 (GFR 42) — NSAIDs now contraindicated\n• Functional impairment: Pain 9/10, walking <1 block, unable to climb stairs\n• Surgical clearance: Cardiology and anesthesia pre-op clearance obtained",
        "confidence": "high"
    },

    # ── Scenario 4: Lumbar MRI — Cigna — DENIED (insufficient conservative care)
    "scenario_4": {
        "payer": "cigna",
        "procedure": "MRI Lumbar Spine (CPT 72148)",
        "icd10_code": "M54.5",
        "icd10_description": "Low back pain, unspecified",
        "cpt_code": "72148",
        "cpt_description": "MRI, spinal canal and contents, lumbar; without contrast material",
        "criteria_met": 1,
        "criteria_total": 3,
        "approval_likelihood": "low",
        "approval_reasoning": "Denial anticipated: symptom duration only 2 weeks (Cigna requires ≥4 weeks) and no conservative treatment documented before requesting imaging.",
        "missing_information": [
            "Symptom duration must reach 4 weeks before resubmission",
            "Documentation of conservative treatment (NSAIDs + physical therapy ≥4 weeks)",
            "Neurological examination findings if deficit develops"
        ],
        "criteria_details": [
            {"criterion": "Diagnosis documented with ICD-10", "met": True, "evidence": "Low back pain M54.5 documented"},
            {"criterion": "Symptom duration ≥4 weeks", "met": False, "evidence": "Only 2 weeks — Cigna requires minimum 4 weeks for non-urgent presentations"},
            {"criterion": "Conservative treatment ≥4 weeks (PT + analgesics)", "met": False, "evidence": "No PT or analgesic trial documented prior to imaging request"}
        ],
        "policy_sections_cited": [
            "Cigna Coverage Policy 0336 — Lumbar Spine MRI",
            "Cigna Coverage Policy 0336 — Denial Criteria: duration <4 weeks, no conservative treatment",
            "Cigna Coverage Policy 0336 — Documentation Requirements",
            "Cigna Coverage Policy 0336 — Non-Coverage Statement"
        ],
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Low back pain (ICD-10: M54.5). Acute onset lower back pain, duration 2 weeks. No neurological deficit identified on examination. Patient requesting MRI for evaluation.",
                "policy_citation": "Cigna Coverage Policy 0336 — Lumbar Spine MRI"
            },
            {
                "label": "Requested Procedure",
                "content": "MRI Lumbar Spine without contrast (CPT 72148). Requested for evaluation of acute low back pain.",
                "policy_citation": "Cigna Coverage Policy 0336"
            },
            {
                "label": "Clinical Justification",
                "content": "CRITERIA GAP IDENTIFIED — This request does not meet Cigna Coverage Policy 0336 criteria at this time:\n\nCriteria Met (1 of 3):\n✓ Diagnosis documented: Low back pain (M54.5)\n\nCriteria NOT Met (2 of 3):\n✗ Symptom duration: 2 weeks (Cigna requires ≥4 weeks for non-urgent presentations)\n✗ Conservative treatment: No documented PT or adequate analgesic trial (Cigna requires minimum 4 weeks)\n\nRecommendation: Initiate conservative treatment (NSAIDs + physical therapy) and resubmit after 4 weeks if symptoms persist. Expedited approval may be considered if neurological deficit develops.",
                "policy_citation": "Cigna Coverage Policy 0336 — Denial Criteria: duration <4 weeks, no conservative treatment"
            },
            {
                "label": "Supporting Clinical Evidence",
                "content": "• Symptom duration: 2 weeks (below 4-week threshold)\n• Conservative treatment: None documented prior to imaging request\n• Neurological exam: No deficit on examination (straight leg raise negative, reflexes intact)\n• Red flags: None identified (no fever, weight loss, bowel/bladder symptoms, history of malignancy)\n• Pain score: 6/10",
                "policy_citation": "Cigna Coverage Policy 0336 — Documentation Requirements"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "DENIAL ANTICIPATED — Per Cigna Coverage Policy 0336, MRI lumbar spine is not covered for acute low back pain of <4 weeks duration without neurological deficit and without a documented trial of conservative therapy. Current request does not meet coverage criteria. Clinical recommendation: begin NSAIDs and physical therapy, resubmit at 4-6 weeks if inadequate response. If neurological deficit develops (new radiculopathy, motor weakness), resubmit immediately as urgent.",
                "policy_citation": "Cigna Coverage Policy 0336 — Non-Coverage Statement"
            }
        ],
        "clinical_justification": "CRITERIA GAP IDENTIFIED — This request does not meet Cigna Coverage Policy 0336 criteria at this time. Criteria met (1 of 3): diagnosis documented (M54.5). Criteria not met (2 of 3): symptom duration only 2 weeks (requires ≥4 weeks) and no conservative treatment documented. Recommendation: initiate NSAIDs + PT and resubmit after 4 weeks.",
        "medical_necessity": "Per Cigna Coverage Policy 0336, MRI lumbar spine is not covered for acute low back pain of <4 weeks duration without neurological deficit and without a documented trial of conservative therapy. Resubmit after 4 weeks of NSAIDs and physical therapy if symptoms persist.",
        "supporting_evidence": "• Symptom duration: 2 weeks (below 4-week threshold)\n• Conservative treatment: None documented prior to imaging request\n• Neurological exam: No deficit (SLR negative, reflexes intact)\n• Red flags: None identified\n• Pain score: 6/10",
        "confidence": "low"
    },

    # ── Scenario 5: Adalimumab — Humana — Approval after step therapy ───────
    "scenario_5": {
        "payer": "humana",
        "procedure": "Adalimumab (Humira) — Rheumatoid Arthritis (CPT J0135)",
        "icd10_code": "M05.79",
        "icd10_description": "Rheumatoid arthritis with rheumatoid factor, multiple sites",
        "cpt_code": "J0135",
        "cpt_description": "Injection, adalimumab, 20mg",
        "criteria_met": 4,
        "criteria_total": 4,
        "approval_likelihood": "high",
        "approval_reasoning": "All 4 Humana HUM-0589 criteria met: moderate-to-severe seropositive RA confirmed (DAS28 5.2), failure of ≥2 conventional DMARDs documented, negative TB screening, and board-certified rheumatologist prescriber.",
        "missing_information": [],
        "criteria_details": [
            {"criterion": "Moderate-to-severe active RA confirmed (DAS28 ≥3.2)", "met": True, "evidence": "DAS28 5.2, CRP 3.8 mg/dL, ESR 62 mm/hr — active moderate-to-severe disease"},
            {"criterion": "Seropositive RA (RF or anti-CCP positive)", "met": True, "evidence": "RF positive and anti-CCP positive documented"},
            {"criterion": "Failure of ≥2 conventional DMARDs at adequate dose/duration", "met": True, "evidence": "MTX 20mg/week ×6mo + HCQ 400mg ×4mo — both inadequate response"},
            {"criterion": "TB screening negative before anti-TNF initiation", "met": True, "evidence": "QuantiFERON-TB Gold negative"}
        ],
        "policy_sections_cited": [
            "Humana Policy HUM-0589 — Biologic DMARD Coverage Criteria",
            "Humana Policy HUM-0589 — Anti-TNF biologics for RA",
            "Humana Policy HUM-0589 — 'Failure of ≥2 conventional DMARDs'",
            "Humana Policy HUM-0589 — Documentation Requirements",
            "Humana Policy HUM-0589 — Medical Necessity Criteria"
        ],
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Seropositive rheumatoid arthritis, multiple joints (ICD-10: M05.79). Moderate-to-severe active RA with DAS28 score of 5.2 despite conventional DMARD therapy. Elevated CRP (3.8 mg/dL) and ESR (62 mm/hr).",
                "policy_citation": "Humana Policy HUM-0589 — Biologic DMARD Coverage Criteria"
            },
            {
                "label": "Requested Medication",
                "content": "Adalimumab (Humira) 40mg SC every other week (J0135). Anti-TNF biologic therapy for moderate-to-severe seropositive RA refractory to conventional DMARD therapy.",
                "policy_citation": "Humana Policy HUM-0589 — Anti-TNF biologics for RA"
            },
            {
                "label": "Step Therapy Documentation",
                "content": "Patient has completed required step therapy per Humana Policy HUM-0589:\n1. Methotrexate 20mg/week ×6 months — inadequate response (DAS28 remained ≥3.2)\n2. Hydroxychloroquine 400mg daily ×4 months — inadequate response\n3. Combination MTX + sulfasalazine ×3 months — inadequate response, GI intolerance to sulfasalazine\nAll conventional DMARDs trialed at adequate doses for adequate duration. Step therapy requirement fulfilled.",
                "policy_citation": "Humana Policy HUM-0589 — 'Failure of ≥2 conventional DMARDs'"
            },
            {
                "label": "Supporting Clinical Evidence",
                "content": "• DAS28 score: 5.2 (moderate-to-severe active disease)\n• CRP: 3.8 mg/dL (elevated — confirms active inflammation)\n• ESR: 62 mm/hr (elevated)\n• RF positive, anti-CCP positive (seropositive RA confirmed)\n• Step therapy: MTX ×6mo + HCQ ×4mo + MTX+SSZ ×3mo — all with inadequate response\n• TB screening: QuantiFERON-TB Gold negative\n• Prescriber: Board-certified rheumatologist",
                "policy_citation": "Humana Policy HUM-0589 — Documentation Requirements"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "Per Humana Policy HUM-0589, adalimumab is medically necessary for this patient with moderate-to-severe seropositive rheumatoid arthritis (M05.79, DAS28 5.2) who has failed adequate trials of conventional DMARDs including methotrexate at 20mg/week ×6 months and hydroxychloroquine ×4 months with documented inadequate response. TB screening is negative. Prescriber is board-certified rheumatologist. All criteria outlined in HUM-0589 are satisfied.",
                "policy_citation": "Humana Policy HUM-0589 — Medical Necessity Criteria"
            }
        ],
        "clinical_justification": "Patient has moderate-to-severe seropositive RA (DAS28 5.2, CRP 3.8 mg/dL, RF+/anti-CCP+) refractory to conventional DMARD therapy. Step therapy per HUM-0589 completed: methotrexate 20mg/week ×6 months and hydroxychloroquine 400mg ×4 months — both with inadequate response. TB screening negative. Prescriber is board-certified rheumatologist. All four Humana HUM-0589 criteria satisfied.",
        "medical_necessity": "Per Humana Policy HUM-0589, adalimumab is medically necessary for this patient with moderate-to-severe seropositive RA (M05.79, DAS28 5.2) who has failed conventional DMARDs including methotrexate ×6 months and hydroxychloroquine ×4 months. TB screening is negative. Prescriber is board-certified rheumatologist.",
        "supporting_evidence": "• DAS28 score: 5.2 (moderate-to-severe active disease)\n• CRP: 3.8 mg/dL (elevated)\n• ESR: 62 mm/hr (elevated)\n• RF positive, anti-CCP positive (seropositive RA confirmed)\n• Step therapy: MTX ×6mo + HCQ ×4mo — all with inadequate response\n• TB screening: QuantiFERON-TB Gold negative\n• Prescriber: Board-certified rheumatologist",
        "confidence": "high"
    },
}


# ── Payer config cache ────────────────────────────────────────────────────────
_payer_cache: dict = {}

def get_payer_config(payer_id: str) -> dict | None:
    """Return payer config from in-memory cache; populate on first call."""
    global _payer_cache
    if not _payer_cache:
        _payer_cache = {p["id"]: p for p in PAYERS}
    return _payer_cache.get(payer_id)

def invalidate_payer_cache() -> None:
    """Clear payer cache (call after config reload)."""
    global _payer_cache
    _payer_cache = {}
