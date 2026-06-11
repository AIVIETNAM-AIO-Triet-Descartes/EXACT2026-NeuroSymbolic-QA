"""
pipeline/type2/formula_rag.py

LangGraph node [4b]: Retrieve best-matching formula from knowledge base.
Hybrid strategy: Layer 1 keyword/exact match → Layer 2 FAISS semantic search.
No LangChain — calls faiss and sentence-transformers directly.
"""

import json
import pickle
import logging
import re
from typing import Optional

from sympy import sympify, Symbol

logger = logging.getLogger(__name__)

# SymPy builtins that must stay as functions/constants, NOT be re-declared as
# symbols. Mirror of sympy_solver._MATH_FNS — keeps validation consistent with
# how the solver actually parses formulas.
_MATH_FNS = frozenset({
    "sqrt", "sin", "cos", "tan", "exp", "log", "abs", "pi",
    "Sum", "Rational", "Integer", "Float",
})

# ══════════════════════════════════════════════════════════════
# Formula DB loader
# ══════════════════════════════════════════════════════════════

def _sympify_locals(expr: str) -> dict:
    """Declare every identifier in `expr` as a plain Symbol so physics symbols
    (N, I, E, S, O, …) aren't mistaken for SymPy builtins (N=evalf, I=imaginary
    unit, E=Euler). Same approach as sympy_solver._make_sym_dict."""
    tokens = set(re.findall(r'\b[A-Za-z_]\w*\b', expr))
    return {t: Symbol(t) for t in tokens if t not in _MATH_FNS}


def load_formula_db(path: str = "data/rag/physics_formulas.json") -> list[dict]:
    """
    Load formula knowledge base, validate each entry with sympify.
    Returns only entries whose formula_sympy parses cleanly.
    Called at startup — production version of tests/physics_formula.py logic.

    Validation declares all identifiers as Symbols (locals) — matches the solver,
    so physics symbols like N (turns) or I (current) are not rejected as the
    SymPy builtins N()/I (see docs/formula_rag_review.md Vấn đề 3).
    """
    with open(path, encoding="utf-8") as f:
        docs = json.load(f)
    valid = []
    for doc in docs:
        try:
            rhs = doc["formula_sympy"].split("=")[-1].strip()
            sympify(rhs, locals=_sympify_locals(rhs))
            valid.append(doc)
        except Exception as e:
            logger.warning(f"[FORMULA_DB] Invalid formula_sympy in {doc['id']}: {e}, skipping")
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

        # Drift guard: JSON edited but index not rebuilt → new formulas invisible
        # to FAISS Layer-2 (formula_rag_review §4). Warn loudly; don't crash.
        try:
            json_docs = load_formula_db()
            if len(json_docs) != index.ntotal:
                logger.warning(
                    f"[FORMULA_RAG] MISMATCH: physics_formulas.json has "
                    f"{len(json_docs)} valid formulas but FAISS index has "
                    f"{index.ntotal} vectors. Run scripts/build_faiss_index.py "
                    f"to rebuild — new formulas are NOT searchable until then."
                )
        except Exception:
            pass  # mismatch check is best-effort

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
# Symbol alias normalization
# ══════════════════════════════════════════════════════════════

# Known equivalent symbol pairs (bidirectional).
# Covers notation differences between curricula (e.g. Vietnamese: U for voltage)
# and common textbook variations.
# NOTE: U↔V removed (2026-06-06). U (hiệu điện thế) and V (điện thế) are now
# DISTINCT symbols — the parser/regex normalizes voltage to U upstream, and the
# RAG DB uses U for hiệu điện thế, V only for điện thế (V = k*q/r). Aliasing them
# here would wrongly bridge potential difference with electric potential.
_SYMBOL_ALIASES: list[tuple[str, str]] = [
    ("W", "E"),       # energy: W (work/energy) vs E
    ("t", "T"),       # time: lowercase vs uppercase
    ("Z_L", "X_L"),   # inductive reactance: VN Z_L (canonical) ↔ international X_L
    ("Z_C", "X_C"),   # capacitive reactance: VN Z_C (canonical) ↔ international X_C
]


