"""
RAG Engine — ChromaDB-based retrieval for payer PA policy criteria.

Architecture:
- Vector store: ChromaDB (local, offline-capable)
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (no API key required)
- Ingestion: payer policy PDFs chunked at 512 tokens, tagged with payer_id + policy_section
- Retrieval: top-5 chunks for (payer, procedure_type) query
- Fallback: synthetic policy text from payer_config.py when ChromaDB is empty
"""

import os
import time
import logging
from typing import Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings

from app.payer_config import PAYERS, SYNTHETIC_POLICIES

logger = logging.getLogger(__name__)

# ── ChromaDB setup ──────────────────────────────────────────────────────────
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
COLLECTION_NAME = "authflow_payer_policies"

_chroma_client: Optional[chromadb.Client] = None
_collection = None
_rag_loaded = False


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def is_rag_loaded() -> bool:
    """Check whether ChromaDB has any documents ingested."""
    try:
        col = get_collection()
        return col.count() > 0
    except Exception:
        return False


# ── Embedding function ───────────────────────────────────────────────────────
_embedder = None

def get_embedder():
    """
    Lazy-load sentence-transformer if available.
    On your machine: pip install sentence-transformers → auto-downloads the model.
    In restricted environments: falls back to TF-IDF style hashing.
    """
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Try loading from cache first (works if model was previously downloaded)
            import os
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            _embedder = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache_dir)
            logger.info("Embedder loaded: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"sentence-transformers unavailable: {e}. Using TF-IDF hashing fallback.")
            _embedder = "tfidf_fallback"
    return _embedder


def _tfidf_embed(text: str, dim: int = 384) -> list[float]:
    """
    Lightweight offline embedding using character n-gram hashing.
    Not as accurate as sentence-transformers but fully offline — works for demo.
    Produces a consistent dim-dimensional vector for any input text.
    """
    import math
    import hashlib

    text = text.lower()
    vec = [0.0] * dim

    # Character n-grams (2-4) hashed into vector positions
    for n in range(2, 5):
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
            pos = h % dim
            vec[pos] += 1.0

    # Word unigrams with position weighting
    words = text.split()
    for idx, word in enumerate(words):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        pos = h % dim
        vec[pos] += 1.0 / (1 + idx * 0.1)

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed a list of texts. Returns None only on unexpected failure."""
    embedder = get_embedder()

    if embedder == "tfidf_fallback":
        return [_tfidf_embed(t) for t in texts]

    if embedder is None:
        return None

    try:
        return embedder.encode(texts, show_progress_bar=False).tolist()
    except Exception as e:
        logger.warning(f"Embedding failed: {e}. Using TF-IDF fallback.")
        return [_tfidf_embed(t) for t in texts]


# ── Ingestion ────────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def ingest_synthetic_policies():
    """
    Load synthetic payer policy text into ChromaDB.
    Called automatically on startup if ChromaDB is empty.
    This ensures the RAG engine works even without real PDFs downloaded.
    """
    global _rag_loaded
    col = get_collection()

    if col.count() > 0:
        logger.info(f"ChromaDB already has {col.count()} chunks. Skipping ingestion.")
        _rag_loaded = True
        return

    logger.info("Ingesting synthetic payer policies into ChromaDB...")
    all_docs, all_ids, all_metas = [], [], []
    doc_counter = 0

    for payer_id, procedures in SYNTHETIC_POLICIES.items():
        for procedure_type, policy_text in procedures.items():
            chunks = chunk_text(policy_text)
            for i, chunk in enumerate(chunks):
                doc_id = f"{payer_id}_{procedure_type}_{i}"
                all_docs.append(chunk)
                all_ids.append(doc_id)
                all_metas.append({
                    "payer_id": payer_id,
                    "procedure_type": procedure_type,
                    "chunk_index": i,
                    "source": "synthetic_policy",
                })
                doc_counter += 1

    # Always provide our own embeddings so ChromaDB never tries to download its ONNX model
    embeddings = embed_texts(all_docs)
    col.add(documents=all_docs, ids=all_ids, metadatas=all_metas, embeddings=embeddings)

    logger.info(f"Ingested {doc_counter} chunks from synthetic policies.")
    _rag_loaded = True


def ingest_pdf(pdf_path: str, payer_id: str, procedure_type: str):
    """
    Ingest a real payer policy PDF into ChromaDB.
    Called by scripts/ingest_policies.py
    """
    from pypdf import PdfReader
    col = get_collection()

    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    if not full_text.strip():
        logger.warning(f"No text extracted from {pdf_path}")
        return 0

    chunks = chunk_text(full_text)
    all_docs, all_ids, all_metas = [], [], []
    pdf_name = Path(pdf_path).stem

    for i, chunk in enumerate(chunks):
        doc_id = f"{payer_id}_{pdf_name}_{i}"
        all_docs.append(chunk)
        all_ids.append(doc_id)
        all_metas.append({
            "payer_id": payer_id,
            "procedure_type": procedure_type,
            "chunk_index": i,
            "source": pdf_path,
        })

    embeddings = embed_texts(all_docs)
    col.add(documents=all_docs, ids=all_ids, metadatas=all_metas, embeddings=embeddings)

    logger.info(f"Ingested {len(chunks)} chunks from {pdf_path}")
    return len(chunks)


# ── Retrieval ────────────────────────────────────────────────────────────────
def retrieve_criteria(payer_id: str, procedure_type: str, clinical_note: str, n_results: int = 5) -> str:
    """
    Retrieve the most relevant policy criteria for a given payer + procedure + clinical context.
    
    Returns a formatted string of policy criteria for use in the LLM prompt.
    Falls back to synthetic policy text if ChromaDB retrieval fails.
    """
    col = get_collection()

    # Build query from clinical note + procedure type
    query = f"{procedure_type} prior authorization criteria {clinical_note[:300]}"

    try:
        # Filter by payer_id only — procedure_type matching is handled by semantic similarity
        where_filter = {"payer_id": {"$eq": payer_id}}

        # Always use our own embeddings — avoids ChromaDB trying to download ONNX model
        query_embedding = embed_texts([query])[0]
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, col.count()),
            where=where_filter,
        )

        if results and results["documents"] and results["documents"][0]:
            retrieved = results["documents"][0]
            combined = "\n\n---\n\n".join(retrieved)
            logger.info(f"RAG retrieved {len(retrieved)} chunks for {payer_id}/{procedure_type}")
            return combined

    except Exception as e:
        logger.warning(f"ChromaDB retrieval failed: {e}. Using synthetic fallback.")

    # Fallback: return synthetic policy for this payer + procedure type
    return _get_synthetic_fallback(payer_id, procedure_type)


def _get_synthetic_fallback(payer_id: str, procedure_type: str) -> str:
    """Return best-match synthetic policy text as fallback."""
    payer_policies = SYNTHETIC_POLICIES.get(payer_id, {})

    # Direct match
    if procedure_type in payer_policies:
        return payer_policies[procedure_type]

    # Fuzzy match — find closest procedure type
    procedure_map = {
        "ct": "imaging", "mri": "imaging", "imaging": "imaging",
        "ct myelogram": "imaging", "scan": "imaging", "radiology": "imaging",
        "surgery": "surgery", "surgical": "surgery", "arthroplasty": "surgery",
        "knee": "surgery", "hip": "surgery", "replacement": "surgery",
        "medication": "medication", "drug": "medication", "biologic": "medication",
        "biologics": "medication", "injection": "medication", "infusion": "medication",
        "physical therapy": "imaging", "pt": "imaging",
    }

    for keyword, mapped_type in procedure_map.items():
        if keyword in procedure_type.lower():
            if mapped_type in payer_policies:
                return payer_policies[mapped_type]

    # Last resort: return any available policy for this payer
    if payer_policies:
        return list(payer_policies.values())[0]

    # If payer not in synthetic policies, use Blue Cross as universal fallback
    bcbs = SYNTHETIC_POLICIES.get("bcbs_il", {})
    return bcbs.get("imaging", "No policy criteria available. Generate based on standard medical necessity criteria.")


def retrieve_with_retry(payer_id: str, procedure: str, max_retries: int = 3) -> list:
    """Retrieve RAG context with exponential backoff retry."""
    import time as _time
    for attempt in range(max_retries):
        try:
            return retrieve_policy_context(payer_id, procedure)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"RAG retrieval failed after {max_retries} attempts: {e}")
                return []
            wait = 2 ** attempt
            logger.warning(f"RAG retrieval attempt {attempt + 1} failed, retrying in {wait}s: {e}")
            _time.sleep(wait)
    return []
