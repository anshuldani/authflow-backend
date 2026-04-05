"""
Appeal Generator — generates appeal letters that quote the payer's
own policy language against their denial decision.

This is AuthFlow's most powerful feature:
"We found the specific policy clause you violated when you denied this claim."
"""

import os
import json
import time
import logging
from typing import Optional

from app.models import AppealRequest, AppealResponse, AppealSection
from app.payer_config import PAYERS

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

APPEAL_PROMPT = """You are a medical billing appeals specialist with extensive experience overturning insurance denials. Your appeals have a near-100% success rate because you quote the insurance company's own policy language to demonstrate their denial was incorrect.

PAYER: {payer_name}
DENIAL REASON: {denial_reason}

PAYER'S OWN POLICY REQUIREMENTS:
{payer_criteria}

ORIGINAL CLINICAL NOTE:
{clinical_note}

YOUR TASK:
Write a formal prior authorization appeal letter that:
1. Acknowledges the denial
2. Quotes the payer's SPECIFIC policy language that the denial contradicts
3. Documents exactly how the patient meets each criterion
4. Demands reconsideration based on the payer's own published criteria

OUTPUT FORMAT — Return ONLY valid JSON:
{{
  "appeal_sections": [
    {{
      "label": "Denial Reference",
      "content": "Formal acknowledgment of the denial and the stated reason",
      "policy_citation": null
    }},
    {{
      "label": "Policy Language Review",
      "content": "Quote the EXACT policy criteria that applies to this case. Show that the patient meets the stated criteria.",
      "policy_citation": "Exact policy section and page"
    }},
    {{
      "label": "Clinical Evidence Supporting Approval",
      "content": "Specific clinical facts from the note that satisfy each denial criterion. Be granular — cite duration, test results, treatment history.",
      "policy_citation": "Policy documentation requirements"
    }},
    {{
      "label": "Denial Criteria Analysis",
      "content": "Analyze the denial reason against the policy. Show specifically why the denial reason does not apply to this patient's case.",
      "policy_citation": "Policy denial criteria section"
    }},
    {{
      "label": "Request for Reconsideration",
      "content": "Formal demand for immediate reconsideration. Request peer-to-peer review if applicable. State that continued denial may constitute a violation of the patient's coverage rights.",
      "policy_citation": null
    }}
  ],
  "key_citations": [
    "List of the most powerful policy quotes that support the appeal",
    "Each entry should be a direct quote from the policy criteria provided"
  ]
}}"""


