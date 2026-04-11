"""
Ingest 2026 CPT/HCPCS codes into ChromaDB for semantic lookup.

Data sources (both from the 'cpt codes' folder):
  - rvu26ar_1 2.zip  → PPRRVU2026_Jan_nonQPP.csv  (CPT Level I — ~10k codes)
  - hcpc2026_apr_anweb_0.zip → HCPC2026_APR_ANWEB.txt (HCPCS Level II — supplies/DME)

Run this once before starting the server:
    python scripts/ingest_cpt_codes.py

Or point at a different folder:
    python scripts/ingest_cpt_codes.py --cpt-dir /path/to/cpt/codes
"""

import os
import sys
import csv
import io
import zipfile
import logging
import argparse
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Default location of the 'cpt codes' folder
DEFAULT_CPT_DIR = Path(__file__).resolve().parent.parent / "cpt codes"
RVU_ZIP = "rvu26ar_1 2.zip"
RVU_CSV = "PPRRVU2026_Jan_nonQPP.csv"
HCPC_ZIP = "hcpc2026_apr_anweb_0.zip"
HCPC_TXT = "HCPC2026_APR_ANWEB.txt"

# Batch size for ChromaDB upserts
BATCH_SIZE = 500


def parse_rvu_csv(cpt_dir: Path) -> list[dict]:
    """
    Parse PPRRVU2026_Jan_nonQPP.csv from the RVU zip.

    CSV columns (after 10 header rows):
        0: HCPCS  1: MOD  2: DESCRIPTION  3: STATUS_CODE  ...

    Status codes to keep (valid for Medicare billing):
        A = Active
        B = Bundled (still a real code)
        C = Carrier-priced
        R = Restricted coverage
    Skip:
        I = Invalid / not covered
        T = Injections (these are real but very specific)
    """
    zip_path = cpt_dir / RVU_ZIP
    if not zip_path.exists():
        logger.warning(f"RVU zip not found: {zip_path}")
        return []

    codes = []
    seen = set()
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(RVU_CSV) as f:
            text = io.TextIOWrapper(f, encoding="latin-1")
            reader = csv.reader(text)

            # Skip header rows until we hit the actual data header
            header_found = False
            for row in reader:
                if not row:
                    continue
                # The actual data header row starts with "HCPCS"
                if row[0].strip() == "HCPCS":
                    header_found = True
                    continue

                if not header_found:
                    continue

                if len(row) < 4:
                    continue

                code = row[0].strip()
                description = row[2].strip()
                status = row[3].strip()

                if not code or not description:
                    continue

                # Skip inactive codes
                if status == "I":
                    continue

                # Skip blank/filler entries
                if description in ("NOT USED FOR MEDICARE", "", "NOT SEPARATELY PAYABLE"):
                    continue

                # Deduplicate — same code can appear multiple times with different modifiers
                if code in seen:
                    continue
                seen.add(code)

                codes.append({
                    "cpt_code": code,
                    "description": description,
                    "status": status,
                    "source": "rvu_2026",
                })

    logger.info(f"Parsed {len(codes)} CPT codes from RVU CSV")
    return codes


def parse_hcpc_txt(cpt_dir: Path) -> list[dict]:
    """
    Parse HCPC2026_APR_ANWEB.txt (fixed-width) for Level II HCPCS codes.

    Record layout (based on HCPC2026_recordlayout.txt):
    - Bytes 1-3:   filler (spaces)
    - Bytes 4-8:   HCPCS code (5 chars, e.g. A1001)
    - The short description starts around byte 9 and runs ~28 chars
    - The long description starts further into the record

    We extract code + short description (first non-code text up to col ~88).
    """
    zip_path = cpt_dir / HCPC_ZIP
    if not zip_path.exists():
        logger.warning(f"HCPC zip not found: {zip_path}")
        return []

    codes = []
    seen = set()

    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(HCPC_TXT) as f:
            for raw_line in f:
                line = raw_line.decode("latin-1")
                if len(line) < 10:
                    continue

                # Code at bytes 4-8 (0-indexed: 3-8)
                code = line[3:8].strip()
                if not code or len(code) < 4:
                    continue

                # Level II codes start with a letter (A-V, excluding E which is errors)
                # Skip if it looks like a CPT (all numeric) — those are in the RVU file
                if code.isdigit():
                    continue

                if code in seen:
                    continue
                seen.add(code)

                # Short description is in the next ~28 chars (bytes 9-36, 0-indexed 8-60)
                description = line[8:60].strip()
                if not description:
                    continue

                codes.append({
                    "cpt_code": code,
                    "description": description,
                    "status": "A",
                    "source": "hcpc_2026",
                })

    logger.info(f"Parsed {len(codes)} HCPCS Level II codes from HCPC txt")
    return codes


