"""
Form Generator — clinical note + payer PA criteria → complete PA form.

LLM: Gemini 2.0 Flash (primary, fast + cheap)
Fallback: GPT-4o-mini
Demo mode: hardcoded responses from payer_config.py
"""

import os
import json
import time
import logging
from typing import Optional

from app.models import PARequest, PAResponse, FormSection, CriterionDetail
from app.payer_config import PAYERS, DEMO_RESPONSES
from app.cpt_engine import lookup_cpt, format_cpt_candidates, is_cpt_loaded

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"


# ── LLM setup ────────────────────────────────────────────────────────────────
def get_llm():
    """Initialize LLM — Gemini Flash primary, GPT-4o-mini fallback."""
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=google_key,
                temperature=0.1,
                max_tokens=2048,
            )
            logger.info("LLM initialized: Gemini 2.0 Flash")
            return llm
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")

    if openai_key and openai_key != "your_openai_api_key_here_optional_fallback":
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
                temperature=0.1,
                max_tokens=2048,
            )
            logger.info("LLM initialized: GPT-4o-mini (fallback)")
            return llm
        except Exception as e:
            logger.warning(f"OpenAI init failed: {e}")

    logger.warning("No LLM API key found. Will use demo mode responses.")
    return None


# ── Core prompt ───────────────────────────────────────────────────────────────
PA_FORM_PROMPT = """You are an expert medical billing specialist with 15 years of experience completing prior authorization forms. Generate a complete PA form that will be APPROVED by the insurance payer.

PAYER: {payer_name}

PAYER PRIOR AUTHORIZATION REQUIREMENTS:
{payer_criteria}

CLINICAL NOTE FROM PHYSICIAN:
{clinical_note}

PROCEDURE TYPE: {procedure_type}

{cpt_candidates}

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no explanation:
{{
  "procedure": "Full procedure name with CPT code",

  "icd10_code": "Most specific ICD-10 code (e.g. M54.42)",
  "icd10_description": "Full ICD-10 description (e.g. Lumbago with sciatica, left side)",
  "cpt_code": "Most appropriate CPT code (e.g. 72265)",
  "cpt_description": "Full CPT description",

  "clinical_justification": "2-3 sentences in payer language mapping patient findings to each criterion. Cite specific policy section.",
  "medical_necessity": "1-2 sentence formal medical necessity statement using the PAYER'S EXACT language from their policy.",
  "supporting_evidence": "Bullet-point list of: symptom duration, conservative treatments with dates/duration, exam findings, test results, functional limitations",

  "policy_sections_cited": ["List of specific policy sections this request satisfies"],

  "criteria_met": 3,
  "criteria_total": 4,
  "criteria_details": [
    {{"criterion": "Description of the payer criterion", "met": true, "evidence": "Specific evidence from the note"}}
  ],
  "approval_likelihood": "high",
  "approval_reasoning": "One sentence explaining the likelihood assessment.",
  "missing_information": ["Any information from the note that would strengthen the request, or empty array"],

  "confidence": "high",

  "sections": [
    {{
      "label": "Patient Diagnosis",
      "content": "ICD-10 code, diagnosis name, key symptoms and duration",
      "policy_citation": "Exact policy section"
    }},
    {{
      "label": "Requested Procedure/Service",
      "content": "What is being requested, why this specific procedure, CPT code",
      "policy_citation": "Policy coverage indication"
    }},
    {{
      "label": "Clinical Justification",
      "content": "Map each payer criterion to specific patient evidence. Be explicit.",
      "policy_citation": "Policy medical necessity section"
    }},
    {{
      "label": "Supporting Clinical Evidence",
      "content": "Bullet points: duration, treatments tried with dates, exam findings, test results, functional limitations",
      "policy_citation": "Policy documentation requirements"
    }},
    {{
      "label": "Medical Necessity Statement",
      "content": "3-4 sentence formal statement using the PAYER'S EXACT LANGUAGE from their requirements.",
      "policy_citation": "Policy medical necessity language"
    }}
  ]
}}

RULES:
- Use the payer's exact terminology throughout
- icd10_code: use most specific code with extension where appropriate
- criteria_met / criteria_total: count of payer criteria satisfied vs total
- approval_likelihood: "high" if all criteria met, "medium" if most met, "low" if key criteria missing
- confidence equals approval_likelihood
- Do NOT output anything except the JSON object"""


