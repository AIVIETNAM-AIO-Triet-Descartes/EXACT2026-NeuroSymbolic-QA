"""
pipeline/type2/formula_rag.py

LangGraph node [4b]: Retrieve best-matching formula from knowledge base.
Hybrid strategy: Layer 1 keyword/exact match → Layer 2 FAISS semantic search.
No LangChain — calls faiss and sentence-transformers directly.
"""

import json
import pickle
import logging
from typing import Optional

from sympy import sympify

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# Formula DB loader
# ══════════════════════════════════════════════════════════════

def load_formula_db(path: str = "data/rag/physics_formulas.json") -> list[dict]:
    """
    Load formula knowledge base, validate each entry with sympify.
    Returns only entries whose formula_sympy parses cleanly.
    Called at startup — production version of tests/physics_formula.py logic.
    """
    with open(path, encoding="utf-8") as f:
        docs = json.load(f)
    valid = []
    for doc in docs:
        try:
            sympify(doc["formula_sympy"].split("=")[-1].strip())
            valid.append(doc)
        except Exception:
            logger.warning(f"[FORMULA_DB] Invalid formula_sympy in {doc['id']}, skipping")
    logger.info(f"[FORMULA_DB] Loaded {len(valid)}/{len(docs)} valid formulas")
    return valid


# ══════════════════════════════════════════════════════════════
# FAISS index — lazy loaded singleton
# ══════════════════════════════════════════════════════════════

_faiss_index = None
_faiss_docs: Optional[list] = None
_faiss_model = None


def _load_faiss_index(index_dir: str = "data/formula_index") -> tuple:
    """Load pre-built FAISS index + metadata. Returns (index, docs, model) or (None, None, None)."""
    try:
        import faiss
        from sentence_transformers import SentenceTransformer

        index = faiss.read_index(f"{index_dir}/index.faiss")
        with open(f"{index_dir}/metadata.pkl", "rb") as f:
            docs = pickle.load(f)
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info(f"[FORMULA_RAG] FAISS index loaded ({len(docs)} entries)")
        return index, docs, model
    except Exception as e:
        logger.warning(f"[FORMULA_RAG] FAISS index not available: {e}")
        return None, None, None


def _ensure_faiss_loaded(index_dir: str = "data/formula_index") -> None:
    global _faiss_index, _faiss_docs, _faiss_model
    if _faiss_index is None:
        _faiss_index, _faiss_docs, _faiss_model = _load_faiss_index(index_dir)


# ══════════════════════════════════════════════════════════════
# Hybrid retrieval
# ══════════════════════════════════════════════════════════════

def retrieve_formula(
    parsed: dict,
    docs: list[dict],
    question: str = "",
) -> Optional[dict]:
    """
    Hybrid retrieval — two layers:
      Layer 1: domain == parsed["domain"] AND parsed["find"] in doc["variables"]
               → exactly 1 candidate → return immediately (skip FAISS)
      Layer 2: FAISS semantic search over candidates (if 2+) or all docs (if 0)
               → return best hit within the search pool

    Falls back to first candidate (or None) if FAISS unavailable.
    """
    domain = parsed.get("domain", "")
    find = parsed.get("find", "")

    # Layer 1: keyword/exact match
    candidates = [
        d for d in docs
        if d.get("domain") == domain and find and find in d.get("variables", {})
    ]

    if len(candidates) == 1:
        logger.info(f"[FORMULA_RAG] Layer 1 hit: {candidates[0]['id']}")
        return candidates[0]

    # Layer 2: FAISS semantic search
    _ensure_faiss_loaded()
    search_pool = candidates if candidates else docs

    if _faiss_index is not None and _faiss_model is not None and _faiss_docs is not None:
        try:
            import numpy as np
            query = f"{domain} {find} {question}".strip()
            emb = _faiss_model.encode([query]).astype("float32")

            # Search top-k, filter to search_pool
            k = min(len(_faiss_docs), 10)
            _, I = _faiss_index.search(emb, k=k)
            for idx in I[0]:
                if 0 <= idx < len(_faiss_docs) and _faiss_docs[idx] in search_pool:
                    logger.info(f"[FORMULA_RAG] Layer 2 FAISS hit: {_faiss_docs[idx]['id']}")
                    return _faiss_docs[idx]

            # Expanded search across all docs if pool had no matches
            if search_pool is not docs:
                _, I2 = _faiss_index.search(emb, k=1)
                if len(I2[0]) > 0 and 0 <= I2[0][0] < len(_faiss_docs):
                    logger.info(f"[FORMULA_RAG] Layer 2 FAISS fallback hit: {_faiss_docs[I2[0][0]]['id']}")
                    return _faiss_docs[I2[0][0]]

        except Exception as e:
            logger.warning(f"[FORMULA_RAG] FAISS search failed: {e}")

    if candidates:
        return candidates[0]

    logger.warning("[FORMULA_RAG] No formula found")
    return None


# ══════════════════════════════════════════════════════════════
# LangGraph node
# ══════════════════════════════════════════════════════════════

# Module-level docs — loaded once at first node call
_formula_docs: Optional[list] = None


def _get_formula_docs() -> list[dict]:
    global _formula_docs
    if _formula_docs is None:
        _formula_docs = load_formula_db()
    return _formula_docs


def formula_rag_node(state: dict) -> dict:
    """
    Node 4b: Retrieve best formula, inject into parsed_physics["formulas"].
    Falls back to LLM-proposed formulas if retrieval fails.
    """
    parsed = state.get("parsed_physics", {})
    question = state.get("question", "")
    formula_rag_failed = False

    try:
        docs = _get_formula_docs()
        formula_doc = retrieve_formula(parsed, docs, question)
    except Exception as e:
        logger.error(f"[FORMULA_RAG] Node failed: {e}")
        formula_doc = None
        formula_rag_failed = True

    if formula_doc:
        updated_parsed = {
            **parsed,
            "formulas": [formula_doc["formula_sympy"]],
            "_formula_doc": formula_doc,
        }
        logger.info(f"[FORMULA_RAG] Using formula: {formula_doc['formula_sympy']}")
    else:
        formula_rag_failed = True
        updated_parsed = parsed  # keep LLM-proposed formulas from physics_parser
        logger.warning("[FORMULA_RAG] Falling back to LLM-proposed formulas")

    return {
        **state,
        "parsed_physics": updated_parsed,
        "_formula_rag_failed": formula_rag_failed,
    }