def ingest_codes(codes: list[dict], batch_size: int = BATCH_SIZE):
    """Embed and upsert CPT/HCPCS codes into the authflow_cpt_codes ChromaDB collection."""
    from app.cpt_engine import get_cpt_collection, CPT_COLLECTION_NAME
    from app.rag_engine import embed_texts

    col = get_cpt_collection()
    existing_count = col.count()

    if existing_count > 0:
        logger.info(f"CPT collection already has {existing_count} codes.")
        ans = input("Re-ingest? This will clear existing data. [y/N]: ").strip().lower()
        if ans != "y":
            logger.info("Skipping ingestion.")
            return
        # Clear and recreate
        import chromadb
        from chromadb.config import Settings
        from app.rag_engine import get_chroma_client, CHROMA_PATH
        client = get_chroma_client()
        client.delete_collection(CPT_COLLECTION_NAME)
        col = client.create_collection(
            name=CPT_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        # Reset module-level cached collection
        import app.cpt_engine as cpt_mod
        cpt_mod._cpt_collection = col
        logger.info("Cleared existing CPT collection.")

    total = len(codes)
    logger.info(f"Ingesting {total} codes in batches of {batch_size}...")

    ingested = 0
    for start in range(0, total, batch_size):
        batch = codes[start : start + batch_size]

        # Document text = "CODE: description" for better semantic matching
        docs = [f"{c['cpt_code']}: {c['description']}" for c in batch]
        ids = [f"cpt_{c['cpt_code']}_{c['source']}" for c in batch]
        metas = [
            {
                "cpt_code": c["cpt_code"],
                "description": c["description"],
                "status": c["status"],
                "source": c["source"],
            }
            for c in batch
        ]

        embeddings = embed_texts(docs)
        col.add(documents=docs, ids=ids, metadatas=metas, embeddings=embeddings)

        ingested += len(batch)
        logger.info(f"  {ingested}/{total} ingested...")

    logger.info(f"Done. CPT collection now has {col.count()} codes.")


def main():
    parser = argparse.ArgumentParser(description="Ingest CPT codes into ChromaDB")
    parser.add_argument(
        "--cpt-dir",
        type=Path,
        default=DEFAULT_CPT_DIR,
        help=f"Directory containing the CPT zip files (default: {DEFAULT_CPT_DIR})",
    )
    parser.add_argument(
        "--rvu-only",
        action="store_true",
        help="Only ingest CPT Level I codes from the RVU file (skip HCPCS Level II)",
    )
    args = parser.parse_args()

    cpt_dir = args.cpt_dir
    if not cpt_dir.exists():
        logger.error(f"CPT directory not found: {cpt_dir}")
        sys.exit(1)

    logger.info(f"CPT source directory: {cpt_dir}")

    all_codes = []

    # Level I: CPT codes from RVU file (the main source)
    rvu_codes = parse_rvu_csv(cpt_dir)
    all_codes.extend(rvu_codes)

    # Level II: HCPCS codes (supplies, DME, drugs) — optional
    if not args.rvu_only:
        hcpc_codes = parse_hcpc_txt(cpt_dir)
        all_codes.extend(hcpc_codes)

    if not all_codes:
        logger.error("No codes parsed. Check that the zip files are in the CPT directory.")
        sys.exit(1)

    logger.info(f"Total codes to ingest: {len(all_codes)}")
    ingest_codes(all_codes)


if __name__ == "__main__":
    main()