def generate_pa_form(request: PARequest, payer_criteria: str) -> PAResponse:
    """
    Core function: generate PA form from clinical note + payer criteria.

    Flow:
    1. Check DEMO_MODE → return hardcoded response
    2. Try LLM (Gemini → GPT-4o-mini)
    3. Fallback to hardcoded demo response if LLM fails
    """
    start_time = time.time()
    payer_info = PAYERS.get(request.payer, {})
    payer_name = payer_info.get("name", request.payer)

    # ── Demo mode ──────────────────────────────────────────────────────────
    if DEMO_MODE:
        return _get_demo_response(request, payer_name, start_time)

    # ── LLM generation ─────────────────────────────────────────────────────
    llm = get_llm()

    if llm:
        try:
            procedure_type = request.procedure_type or request.procedure_category or "general"

            # CPT lookup — build a query from procedure type + key clinical terms
            cpt_query = f"{procedure_type} {request.clinical_note[:300]}"
            cpt_hits = lookup_cpt(cpt_query, top_k=5) if is_cpt_loaded() else []
            cpt_candidates = format_cpt_candidates(cpt_hits)
            if cpt_hits:
                logger.info(f"CPT lookup returned {len(cpt_hits)} candidates (top: {cpt_hits[0]['code']})")

            prompt = PA_FORM_PROMPT.format(
                payer_name=payer_name,
                payer_criteria=payer_criteria,
                clinical_note=request.clinical_note,
                procedure_type=procedure_type,
                cpt_candidates=cpt_candidates,
            )

            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Strip markdown fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip().rstrip("```").strip()

            data = json.loads(content)

            sections = [
                FormSection(
                    label=s["label"],
                    content=s["content"],
                    policy_citation=s.get("policy_citation"),
                )
                for s in data.get("sections", [])
            ]

            criteria_details = [
                CriterionDetail(
                    criterion=c["criterion"],
                    met=c["met"],
                    evidence=c["evidence"],
                )
                for c in data.get("criteria_details", [])
            ]

            elapsed = int((time.time() - start_time) * 1000)

            # Gemini sometimes returns supporting_evidence as a list — normalise to str
            raw_evidence = data.get("supporting_evidence")
            if isinstance(raw_evidence, list):
                raw_evidence = "\n".join(str(x) for x in raw_evidence)

            return PAResponse(
                success=True,
                payer_name=payer_name,
                procedure=data.get("procedure", request.procedure_type),
                form_sections=sections,
                raw_justification="\n\n".join(s.content for s in sections),
                confidence=data.get("confidence", "medium"),
                processing_time_ms=elapsed,
                demo_mode=False,
                # GeneratedForm-compatible flat fields
                icd10_code=data.get("icd10_code"),
                icd10_description=data.get("icd10_description"),
                cpt_code=data.get("cpt_code"),
                cpt_description=data.get("cpt_description"),
                clinical_justification=data.get("clinical_justification"),
                medical_necessity=data.get("medical_necessity"),
                supporting_evidence=raw_evidence,
                policy_sections_cited=data.get("policy_sections_cited") or [],
                criteria_met=data.get("criteria_met"),
                criteria_total=data.get("criteria_total"),
                criteria_details=criteria_details,
                approval_likelihood=data.get("approval_likelihood"),
                approval_reasoning=data.get("approval_reasoning"),
                missing_information=data.get("missing_information") or [],
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}. Trying text fallback.")
            return _text_fallback(request, payer_name, payer_criteria, llm, start_time)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")

    # ── No LLM available — use demo response ───────────────────────────────
    logger.warning("No LLM available. Returning demo response.")
    return _get_demo_response(request, payer_name, start_time)