def _inject_symbol_aliases(parsed: dict, formula_doc: dict) -> dict:
    """
    Compare formula_doc["variables"] keys against parsed["given"] keys.
    For each known alias pair, if one side is in the formula but the other
    side is in given (and not already present), inject the missing alias so
    the solver can substitute correctly.

    Returns a new parsed dict with updated "given" (original is not mutated).
    """
    formula_vars: set[str] = set(formula_doc.get("variables", {}).keys())
    given: dict = dict(parsed.get("given", {}))
    injected: list[str] = []

    for sym_a, sym_b in _SYMBOL_ALIASES:
        a_in_formula = sym_a in formula_vars
        b_in_formula = sym_b in formula_vars
        a_in_given = sym_a in given
        b_in_given = sym_b in given

        # formula uses A but given has B → inject A = given[B]
        if a_in_formula and b_in_given and sym_a not in given:
            given[sym_a] = given[sym_b]
            injected.append(f"{sym_a}={sym_b}")

        # formula uses B but given has A → inject B = given[A]
        if b_in_formula and a_in_given and sym_b not in given:
            given[sym_b] = given[sym_a]
            injected.append(f"{sym_b}={sym_a}")

    if injected:
        logger.info(f"[FORMULA_RAG] Alias injected for {formula_doc['id']}: {injected}")

    return {**parsed, "given": given}


# ══════════════════════════════════════════════════════════════
# Dependency-chain builder (multi-formula problems, e.g. RLC: Z_L→Z_C→Z)
# ══════════════════════════════════════════════════════════════

# Universal bridges not always present as DB entries (angular frequency from f).
_BRIDGE_FORMULAS = {"omega": "omega = 2 * pi * f"}


def _rhs_symbols(formula_sympy: str) -> list[str]:
    """Identifiers on the RHS of 'LHS = RHS', minus SymPy builtins."""
    if "=" not in formula_sympy:
        return []
    rhs = formula_sympy.split("=", 1)[1]
    return [t for t in set(re.findall(r'[A-Za-z_]\w*', rhs)) if t not in _MATH_FNS]


def build_formula_chain(
    target_sympy: str,
    all_docs: list[dict],
    given_keys: set,
    max_depth: int = 8,
) -> list[str]:
    """
    Resolve the dependency chain for `target_sympy` over the formula DB.

    A formula's RHS symbol that is NOT in `given` is an intermediate unknown; if
    some DB formula has that symbol as its LHS, pull it in (recursively) so the
    solver can compute it first. Returns formulas in dependency-first order
    (leaves → target last), ready for `_solve_multi_step` to chain.

    Example (RLC impedance): given {R,L,C,f}, target "Z = sqrt(R**2+(Z_L-Z_C)**2)"
      → ["omega = 2*pi*f", "Z_L = omega*L", "Z_C = 1/(omega*C)", "Z = sqrt(...)"]
    """
    by_lhs: dict[str, str] = {}
    for d in all_docs:
        fs = d.get("formula_sympy", "")
        if "=" in fs:
            lhs = fs.split("=", 1)[0].strip()
            if lhs and lhs not in by_lhs:
                by_lhs[lhs] = fs
    for sym, fs in _BRIDGE_FORMULAS.items():
        by_lhs.setdefault(sym, fs)

    chain: list[str] = []
    visiting: set[str] = set()

    def resolve(fs: str, depth: int) -> None:
        if fs in chain or fs in visiting or depth > max_depth:
            return
        visiting.add(fs)
        for sym in _rhs_symbols(fs):
            if sym in given_keys:
                continue
            dep = by_lhs.get(sym)
            if dep and dep != fs:
                resolve(dep, depth + 1)
        visiting.discard(fs)
        if fs not in chain:
            chain.append(fs)

    resolve(target_sympy, 0)
    return chain


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
        # Normalize symbol aliases before solver substitution
        parsed = _inject_symbol_aliases(parsed, formula_doc)
        given_keys = set((parsed.get("given") or {}).keys())
        # Resolve dependency chain so multi-formula problems (RLC Z_L→Z_C→Z,
        # solenoid n→B, …) get all intermediate formulas, not just the target.
        chain = build_formula_chain(formula_doc["formula_sympy"], docs, given_keys)
        updated_parsed = {
            **parsed,
            "formulas": chain or [formula_doc["formula_sympy"]],
            "_formula_doc": formula_doc,
        }
        logger.info(
            f"[FORMULA_RAG] target={formula_doc['formula_sympy']} "
            f"chain={chain if len(chain) > 1 else '(single)'}"
        )
    else:
        formula_rag_failed = True
        updated_parsed = parsed  # keep LLM-proposed formulas from physics_parser
        logger.warning("[FORMULA_RAG] Falling back to LLM-proposed formulas")

    return {
        **state,
        "parsed_physics": updated_parsed,
        "_formula_rag_failed": formula_rag_failed,
    }
