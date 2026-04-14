"""
CPT Engine — semantic lookup of CPT/HCPCS codes from the 2026 Medicare fee schedule.

Data source: PPRRVU2026_Jan_nonQPP.csv (CMS Physician Fee Schedule)
             Ingested offline by: scripts/ingest_cpt_codes.py

Collection: authflow_cpt_codes (separate from payer policies)

Public API:
    lookup_cpt(query, top_k=5) -> list[dict]
        Returns [{"code": "72265", "description": "CT myelogram lumbar spine", "score": 0.92}, ...]

    is_cpt_loaded() -> bool
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from app.rag_engine import get_chroma_client, embed_texts, CHROMA_PATH

logger = logging.getLogger(__name__)

CPT_COLLECTION_NAME = "authflow_cpt_codes"

_cpt_collection = None


def get_cpt_collection():
    global _cpt_collection
    if _cpt_collection is None:
        client = get_chroma_client()
        _cpt_collection = client.get_or_create_collection(
            name=CPT_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _cpt_collection


def is_cpt_loaded() -> bool:
    """Return True if CPT codes have been ingested into ChromaDB."""
    try:
        return get_cpt_collection().count() > 0
    except Exception:
        return False


def lookup_cpt(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search for CPT codes matching a clinical procedure description.

    Args:
        query:  e.g. "CT myelogram lumbar spine" or "knee replacement arthroplasty"
        top_k:  number of results to return

    Returns:
        list of dicts: [{"code": "72265", "description": "...", "score": 0.92}, ...]
        Empty list if CPT data not yet ingested.
    """
    col = get_cpt_collection()
    if col.count() == 0:
        logger.warning("CPT collection is empty — run scripts/ingest_cpt_codes.py first")
        return []

    try:
        query_embedding = embed_texts([query])[0]
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, col.count()),
        )

        hits = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]

            for doc, meta, dist in zip(docs, metas, distances):
                score = round(1 - dist, 4)  # cosine distance → similarity
                hits.append({
                    "code": meta.get("cpt_code", ""),
                    "description": meta.get("description", doc),
                    "score": score,
                })

        logger.info(f"CPT lookup for '{query[:60]}' → {len(hits)} results")
        return hits

    except Exception as e:
        logger.error(f"CPT lookup failed: {e}")
        return []


def format_cpt_candidates(hits: list[dict]) -> str:
    """Format CPT lookup results as a prompt-injectable string."""
    if not hits:
        return "CPT code database not available — use clinical knowledge to assign code."

    lines = ["CANDIDATE CPT CODES FROM 2026 CMS FEE SCHEDULE (ranked by relevance):"]
    for i, h in enumerate(hits, 1):
        lines.append(f"  {i}. {h['code']} — {h['description']} (score: {h['score']})")
    lines.append("Select the most clinically appropriate code from the list above.")
    return "\n".join(lines)


# ── CPT code search ──────────────────────────────────────────────────────────
def search_cpt_by_description(keyword: str, limit: int = 10) -> list[dict]:
    """Full-text search across CPT descriptions. Case-insensitive substring match."""
    kw = keyword.lower().strip()
    results = []
    for code, desc in _get_cpt_db().items():
        if kw in desc.lower():
            results.append({"code": code, "description": desc})
            if len(results) >= limit:
                break
    return results