def _text_fallback(request, payer_name, payer_criteria, llm, start_time):
    """Second attempt: ask LLM for plain text if JSON parsing failed."""
    try:
        simple_prompt = f"""You are a medical billing specialist. Write a prior authorization clinical justification for:

Payer: {payer_name}
Patient note: {request.clinical_note}
Procedure: {request.procedure_type or 'as clinically indicated'}

Payer requirements: {payer_criteria[:1000]}

Write 4 clear paragraphs:
1. DIAGNOSIS: Patient's diagnosis and ICD-10 code
2. REQUESTED SERVICE: What is being requested and why
3. CLINICAL JUSTIFICATION: How the patient meets the payer's criteria
4. MEDICAL NECESSITY: Formal statement using the payer's language

Be specific and professional."""

        response = llm.invoke(simple_prompt)
        text = response.content if hasattr(response, "content") else str(response)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        labels = ["Patient Diagnosis", "Requested Service", "Clinical Justification", "Medical Necessity Statement"]
        sections = []
        for i, para in enumerate(paragraphs[:4]):
            label = labels[i] if i < len(labels) else f"Section {i+1}"
            content = para
            for prefix in ["1. ", "2. ", "3. ", "4. ", "DIAGNOSIS: ", "REQUESTED SERVICE: ",
                          "CLINICAL JUSTIFICATION: ", "MEDICAL NECESSITY: "]:
                if content.startswith(prefix):
                    content = content[len(prefix):]
                    break
            sections.append(FormSection(label=label, content=content))

        elapsed = int((time.time() - start_time) * 1000)
        return PAResponse(
            success=True,
            payer_name=payer_name,
            procedure=request.procedure_type,
            form_sections=sections,
            raw_justification=text,
            confidence="medium",
            processing_time_ms=elapsed,
            demo_mode=False,
        )
    except Exception as e:
        logger.error(f"Text fallback also failed: {e}")
        return _get_demo_response(request, payer_name, start_time)


def _get_demo_response(request: PARequest, payer_name: str, start_time: float) -> PAResponse:
    """Return hardcoded demo response. Picks best match by payer."""
    elapsed = int((time.time() - start_time) * 1000)

    # Map payer to best-fit demo scenario
    payer_scenario_map = {
        "bcbs_il": "scenario_1",
        "aetna": "scenario_2",
        "uhc": "scenario_3",
        "cigna": "scenario_4",
        "humana": "scenario_5",
    }

    scenario_key = payer_scenario_map.get(request.payer, "scenario_1")
    demo = DEMO_RESPONSES.get(scenario_key)

    if not demo:
        return PAResponse(
            success=True,
            payer_name=payer_name,
            procedure="Prior Authorization Form",
            form_sections=[FormSection(
                label="Prior Authorization",
                content="Demo mode: Connect an LLM API key for live generation.",
            )],
            raw_justification="Demo mode response",
            confidence="high",
            processing_time_ms=elapsed,
            demo_mode=True,
        )

    sections = [
        FormSection(
            label=s["label"],
            content=s["content"],
            policy_citation=s.get("policy_citation"),
        )
        for s in demo["form_sections"]
    ]

    criteria_details = [
        CriterionDetail(
            criterion=c["criterion"],
            met=c["met"],
            evidence=c["evidence"],
        )
        for c in demo.get("criteria_details", [])
    ]

    return PAResponse(
        success=True,
        payer_name=payer_name,
        procedure=demo["procedure"],
        form_sections=sections,
        raw_justification="\n\n".join(s.content for s in sections),
        confidence=demo["confidence"],
        processing_time_ms=elapsed,
        demo_mode=True,
        # GeneratedForm-compatible flat fields
        icd10_code=demo.get("icd10_code"),
        icd10_description=demo.get("icd10_description"),
        cpt_code=demo.get("cpt_code"),
        cpt_description=demo.get("cpt_description"),
        clinical_justification=demo.get("clinical_justification"),
        medical_necessity=demo.get("medical_necessity"),
        supporting_evidence=demo.get("supporting_evidence"),
        policy_sections_cited=demo.get("policy_sections_cited") or [],
        criteria_met=demo.get("criteria_met"),
        criteria_total=demo.get("criteria_total"),
        criteria_details=criteria_details,
        approval_likelihood=demo.get("approval_likelihood"),
        approval_reasoning=demo.get("approval_reasoning"),
        missing_information=demo.get("missing_information") or [],
    )
