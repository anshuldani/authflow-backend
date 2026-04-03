"""
Payer configuration — IDs, display names, policy PDF paths,
and procedure-specific PA criteria summaries used as RAG fallback
when PDF ingestion hasn't run yet.
"""

PAYERS = {
    "bluecross_il": {
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
    "unitedhealthcare": {
        "name": "UnitedHealthcare",
        "short_name": "UnitedHealthcare",
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
# Written to match real payer policy language closely.

SYNTHETIC_POLICIES = {

    "bluecross_il": {
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
"Total knee arthroplasty is medically necessary for this patient with [OA grade] osteoarthritis who has exhausted conservative management including [treatments] over [duration]. Conservative treatment has been limited by [reason if applicable]. Functional assessment demonstrates [findings] impacting activities of daily living."
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

STEP THERAPY FAILURE LANGUAGE:
"Patient has failed adequate trials of conventional systemic therapy including [agent] at [dose] for [duration] due to [inadequate response/intolerance/contraindication]. BSA is [X%] consistent with [moderate/severe] disease. Biologic therapy is medically necessary for adequate disease control."
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

CONSERVATIVE THERAPY REQUIREMENTS (for non-urgent presentations):
- Physical therapy: minimum 4 weeks with documented sessions
- Analgesic therapy: appropriate for diagnosis and duration
- Activity modification as clinically appropriate

CT MYELOGRAM — COVERED INDICATIONS:
1. Contraindication to MRI clearly documented (e.g., pacemaker, MRI-incompatible implant)
2. Need for pre-surgical planning when MRI nondiagnostic
3. Evaluation of nerve root compression when MRI findings inconclusive

DOCUMENTATION REQUIREMENTS:
- Clinical notes documenting symptom duration and severity
- Conservative treatment record (type, duration, response)
- Physical examination findings
- If CT myelogram: explicit MRI contraindication in chart

AETNA MEDICAL NECESSITY LANGUAGE:
"This patient meets Aetna CPB 0609 criteria for [procedure] based on [duration] of [diagnosis] with [neurological findings] who has undergone [conservative treatments] for [duration] without adequate relief. The requested study is necessary to guide further clinical management."
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

STEP THERAPY EXCEPTION CRITERIA:
Step therapy may be waived if:
- Contraindication to all conventional systemic agents
- Patient already on biologic with documented response (continuation)
- Documented organ toxicity risk from conventional agents

AETNA MEDICAL NECESSITY LANGUAGE:
"Per Aetna CPB 0249, patient has moderate-to-severe plaque psoriasis (BSA [X%], DLQI [score]) with documented failure of step therapy including [agent] at [dose] for [duration]. Adalimumab is requested as per protocol following inadequate response/contraindication to first-line systemic therapy."
""",
    },

    "unitedhealthcare": {
        "imaging": """
UNITEDHEALTHCARE MEDICAL POLICY — ADVANCED IMAGING
Policy Number: RAD007.25 — Spine Imaging

LUMBAR SPINE MRI — MEDICAL NECESSITY CRITERIA:
UnitedHealthcare covers lumbar spine MRI when ONE of the following applies:
A. URGENT/EMERGENT (no wait required):
   - Suspected cauda equina syndrome
   - Suspected spinal cord compression
   - Suspected vertebral osteomyelitis or discitis
   - New or progressive neurological deficit

B. NON-URGENT (conservative therapy required first):
   - Radiculopathy with/without neurological findings after ≥4 weeks of conservative care
   - Documented failure of: rest, activity modification, analgesics, AND physical therapy
   - Suspected herniated disc, stenosis, or other structural pathology

CT MYELOGRAM (CPT 72265) CRITERIA:
1. MRI technically contraindicated (pacemaker, cochlear implant, metallic foreign body)
2. MRI technically inadequate or nondiagnostic for clinical question
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
- Vascular disease prohibiting conservative management

MEDICAL NECESSITY STATEMENT:
"[Patient] has Kellgren-Lawrence Grade [X] osteoarthritis of the right/left knee confirmed by X-ray dated [date]. Conservative treatment including [PT duration], [analgesics and duration] has been exhausted. [NSAIDs contraindicated due to CKD/GI/CV if applicable.] Functional assessment demonstrates [limitation]. Total knee arthroplasty is medically necessary."
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
- Repeat MRI within 6 months without change in clinical status or new neurological findings

CT MYELOGRAM — CIGNA CRITERIA:
Coverage when: (a) MRI contraindicated, (b) MRI technically inadequate, or (c) pre-surgical planning

REQUIRED CLINICAL INFORMATION:
1. Date of symptom onset
2. Neurological exam findings (including straight leg raise, reflexes, dermatomal deficit)
3. Conservative treatment description with dates
4. Specific clinical question imaging will answer

CIGNA MEDICAL NECESSITY LANGUAGE:
"The patient presents with [diagnosis, ICD-10] for [duration] with [neurological findings] on examination. Conservative management including [PT/medications] from [date] to [date] has not provided adequate relief. [Imaging type] is medically necessary to evaluate [specific question] and guide clinical management per Cigna Coverage Policy 0336."
""",
    },

    "humana": {
        "imaging": """
HUMANA MEDICAL COVERAGE POLICY — DIAGNOSTIC IMAGING
Policy: HUM-DIAG-007 — Advanced Diagnostic Imaging

LUMBAR SPINE MRI (CPT 72148, 72149, 72158):
Humana considers lumbar spine MRI medically necessary for:
1. Radiculopathy (pain, numbness, or weakness in dermatomal distribution) after ≥4 weeks of:
   - Conservative therapy: physical therapy AND analgesic medication
   - Documented failure to improve with above
2. Myelopathy (spinal cord compression signs)
3. Suspected malignancy, infection, or inflammatory pathology (no wait required)
4. Pre-operative evaluation prior to planned spinal surgery

CT MYELOGRAM (CPT 72265):
Covered when MRI is contraindicated or when pre-surgical CT myelography is needed:
- Documentation required: specific MRI contraindication (e.g., "patient has cardiac pacemaker implanted [date]")

HUMANA DOCUMENTATION CHECKLIST:
□ Primary diagnosis (ICD-10)
□ Symptom onset date
□ Physical exam findings (motor, sensory, reflexes)
□ Conservative treatment: specify type, start date, end date
□ MRI contraindication if CT Myelogram requested
□ Clinical question the imaging will answer

MEDICAL NECESSITY LANGUAGE:
"Pursuant to Humana Policy HUM-DIAG-007, [imaging] is medically necessary for this patient with [diagnosis] presenting with [symptoms] for [duration]. Conservative treatment consisting of [treatment] from [date] to [date] has been undertaken without adequate clinical improvement. Neurological examination reveals [findings]."
""",
    },
}

# ── Demo fallback responses ─────────────────────────────────────────────────
# Used when DEMO_MODE=1 or LLM API is unavailable during demo

DEMO_RESPONSES = {
    "scenario_1": {
        "payer": "bluecross_il",
        "procedure": "CT Myelogram — Lumbar Spine (CPT 72265)",
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Lumbar radiculopathy with suspected herniated disc at L4-L5 (ICD-10: M54.4 — Lumbago with sciatica, left side). Progressive lower back pain radiating to left leg, duration 6 weeks.",
                "policy_citation": "BCBS IL Policy 4.1 — Advanced Diagnostic Imaging"
            },
            {
                "label": "Requested Procedure",
                "content": "CT Myelogram Lumbar Spine (CPT 72265). MRI is contraindicated due to presence of cardiac pacemaker implanted 2019. CT myelogram is the appropriate alternative imaging modality for evaluation of nerve root compression.",
                "policy_citation": "BCBS IL Policy 4.1 — CT Myelogram Covered Indications: MRI contraindication"
            },
            {
                "label": "Clinical Justification",
                "content": "Patient is a 52-year-old female with a 6-week history of progressive lower back pain with left leg radiculopathy rated 8/10. Neurological examination demonstrates decreased sensation in the L4-L5 dermatome, consistent with nerve root compromise. Conservative treatment consisting of NSAIDs and physical therapy over 4 weeks has not provided adequate relief. MRI is contraindicated due to existing cardiac pacemaker (implanted 2019). Patient meets BCBS IL criteria for CT myelogram: (1) MRI contraindication documented, (2) neurological deficit present, (3) conservative treatment attempted for adequate duration.",
                "policy_citation": "BCBS IL Policy 4.1 — CT Myelogram: 'Contraindication to MRI clearly documented'"
            },
            {
                "label": "Supporting Clinical Evidence",
                "content": "• Symptom duration: 6 weeks (exceeds 4-week minimum threshold)\n• Conservative treatment: NSAIDs + physical therapy × 4 weeks — inadequate response\n• Neurological findings: Decreased sensation L4-L5 dermatome on examination\n• MRI contraindication: Cardiac pacemaker (2019) — documented in chart\n• Pain severity: 8/10 impacting functional capacity and activities of daily living\n• Prolonged sitting exacerbates symptoms — functional impairment confirmed",
                "policy_citation": "BCBS IL Documentation Requirements — Section 4.1.3"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "The requested CT myelogram lumbar spine is medically necessary to evaluate nerve root compression in a patient with lumbar radiculopathy who has failed conservative management consisting of NSAIDs and physical therapy over 4 weeks. Neurological examination demonstrates L4-L5 dermatomal sensory deficit. MRI is contraindicated due to cardiac pacemaker implanted in 2019. This imaging will directly inform treatment planning including surgical candidacy evaluation and management decisions.",
                "policy_citation": "BCBS IL Policy 4.1 — Medical Necessity Statement Language"
            }
        ],
        "confidence": "high"
    },
    "scenario_2": {
        "payer": "aetna",
        "procedure": "Adalimumab (Humira) — Moderate-Severe Plaque Psoriasis",
        "form_sections": [
            {
                "label": "Patient Diagnosis",
                "content": "Moderate-to-severe chronic plaque psoriasis (ICD-10: L40.0). Body surface area involvement: 15%, consistent with severe classification per Aetna CPB 0249 threshold (BSA ≥10%).",
                "policy_citation": "Aetna CPB 0249 — Moderate: BSA ≥5%, Severe: BSA ≥10%"
            },
            {
                "label": "Requested Medication",
                "content": "Adalimumab (Humira) 80mg subcutaneous initial dose, then 40mg every other week. Biologic therapy for inadequately controlled moderate-to-severe plaque psoriasis following step therapy failure.",
                "policy_citation": "Aetna CPB 0249 — Biologic Agents for Psoriasis"
            },
            {
                "label": "Step Therapy Documentation",
                "content": "Patient has completed required step therapy per Aetna CPB 0249:\n1. Methotrexate: 15mg/week × 16 weeks — inadequate response (BSA remained >10%)\n2. Topical corticosteroids: Extended course — inadequate response for BSA involvement\nBoth agents trialed at therapeutic doses for adequate duration. Step therapy requirement fulfilled.",
                "policy_citation": "Aetna CPB 0249: 'Methotrexate ≥3 months at therapeutic dose OR documented contraindication'"
            },
            {
                "label": "Medical Necessity Statement",
                "content": "Per Aetna CPB 0249, patient has moderate-to-severe plaque psoriasis (BSA 15%, DLQI significantly impacted) with documented failure of step therapy including methotrexate at 15mg/week for 16 weeks and topical corticosteroids. Adalimumab is requested following inadequate response to first-line systemic therapy. Prescriber is board-certified dermatologist. This request meets all criteria outlined in Aetna CPB 0249.",
                "policy_citation": "Aetna CPB 0249 — Medical Necessity Criteria"
            }
        ],
        "confidence": "high"
    }
}
