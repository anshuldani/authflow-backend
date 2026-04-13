"""
OCR Engine — image → clean clinical text.

Primary:  Gemini Vision (uses GOOGLE_API_KEY from .env)
Fallback: pytesseract (local, works offline)

Public API:
    extract_text_from_image(image_bytes) -> dict
        {text, confidence, method, raw_text}
"""

import os
import base64
import logging
import re

logger = logging.getLogger(__name__)

OCR_PROMPT = """You are reading a handwritten medical clinical note.
Extract ALL text exactly as written. Preserve:
- Patient demographics (age, sex)
- Chief complaint and symptoms
- Duration of symptoms
- Physical examination findings
- Medications and treatments tried
- Assessment and plan
- Any codes, dosages, or measurements mentioned

Return ONLY the extracted text. No commentary. No formatting.
If handwriting is unclear, make your best attempt and note [unclear] inline."""


def extract_text_gemini_vision(image_bytes: bytes) -> str:
    """Extract text from image using Gemini Vision."""
    google_key = os.getenv("GOOGLE_API_KEY", "")
    if not google_key:
        raise ValueError("GOOGLE_API_KEY not set")

    import google.generativeai as genai

    genai.configure(api_key=google_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_part = {
        "inline_data": {
            "mime_type": "image/png",
            "data": image_b64,
        }
    }

    response = model.generate_content([image_part, OCR_PROMPT])
    return response.text.strip()


def extract_text_tesseract(image_bytes: bytes) -> str:
    """Extract text from image using pytesseract (local fallback)."""
    import pytesseract
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img).strip()


def clean_medical_text(raw_text: str) -> str:
    """Fix common OCR artifacts in clinical text."""
    text = raw_text

    # Collapse multiple spaces/blank lines
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Fix common digit/letter confusions in medical codes (e.g. "O" vs "0")
    # Only apply inside patterns that look like codes (alphanumeric, uppercase)
    text = re.sub(r"\bO(\d)", r"0\1", text)   # leading O before digit → 0
    text = re.sub(r"(\d)O\b", r"\g<1>0", text) # trailing O after digit → 0

    # Remove stray pipe characters and form-feed artifacts
    text = text.replace("|", "I").replace("\f", "\n")

    return text.strip()


def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Try Gemini Vision first, fall back to tesseract.

    Returns:
        {
          "text":       str,   # cleaned extracted text
          "raw_text":   str,   # text before cleaning
          "confidence": str,   # "high" | "medium" | "low"
          "method":     str,   # "gemini_vision" | "tesseract" | "failed"
        }
    """
    # ── Gemini Vision (primary) ───────────────────────────────────────────────
    try:
        raw = extract_text_gemini_vision(image_bytes)
        text = clean_medical_text(raw)
        return {
            "text": text,
            "raw_text": raw,
            "confidence": "high",
            "method": "gemini_vision",
        }
    except Exception as e:
        logger.warning(f"Gemini Vision OCR failed: {e} — trying tesseract fallback")

    # ── Tesseract (fallback) ──────────────────────────────────────────────────
    try:
        raw = extract_text_tesseract(image_bytes)
        text = clean_medical_text(raw)
        return {
            "text": text,
            "raw_text": raw,
            "confidence": "medium",
            "method": "tesseract",
        }
    except Exception as e:
        logger.error(f"Tesseract OCR also failed: {e}")

    return {
        "text": "",
        "raw_text": "",
        "confidence": "low",
        "method": "failed",
    }


# ── OCR result confidence filter ─────────────────────────────────────────────
MIN_CONFIDENCE = 0.75

def filter_low_confidence_blocks(blocks: list, threshold: float = MIN_CONFIDENCE) -> list:
    """Remove OCR text blocks below confidence threshold to reduce hallucinations."""
    return [b for b in blocks if b.get("confidence", 1.0) >= threshold]
