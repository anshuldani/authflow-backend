"""
scripts/ingest_policies.py

Run this script to ingest real payer policy PDFs into ChromaDB.
Usage:
    cd authflow-backend
    python scripts/ingest_policies.py

What it does:
1. Looks for PDFs in data/payer_policies/
2. For each PDF found, determines payer + procedure type from filename
3. Chunks, embeds, and stores in ChromaDB
4. Falls back to synthetic policies for any missing PDFs

Filename convention:
    {payer_id}_{procedure_type}.pdf
    e.g. bluecross_il_imaging.pdf, aetna_biologics.pdf

PDF Sources (all publicly accessible):
- Blue Cross IL:  bcbsil.com/providers/clinical-resources/clinical-payment-policies
- Aetna:          aetna.com/health-care-professionals/clinical-policy-bulletins
- UHC:            uhcprovider.com/en/clinical-policies-guidelines.html
- Cigna:          cigna.com/healthcare-professionals/resources/medical-coverage-policies
- Humana:         humana.com/provider/medical-resources/clinical-guidelines
- CMS fallback:   cms.gov/medicare-coverage-database

Run with:  python scripts/ingest_policies.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

from app.rag_engine import (
    ingest_pdf, ingest_synthetic_policies,
    get_collection, is_rag_loaded
)
from app.payer_config import PAYERS

POLICY_DIR = Path("data/payer_policies")

# Map filename keywords to procedure types
PROCEDURE_MAP = {
    "imaging": "imaging",
    "mri": "imaging",
    "ct": "imaging",
    "radiology": "imaging",
    "surgery": "surgery",
    "surgical": "surgery",
    "ortho": "surgery",
    "pt": "medication",
    "therapy": "medication",
    "biologics": "medication",
    "biologic": "medication",
    "medication": "medication",
    "drug": "medication",
    "pharmacy": "medication",
}


def get_procedure_type(filename: str) -> str:
    fname_lower = filename.lower()
    for keyword, proc_type in PROCEDURE_MAP.items():
        if keyword in fname_lower:
            return proc_type
    return "general"


def get_payer_id(filename: str) -> str | None:
    fname_lower = filename.lower()

    # Explicit alias mapping for common filename patterns
    aliases = {
        "bcbs_il": ["bcbs_il", "bcbsil", "bcbs", "bluecross_il", "bluecross", "blueshield", "blue"],
        "uhc": ["uhc", "unitedhealthcare", "united"],
        "aetna": ["aetna"],
        "cigna": ["cigna"],
        "humana": ["humana"],
    }

    # Strip underscores, dashes, and spaces for fuzzy matching
    fname_clean = fname_lower.replace("_", "").replace("-", "").replace(" ", "")
    for payer_id, patterns in aliases.items():
        for pattern in patterns:
            if pattern.replace("_", "").replace(" ", "") in fname_clean:
                return payer_id

    return None


def main():
    logger.info("=" * 60)
    logger.info("AuthFlow Policy Ingestion Script")
    logger.info("=" * 60)

    # Check for PDF files
    if not POLICY_DIR.exists():
        logger.warning(f"Policy directory not found: {POLICY_DIR}")
        logger.info("Creating directory — add payer PDFs here and re-run")
        POLICY_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(POLICY_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {POLICY_DIR}")

    # Ingest real PDFs
    ingested_count = 0
    for pdf_path in pdf_files:
        payer_id = get_payer_id(pdf_path.stem)
        procedure_type = get_procedure_type(pdf_path.stem)

        if not payer_id:
            logger.warning(f"Could not determine payer for {pdf_path.name} — skipping")
            continue

        logger.info(f"Ingesting: {pdf_path.name} → payer={payer_id}, type={procedure_type}")
        try:
            chunks = ingest_pdf(str(pdf_path), payer_id, procedure_type)
            logger.info(f"  ✓ {chunks} chunks ingested")
            ingested_count += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")

    # Always ensure synthetic policies are loaded as baseline
    logger.info("\nEnsuring synthetic policy baseline is loaded...")
    ingest_synthetic_policies()

    # Report
    col = get_collection()
    total = col.count()
    logger.info("\n" + "=" * 60)
    logger.info(f"Ingestion complete")
    logger.info(f"Real PDFs ingested: {ingested_count}")
    logger.info(f"Total chunks in ChromaDB: {total}")
    logger.info(f"RAG ready: {is_rag_loaded()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
