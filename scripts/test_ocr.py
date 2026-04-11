"""
Test the OCR endpoint and the image→PA flow.

Usage:
    python scripts/test_ocr.py                  # synthetic test image
    python scripts/test_ocr.py path/to/note.png # real image file
"""

import sys
import requests
import base64
import io

BASE_URL = "http://localhost:8000"

# ── Get a JWT token first ─────────────────────────────────────────────────────
def get_token() -> str:
    r = requests.post(f"{BASE_URL}/token", data={"username": "demo", "password": "demo123"})
    if r.status_code != 200:
        raise RuntimeError(f"Could not get token: {r.status_code} {r.text}")
    return r.json()["access_token"]


def make_test_image() -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (600, 300), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20),  "Patient: 52F",                                    fill="black")
    draw.text((20, 50),  "CC: Lower back pain x6 weeks",                    fill="black")
    draw.text((20, 80),  "RX: NSAIDs, PT x4 weeks - no improvement",        fill="black")
    draw.text((20, 110), "Pacemaker 2019 - MRI contraindicated",             fill="black")
    draw.text((20, 140), "Plan: CT myelogram lumbar spine",                  fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_note(token: str, image_bytes: bytes):
    print("\n── Test 1: POST /extract-note ──────────────────────────────────")
    image_b64 = base64.b64encode(image_bytes).decode()
    r = requests.post(
        f"{BASE_URL}/extract-note",
        json={"image_base64": image_b64, "mime_type": "image/png", "procedure_type": "imaging"},
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        ext = data.get("extraction", {})
        print(f"Confidence:  {ext.get('extraction_confidence')}")
        print(f"Diagnosis:   {ext.get('diagnosis')}")
        print(f"Symptoms:    {ext.get('symptoms')}")
        print(f"Raw text:    {(ext.get('raw_text') or '')[:120]}...")
    else:
        print(data)


def test_generate_pa_with_image(token: str, image_bytes: bytes):
    print("\n── Test 2: POST /generate-pa with image_base64 ─────────────────")
    image_b64 = base64.b64encode(image_bytes).decode()
    r = requests.post(
        f"{BASE_URL}/generate-pa",
        json={
            "clinical_note": "",
            "payer": "bcbs_il",
            "procedure_type": "imaging",
            "image_base64": image_b64,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print(f"Demo mode:   {data.get('demo_mode')}")
        print(f"Confidence:  {data.get('confidence')}")
        print(f"ICD-10:      {data.get('icd10_code')} — {data.get('icd10_description')}")
        print(f"CPT:         {data.get('cpt_code')} — {data.get('cpt_description')}")
        print(f"Sections:    {len(data.get('form_sections', []))}")
    else:
        print(data)


def test_generate_pa_text_only(token: str):
    print("\n── Test 3: POST /generate-pa plain text (regression) ───────────")
    r = requests.post(
        f"{BASE_URL}/generate-pa",
        json={
            "clinical_note": "52-year-old female with lower back pain x6 weeks. Failed NSAIDs and PT x4 weeks. Pacemaker 2019 — MRI contraindicated. Plan: CT myelogram lumbar spine.",
            "payer": "bcbs_il",
            "procedure_type": "imaging",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print(f"Demo mode:  {data.get('demo_mode')}")
        print(f"Confidence: {data.get('confidence')}")
        print(f"Sections:   {len(data.get('form_sections', []))}")
    else:
        print(data)


if __name__ == "__main__":
    try:
        token = get_token()
    except Exception as e:
        print(f"Auth failed: {e}")
        sys.exit(1)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as f:
            image_bytes = f.read()
        print(f"Using image: {sys.argv[1]}")
    else:
        try:
            image_bytes = make_test_image()
            print("Using synthetic test image (Pillow)")
        except ImportError:
            print("Pillow not installed — run: pip install Pillow")
            sys.exit(1)

    test_extract_note(token, image_bytes)
    test_generate_pa_with_image(token, image_bytes)
    test_generate_pa_text_only(token)
    print("\nDone.")
