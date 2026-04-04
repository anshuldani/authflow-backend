"""
Form Generator — takes clinical note + payer PA criteria → complete PA form.

LLM: Gemini 1.5 Flash (primary, fast + cheap)
Fallback: GPT-4o-mini
Demo mode: hardcoded responses from payer_config.py
"""

import os
import json
import time
import logging
from typing import Optional

from app.models import PARequest, PAResponse, FormSection
from app.payer_config import PAYERS, DEMO_RESPONSES

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
            logger.info("LLM initialized: Gemini 1.5 Flash")
            return llm
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")

    if openai_key:
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
PA_FORM_PROMPT = """You are an expert medical billing specialist with 15 years of experience completing prior authorization forms. Your job is to generate a complete, professional prior authorization form that will be APPROVED by the insurance payer.

PAYER: {payer_name}

PAYER PRIOR AUTHORIZATION REQUIREMENTS:
{payer_criteria}

CLINICAL NOTE FROM PHYSICIAN:
{clinical_note}

PROCEDURE TYPE: {procedure_type}

INSTRUCTIONS:
Generate a complete prior authorization form with exactly these 5 sections. Use the payer's own terminology from the requirements above. Be specific and clinical. Map every criterion from the payer requirements to evidence in the clinical note.

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no explanation:
{{
  "procedure": "Full procedure name with CPT code if determinable",
  "sections": [
    {{
      "label": "Patient Diagnosis",
      "content": "ICD-10 code(s) if mentioned, diagnosis name, key presenting symptoms and duration",
      "policy_citation": "Exact policy section this satisfies"
    }},
    {{
      "label": "Requested Procedure/Service",
      "content": "What is being requested, why this specific procedure, CPT code",
      "policy_citation": "Policy coverage indication"
    }},
    {{
      "label": "Clinical Justification",
      "content": "Map patient's specific symptoms and findings to EACH payer criterion. Be explicit about how the patient meets every requirement.",
      "policy_citation": "Policy section for medical necessity"
    }},
    {{
      "label": "Supporting Clinical Evidence",
      "content": "Bullet points: symptom duration, conservative treatments tried with dates/duration, examination findings, relevant test results, functional limitations",
      "policy_citation": "Policy documentation requirements section"
    }},
    {{
      "label": "Medical Necessity Statement",
      "content": "3-4 sentence formal medical necessity statement using the PAYER'S EXACT LANGUAGE from their requirements. State why this is medically necessary, what conservative care failed, what the imaging/treatment will determine.",
      "policy_citation": "Policy medical necessity language section"
    }}
  ],
  "confidence": "high"
}}

IMPORTANT:
- Use the payer's exact terminology (copy their medical necessity language template)
- If ICD-10 or CPT codes are not in the note, derive them from the clinical picture
- Confidence should be "high" if the note clearly satisfies payer criteria, "medium" if some criteria are implied, "low" if critical information is missing
- Do NOT add information not supported by the clinical note
- Do NOT output anything except the JSON object"""


def generate_pa_form(request: PARequest, payer_criteria: str) -> PAResponse:
    """
    Core function: generate PA form from clinical note + payer criteria.
    
    Flow:
    1. Check DEMO_MODE → return hardcoded response
    2. Try LLM (Gemini → GPT-4o-mini)
    3. Fallback to structured extraction if LLM fails
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
            prompt = PA_FORM_PROMPT.format(
                payer_name=payer_name,
                payer_criteria=payer_criteria,
                clinical_note=request.clinical_note,
                procedure_type=request.procedure_type or "general",
            )

            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Clean JSON from response
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

            elapsed = int((time.time() - start_time) * 1000)

            return PAResponse(
                success=True,
                payer_name=payer_name,
                procedure=data.get("procedure", request.procedure_type),
                form_sections=sections,
                raw_justification="\n\n".join(s.content for s in sections),
                confidence=data.get("confidence", "medium"),
                processing_time_ms=elapsed,
                demo_mode=False,
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
            # Remove numbering prefix if present
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

    # Match to best demo scenario
    demo = None
    if request.payer in ("bluecross_il",):
        demo = DEMO_RESPONSES.get("scenario_1")
    elif request.payer == "aetna":
        demo = DEMO_RESPONSES.get("scenario_2")
    else:
        demo = DEMO_RESPONSES.get("scenario_1")  # Default

    if not demo:
        # Minimal fallback
        return PAResponse(
            success=True,
            payer_name=payer_name,
            procedure="Prior Authorization Form",
            form_sections=[FormSection(
                label="Prior Authorization",
                content="Demo mode: This is a sample prior authorization form. Connect an LLM API key for live generation.",
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

    return PAResponse(
        success=True,
        payer_name=payer_name,
        procedure=demo["procedure"],
        form_sections=sections,
        raw_justification="\n\n".join(s.content for s in sections),
        confidence=demo["confidence"],
        processing_time_ms=elapsed,
        demo_mode=True,
    )