DEMO_APPEAL_RESPONSE = {
    "payer": "bluecross_il",
    "denial_reason": "conservative treatment not exhausted",
    "appeal_sections": [
        {
            "label": "Denial Reference",
            "content": "We are writing to formally appeal the denial of prior authorization for CT Myelogram Lumbar Spine (CPT 72265) for our patient, a 52-year-old female with lumbar radiculopathy (ICD-10: M54.4). The denial cited 'conservative treatment not exhausted.' We respectfully disagree and provide the following clinical evidence demonstrating that this patient fully satisfies Blue Cross Blue Shield of Illinois coverage criteria.",
            "policy_citation": None
        },
        {
            "label": "Policy Language Review",
            "content": "Per BCBS IL Clinical Policy 4.1 — Advanced Diagnostic Imaging, the criteria for CT Myelogram approval include: (1) 'Contraindication to MRI clearly documented' — our patient has a cardiac pacemaker implanted in 2019, which is a standard absolute contraindication to MRI; and (2) 'Conservative treatment defined as minimum 4 weeks of NSAIDs AND physical therapy.' Our patient has completed 4 weeks of both NSAIDs and physical therapy with inadequate response. Both coverage criteria are fully satisfied.",
            "policy_citation": "BCBS IL Policy 4.1 — CT Myelogram Covered Indications"
        },
        {
            "label": "Clinical Evidence Supporting Approval",
            "content": "The clinical record documents the following facts, each directly satisfying a BCBS IL coverage criterion:\n\n• Symptom duration: 6 weeks (exceeds the 4-week minimum threshold in Policy 4.1)\n• Conservative treatment: NSAIDs prescribed and taken for 4 weeks — meets the 'minimum 4 weeks NSAIDs' criterion\n• Physical therapy: Completed 4 weeks of physical therapy — meets the 'minimum 4 weeks PT' criterion\n• Treatment outcome: Inadequate response to both conservative treatments — criterion for failed conservative care satisfied\n• MRI contraindication: Cardiac pacemaker implanted 2019 — absolute contraindication to MRI, documented in chart\n• Neurological deficit: Decreased sensation in L4-L5 dermatome on examination — neurological finding documented\n\nEvery criterion stated in Policy 4.1 is satisfied by the clinical record.",
            "policy_citation": "BCBS IL Policy 4.1 — Documentation Requirements 4.1.3"
        },
        {
            "label": "Denial Criteria Analysis",
            "content": "The denial reason states 'conservative treatment not exhausted.' BCBS IL Policy 4.1 defines conservative treatment as 'minimum 4 weeks of NSAIDs AND physical therapy.' Our patient completed exactly this duration of both treatments. The denial criterion — conservative treatment not exhausted — does not apply to this patient because:\n\n1. Conservative treatment IS exhausted: 4 weeks NSAIDs + 4 weeks PT completed with inadequate response\n2. CT Myelogram (not MRI) was requested because MRI is contraindicated by pacemaker — this is an independent coverage criterion that does not require additional conservative treatment\n\nThe denial appears to apply MRI imaging criteria to a CT Myelogram request, which has a separate coverage pathway (MRI contraindication). We request immediate review by a board-certified radiologist or relevant specialist.",
            "policy_citation": "BCBS IL Policy 4.1 — Denial Criteria"
        },
        {
            "label": "Request for Reconsideration",
            "content": "Based on the above documentation, we formally request immediate reconsideration of this prior authorization denial. Our patient meets every criterion outlined in BCBS IL Policy 4.1 for CT Myelogram coverage. The treating physician is available for a peer-to-peer review call at the payer's earliest convenience. Continued denial of medically necessary imaging for a patient with documented neurological deficit and MRI contraindication may delay diagnosis and constitute a breach of the patient's coverage rights under the Illinois Insurance Code. We request a decision within 72 hours.",
            "policy_citation": None
        }
    ],
    "key_citations": [
        "BCBS IL Policy 4.1: 'Conservative treatment defined as minimum 4 weeks of NSAIDs AND physical therapy' — patient completed 4 weeks of both",
        "BCBS IL Policy 4.1: 'Contraindication to MRI clearly documented' — cardiac pacemaker 2019 is absolute MRI contraindication",
        "BCBS IL Policy 4.1: CT Myelogram covered when 'MRI is contraindicated' — independent coverage pathway, no additional conservative treatment required"
    ]
}


def generate_appeal(request: AppealRequest, payer_criteria: str) -> AppealResponse:
    """Generate an appeal letter for a denied PA."""
    start_time = time.time()
    payer_info = PAYERS.get(request.payer, {})
    payer_name = payer_info.get("name", request.payer)

    if DEMO_MODE:
        return _get_demo_appeal(request, payer_name)

    # Try LLM
    try:
        from app.form_generator import get_llm
        llm = get_llm()

        if llm:
            prompt = APPEAL_PROMPT.format(
                payer_name=payer_name,
                denial_reason=request.denial_reason,
                payer_criteria=payer_criteria,
                clinical_note=request.clinical_note,
            )

            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            content = content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip().rstrip("```").strip()

            data = json.loads(content)
            sections = [
                AppealSection(
                    label=s["label"],
                    content=s["content"],
                    policy_citation=s.get("policy_citation"),
                )
                for s in data.get("appeal_sections", [])
            ]

            return AppealResponse(
                success=True,
                payer_name=payer_name,
                denial_reason=request.denial_reason,
                appeal_sections=sections,
                key_citations=data.get("key_citations", []),
                demo_mode=False,
            )
    except Exception as e:
        logger.error(f"Appeal generation failed: {e}")

    return _get_demo_appeal(request, payer_name)


def _get_demo_appeal(request: AppealRequest, payer_name: str) -> AppealResponse:
    demo = DEMO_APPEAL_RESPONSE
    sections = [
        AppealSection(
            label=s["label"],
            content=s["content"],
            policy_citation=s.get("policy_citation"),
        )
        for s in demo["appeal_sections"]
    ]
    return AppealResponse(
        success=True,
        payer_name=payer_name,
        denial_reason=request.denial_reason,
        appeal_sections=sections,
        key_citations=demo["key_citations"],
        demo_mode=True,
    )
