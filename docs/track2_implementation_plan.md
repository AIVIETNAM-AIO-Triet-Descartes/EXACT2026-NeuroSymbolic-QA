# Track 2 — Physics Pipeline: Implementation Plan

**Scope:** Build all stub files under `pipeline/type2/` into a working pipeline.  
**Deadline:** Competition active phase ends 2026-05-30. Target: functional baseline by 2026-05-24.  
**Constraint:** All LLM inference must use local open-source models ≤8B params. No closed-source API calls.

---

## 1. Pipeline Overview

```
HTTP Request
    │
    ▼  (Router classified query_type = "type2")
[3b] PhysicsParser       ← LLM extracts variables + identifies domain/formula hints
    │
    ▼
[4b] FormulaRAG          ← Hybrid retrieval: keyword match → FAISS (no LangChain)
    │
    ▼
[5b] SympySolver         ← SymPy solves by PhysicsQuestionType strategy
    │
    ▼
[6b] SelfVerifier        ← Wraps type2_validation.validate_sympy_result()
    │
    ▼
[6c] CotBuilder          ← Pure string formatting from solver steps (no LLM)
    │
    ▼
[7]  ExplainerAgent      ← LLM narrates explanation from SolverResult
    │
    ▼
[8]  ResponseBuilder     ← Pack JSON: {answer, explanation, cot, confidence}
```

**State fields used by Track 2** (defined in `pipeline/state.py` — do not redefine):

```python
# Input
question: str
query_type: str                     # "type2"

# Track 2
parsed_physics: Optional[dict]      # output of PhysicsParser
sympy_result: Optional[dict]        # output of SympySolver
cot: Optional[list[str]]            # output of CotBuilder

# Shared output
answer: Optional[str]
explanation: Optional[str]
confidence: Optional[float]
solver_result: Optional[SolverResult]
```

---

## 2. Already Implemented — Do Not Rewrite

| File | What exists |
|------|-------------|
| `pipeline/state.py` | `PipelineState` + `SolverResult` TypedDicts — complete |
| `pipeline/type2/type2_classifier.py` | `PhysicsClassifier.classify_physics()` + `PhysicsQuestionType` enum — complete |
| `pipeline/type2/type2_validation.py` | `validate_sympy_result()` + `validate_multi_target_hint()` — complete |
| `tests/physics_formula.py` | Validator script — keep as standalone CLI, refactor to `if __name__ == "__main__"`, import `load_formula_db()` from `formula_rag.py` |

---

## 3. Component Specifications

### 3.1 PhysicsParser — `pipeline/type2/physics_parser.py`

**Responsibility:** Extract structured data from raw physics question text via LLM.

**Input:** `state["question"]: str`

**Output** (written to `state["parsed_physics"]`):
```python
{
    "given": {"V": 10.0, "I": 2.0},    # known variables with numeric values
    "find": "R",                         # target symbol — matches PhysicsClassifier.target_variable
    "domain": "circuits",                # "circuits" | "electrostatics"
    "formulas": ["V = I * R"],           # LLM-proposed hints, refined by FormulaRAG
    "units": {"V": "V", "I": "A"}       # units of given values (for unit conversion)
}
```

**Integration with PhysicsClassifier:** Call `PhysicsClassifier.classify_physics(question)` first. Use `domain` and `target_variable` as structured priors before LLM call — reduces hallucination.

**LLM call:** Delegate to `LLMReasoner.parse_physics_question(question)` — already implemented in `llm/llm_reasoner.py`. PhysicsParser node is a thin wrapper:

```python
def physics_parser_node(state: PipelineState) -> PipelineState:
    reasoner = get_shared_reasoner()
    classified = PhysicsClassifier().classify_physics(state["question"])
    parsed = reasoner.parse_physics_question(state["question"])
    # Override domain/find from classifier if LLM missed them
    if not parsed["find"] and classified.target_variable:
        parsed["find"] = classified.target_variable
    if parsed["domain"] == "general":
        parsed["domain"] = classified.domain
    parsed["question_type"] = classified.question_type.value
    return {**state, "parsed_physics": parsed}
```

**Fallback:** Handled inside `parse_physics_question()` — retries once with simplified prompt. On total failure returns `{"given": {}, "find": "", "domain": "general", "formulas": [], "units": {}}`. Set `confidence = 0.3` in node wrapper when `find == ""`.

**Error contract:** Wrap in `try/except`. Never raise — always return dict.

---

### 3.2 FormulaRAG — `pipeline/type2/formula_rag.py` *(new file)*

**Responsibility:** Retrieve the correct `formula_sympy` string from knowledge base. Two responsibilities: (1) build/load index; (2) query at inference time.

#### `load_formula_db(path)` — called at startup

Reads `data/rag/physics_formulas.json`, validates each `formula_sympy` with `sympify()`, returns only valid entries. This is the production version of the logic in `tests/physics_formula.py`.

```python
def load_formula_db(path: str = "data/rag/physics_formulas.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        docs = json.load(f)
    valid = []
    for doc in docs:
        try:
            sympify(doc["formula_sympy"].split("=")[-1].strip())
            valid.append(doc)
        except Exception:
            logger.warning(f"Invalid formula_sympy in {doc['id']}, skipping")
    return valid
```

#### Build FAISS index — `scripts/build_faiss_index.py` (one-time script)

```python
from sentence_transformers import SentenceTransformer
import faiss, pickle, numpy as np

def build_formula_index(docs: list[dict], save_dir: str = "data/formula_index"):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [
        f"{d['domain']}: {d['formula_natural']} — {' '.join(d['keywords'])}"
        for d in docs
    ]
    embeddings = model.encode(texts).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, f"{save_dir}/index.faiss")
    with open(f"{save_dir}/metadata.pkl", "wb") as f:
        pickle.dump(docs, f)
```

Run: `python scripts/build_faiss_index.py` — output saved to `data/formula_index/`.

#### `retrieve_formula(parsed, docs, index, model)` — Hybrid Retrieval

Two-layer strategy: fast exact match first, FAISS only on ambiguity or miss.

```
Layer 1 — Keyword/exact match (deterministic):
    filter docs where doc["domain"] == parsed["domain"]
                  AND parsed["find"] in doc["variables"]
    → if exactly 1 candidate → return immediately, skip FAISS

Layer 2 — FAISS semantic search (only if Layer 1 returns 0 or 2+ candidates):
    search_pool = candidates (if any) else all docs
    query = f"{domain} {find} {question}"
    embed → search top-k → return best match
```

**Fallback:** FAISS index not found or query exception → return `parsed_physics["formulas"]` as-is. Log `formula_rag_failed=True`.

**No LangChain** — call FAISS and sentence-transformers directly. LangChain abstraction is overkill for ~100 documents.

---

### 3.3 SympySolver — `pipeline/type2/sympy_solver.py`

**Responsibility:** Solve physics equation symbolically. Zero arithmetic hallucination.

**Input:** `state["parsed_physics"]` (with `given`, `find`, `formulas`, `units`)

**Dispatch by `PhysicsQuestionType`** (from `type2_classifier`):

| Type | Strategy |
|------|----------|
| `SINGLE_FORMULA` | Parse 1 formula → substitute knowns → `solve()` for target |
| `MULTI_STEP` | Chain formulas sequentially — step N output feeds step N+1 as known |
| `CIRCUIT` | Build KVL/KCL equation system → `linsolve()` |
| `ELECTROSTATIC` | Match Coulomb / capacitance formula → `solve()` |

**Core skeleton:**
```python
from sympy import symbols, Eq, solve, sympify
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def solve_physics(parsed: dict, q_type: PhysicsQuestionType, timeout: int = 10) -> dict:
    """
    1. Declare SymPy symbols for all variables in formula
    2. Parse formula string → SymPy Eq via sympify
    3. Substitute known values from parsed["given"] (with unit conversion)
    4. Solve for parsed["find"]
    5. Return {answer, unit, steps, source}
    """
```

**Timeout:** `concurrent.futures.ThreadPoolExecutor` with `timeout` parameter (works on Windows; `signal.SIGALRM` Linux-only).

**Multi-formula:** If `formulas` has multiple entries, try each in order. First successful solve wins. Log which formula solved it.

**Output** (written to `state["sympy_result"]`):
```python
{
    "answer": "5.0",
    "unit": "Ω",
    "steps": [
        "Given: V=10V, I=2A",
        "Formula: V = I * R",
        "Substitute: 10 = 2 * R",
        "Solve: R = 10/2",
        "Result: R = 5.0 Ω"
    ],
    "raw_expr": "R = V/I",
    "source": "sympy"
}
```

**Fallback (timeout or solve failure):** `{"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}`, `confidence = 0.5`.

---

### 3.4 SelfVerifier — wraps `pipeline/type2/type2_validation.py`

**Do NOT create `self_verifier.py`.** Logic already exists:
- `validate_sympy_result(value, target_variable)` → `ValidationResult`
- `validate_multi_target_hint(question)` → `bool`

SelfVerifier node in LangGraph is a thin wrapper:

```python
def self_verifier_node(state: PipelineState) -> PipelineState:
    sympy_result = state.get("sympy_result", {})
    parsed = state.get("parsed_physics", {})
    val = validate_sympy_result(
        value=sympy_result.get("answer"),
        target_variable=parsed.get("find"),
    )
    confidence = state.get("confidence", 1.0)
    if not val.is_valid:
        confidence = 0.4
        logger.warning(f"self_verify_failed: {val.errors}")
    for w in val.warnings:
        logger.info(f"self_verify_warning: {w}")
    return {**state, "confidence": confidence}
```

**Confidence rules:**
- `is_valid=True` → `confidence` unchanged
- `is_valid=False` → `confidence = 0.4`, log `self_verify_failed=True`
- Exception inside validate → `confidence` unchanged, log `self_verify_skipped=True`

**Never blocks pipeline.**

---

### 3.5 CotBuilder — `pipeline/type2/cot_builder.py`

**Responsibility:** Format `sympy_result["steps"]` into `cot: list[str]` for API response.

**No LLM call** — pure string formatting. Fast, deterministic, no failure mode.

**Output format:**
```python
[
    "Step 1 — Identify known quantities: V = 10V, I = 2A",
    "Step 2 — Select formula: Ohm's Law — V = I × R",
    "Step 3 — Substitute values: 10 = 2 × R",
    "Step 4 — Solve for R: R = 10 ÷ 2 = 5",
    "Step 5 — Result: R = 5.0 Ω"
]
```

**Fallback (empty solver steps):** Build minimal CoT from `parsed_physics`:
```python
["Given: ...", "Find: ...", "Unable to complete calculation — see explanation"]
```

---

### 3.6 ExplainerAgent — `pipeline/type2/explainer.py`

**Shared with Track 1** — receives `SolverResult` struct only. No track-specific logic here.

**LLM call:** Delegate to `LLMReasoner.explain_physics(question, answer, unit, steps)` — already implemented in `llm/llm_reasoner.py`. Node wrapper:

```python
def explainer_node_type2(state: PipelineState) -> PipelineState:
    reasoner = get_shared_reasoner()
    sr = state["solver_result"]
    explanation = reasoner.explain_physics(
        question=state["question"],
        answer=sr["answer"],
        unit=sr.get("unit", ""),
        steps=sr.get("steps", []),
    )
    return {**state, "explanation": explanation}
```

**Fallback:** Handled inside `explain_physics()` — retries once, then hardcoded `f"The answer is {answer} {unit}."`. Prompt template: `PHYSICS_EXPLANATION_PROMPT` in `llm/prompt_templates.py`.

---

### 3.7 ResonanceSolver — `pipeline/type2/resonance_solver.py` *(new file — CHLT)*

**Responsibility:** Answer Yes/No resonance questions for the **CHLT** prefix (20 problems, 100% gap). These do **not** use FormulaRAG or `sympy.solve()` — pure value comparison.

**Why a separate solver:** CHLT asks "does the circuit experience resonance?" → compute resonant frequency `f₀ = 1/(2π√(LC))` and compare to the driving frequency `f`. No equation to solve, no formula to retrieve.

**Trigger:** `PhysicsQuestionType.YES_NO` (already in enum). Dispatched from `sympy_solver_node` (see Integration below).

**Entry point** — same `sympy_result` contract as other solvers:
```python
def solve_resonance(parsed: dict, question: str = "") -> dict:
    """
    Input  : parsed["given"] must contain L (H), C (F), f (Hz).
    Output : {"answer": "Yes"|"No", "unit": "", "steps": [...], "source": "resonance"}
    Logic  : f0 = 1 / (2*pi*sqrt(L*C));  Yes if abs(f - f0)/f0 < TOL else No.
             TOL ~ 0.01–0.02 (relative). Tune against CHLT examples in track2_data_info.md.
    """
```

**Output example:**
```python
{
    "answer": "No",
    "unit": "",
    "steps": [
        "Given: L=0.5 H, C=20 µF, f=40 Hz",
        "Resonant frequency: f0 = 1/(2π√(LC)) = 50.3 Hz",
        "Compare: |40 − 50.3|/50.3 = 0.20 > 0.01 → not resonant",
    ],
    "source": "resonance",
}
```

**Confidence:** deterministic → `1.0` (treat `"resonance"` like `"sympy"` in the confidence map).

**Fallback:** missing L/C/f after parse → `{"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}` (lets LLM CoT handle it). Never raise.

**Parsing note:** CHLT `given` extraction can reuse the regex helpers in `scripts/demo_type2.py` (`_normalize_superscripts`, unit conversion) or a small local regex. Does **not** depend on the LLM parser.

---

### 3.8 ErrorSolver — `pipeline/type2/error_solver.py` *(new file — THCB)*

**Responsibility:** Measurement-error problems for the **THCB** prefix (80 problems, 100% gap). Explicit formula computation — **no `sympy.solve()`**. Largest multi-answer group (23/80 use `;`).

**Trigger:** `PhysicsQuestionType.ERROR_CALC` (single value) and `PhysicsQuestionType.MULTI_ANSWER` (≥2 values). Both already in enum.

**Sub-cases** (detect from question keywords; formulas per `track2_formula_gaps.md` F-043…F-048):

| Sub-case | Formula | Example IDs |
|----------|---------|-------------|
| absolute error (instrument) | `Δx = least_count / 2` (or given directly) | THCB001 |
| relative error | `δ = Δx / x * 100` (%) | THCB002 |
| error propagation — product/quotient | `δZ = δA + δB` (Z=A·B or A/B) | THCB003 |
| error propagation — sum/diff | `ΔZ = ΔA + ΔB` (Z=A±B) | THCB009 |
| mean + random error | `x̄ = Σxᵢ/n`, `Δx̄ = Σ|xᵢ−x̄|/n` | THCB007 |
| absolute error from true value | `Δx = |x_measured − x_true|` | THCB087 |

**Entry point:**
```python
def solve_error(parsed: dict, question: str = "") -> dict:
    """
    Output (single) : {"answer": "3.57", "unit": "%", "steps": [...], "source": "error_calc"}
    Output (multi)  : {"answer": "0.6; 1.2", "unit": "cm; %", "steps": [...], "source": "error_calc"}
    """
```

**Multi-answer format (critical):** when the question asks for ≥2 quantities ("calculate absolute error AND relative error"), join with `"; "` in BOTH `answer` and `unit`, in the same order. Matches dataset convention (`Answer: 0.6; 1.2 | Unit: cm; %`).

**Confidence:** deterministic → `1.0`.

**Fallback:** unrecognized sub-case or missing data → `source="llm_fallback"`. Never raise.

---

## 4. SolverResult — Unified Interface

Before handing off to Explainer, SympySolver must populate:

```python
SolverResult(
    answer=str(sympy_result["answer"]),
    unit=sympy_result.get("unit"),
    steps=sympy_result.get("steps", []),
    fol=None,                           # Type 2 has no FOL
    source=sympy_result.get("source"),  # "sympy" | "llm_fallback"
    confidence=state["confidence"],
)
```

`source` → `confidence` baseline:
- `"sympy"` + self_verify OK → `1.0`
- `"sympy"` + self_verify failed → `0.4`
- `"resonance"` (CHLT) / `"error_calc"` (THCB) → `1.0` (deterministic, treat like `"sympy"`)
- `"llm_fallback"` → `0.5`

**Integration — dispatch in `sympy_solver_node`** (the only edit to existing solver code; one branch, ~6 lines):
```python
# pipeline/type2/sympy_solver.py — inside sympy_solver_node, before solve_physics()
if q_type == PhysicsQuestionType.YES_NO:
    from pipeline.type2.resonance_solver import solve_resonance
    sympy_result = solve_resonance(parsed, state.get("question", ""))
elif q_type in (PhysicsQuestionType.ERROR_CALC, PhysicsQuestionType.MULTI_ANSWER):
    from pipeline.type2.error_solver import solve_error
    sympy_result = solve_error(parsed, state.get("question", ""))
else:
    sympy_result = solve_physics(parsed, q_type)   # existing path
# existing vector_solver + llm_fallback handling continues unchanged
```
Self-verifier downgrades confidence only for numeric answers; Yes/No and multi-answer strings skip numeric validation (extend `validate_sympy_result` if needed, but do not block).

---

## 5. Implementation Tasks

### Phase 1 — Core pipeline (ship before eval)

| Task | File | Note |
|------|------|------|
| T2-00: Build FAISS index | `scripts/build_faiss_index.py` | Prerequisite for FormulaRAG |
| T2-01: `load_formula_db()` + hybrid `retrieve_formula()` | `pipeline/type2/formula_rag.py` | Layer 1 keyword + Layer 2 FAISS |
| T2-02: `PhysicsParser` node wrapper (LLM call via `llm_reasoner.parse_physics_question()`) | `pipeline/type2/physics_parser.py` | LLM logic already in llm_reasoner |
| T2-03: `SympySolver.solve()` with 4-type dispatch + timeout | `pipeline/type2/sympy_solver.py` | ThreadPoolExecutor timeout |
| T2-04: `CotBuilder.build()` pure formatter | `pipeline/type2/cot_builder.py` | No LLM |
| T2-05: `ExplainerAgent` node wrapper (LLM call via `llm_reasoner.explain_physics()`) | `pipeline/type2/explainer.py` | LLM logic already in llm_reasoner |
| T2-06: SelfVerifier node wrapper | thin function in orchestration layer | Wraps type2_validation.py |
| T2-07: Wire LangGraph nodes for Track 2 | `api/main.py` | physics_parser→formula_rag→sympy_solver→self_verifier→cot_builder→explainer |
| T2-08: Refactor `tests/physics_formula.py` | `tests/physics_formula.py` | Add `main()`, import `load_formula_db` from formula_rag |
| T2-09: `tests/test_type2.py` — 3 circuit + 2 electrostatics | `tests/test_type2.py` | See Section 6 |

### Phase 2 — Optional enhancements (only if time allows)

| Task | Description |
|------|-------------|
| T2-10: LLM-only fallback CoT path | When SymPy times out, LLM calculates directly with physics CoT prompt |
| T2-11: Code Agent node | LLM generates SymPy code, execute in `subprocess` sandbox with 10s timeout |
| T2-12: Populate FAISS from competition source materials | Post kick-off workshop, replace seed data |
| T2-13: QLoRA fine-tune PhysicsParser | Only if variable extraction accuracy < 70% on eval set |

### Phase 3 — Dedicated solvers for non-RAG prefixes (CHLT + THCB) — independent work package

These two prefixes do **not** use FormulaRAG/`solve()`, so they can be built in parallel with the formula-DB expansion (which covers CH/DDT/NL/LD/DT/TD). Clean boundary: two new files + one dispatch branch in `sympy_solver_node`.

| Task | File | Note |
|------|------|------|
| T2-14: `solve_resonance()` — CHLT Yes/No | `pipeline/type2/resonance_solver.py` *(new)* | §3.7. `f₀=1/(2π√(LC))`, relative-tol compare. 20 problems. |
| T2-15: `solve_error()` — THCB error calc + multi-answer | `pipeline/type2/error_solver.py` *(new)* | §3.8. Sub-cases F-043…F-048, `;`-joined multi-answer. 80 problems. |
| T2-16: Dispatch branch (YES_NO / ERROR_CALC / MULTI_ANSWER) | `pipeline/type2/sympy_solver.py` | §4 Integration snippet — ~6 lines, before `solve_physics()`. |
| T2-17: Tests — CHLT (Yes + No cases) + THCB (single + multi-answer) | `tests/test_type2.py` | ≥4 cases. Use CHLT001/002 + THCB002/087 from track2_data_info.md. |

**Enum/domain already done** (commit 2026-05-31): `YES_NO`, `ERROR_CALC`, `MULTI_ANSWER` types and `measurement` domain exist in `type2_classifier.py` — the owner only consumes them, does not edit the classifier.

---

## 6. Fallback Decision Tree

```
PhysicsParser
    ├─ JSON OK → parsed_physics populated → continue
    └─ JSON fail (2 retries) → minimal struct, confidence=0.3
                               → FormulaRAG skips to LLM-proposed formulas

FormulaRAG (Hybrid)
    ├─ Layer 1 keyword hit (1 match) → verified formula → SympySolver
    ├─ Layer 1 ambiguous (2+ matches) → Layer 2 FAISS disambiguates → SympySolver
    ├─ Layer 1 miss → Layer 2 FAISS full search → SympySolver
    └─ FAISS fail → use LLM-proposed formulas from physics_parser → SympySolver

SympySolver
    ├─ Solve OK → self_verifier → cot_builder → explainer
    ├─ Timeout (>10s) → source="llm_fallback", confidence=0.5 → cot_builder(empty) → explainer
    └─ Exception → same as timeout

SelfVerifier (type2_validation)
    ├─ is_valid=True → confidence unchanged
    ├─ is_valid=False → confidence=0.4, log warning
    └─ Exception → skip, confidence unchanged

Explainer
    ├─ LLM OK → explanation str
    ├─ Fail once → retry simplified
    └─ Fail twice → f"The answer is {answer} {unit}.", confidence=0.3
```

---

## 7. Test Cases

```python
# Circuit — Ohm's Law
{
    "question": "A circuit has voltage 12V and resistance 4Ω. Calculate the current.",
    "expected_answer": "3.0",
    "expected_unit": "A"
}

# Circuit — Parallel resistance
{
    "question": "Two resistors R1=6Ω and R2=3Ω are connected in parallel. Find total resistance.",
    "expected_answer": "2.0",
    "expected_unit": "Ω"
}

# Circuit — Power (MULTI_STEP: I from V/R, then P=I²R)
{
    "question": "A resistor has resistance 5Ω and carries current 2A. Calculate power dissipated.",
    "expected_answer": "20.0",
    "expected_unit": "W"
}

# Electrostatics — Capacitor energy
{
    "question": "A capacitor with capacitance 4F is charged to 3V. Find the energy stored.",
    "expected_answer": "18.0",
    "expected_unit": "J"
}

# Fallback test — ambiguous question, must not crash
{
    "question": "What happens when voltage increases in a circuit?",
    "assert": "response has answer and explanation, confidence > 0, no exception"
}
```

Each test asserts:
1. Response has `answer` and `explanation` (required fields — Dev Rule #3)
2. No unhandled exception
3. `confidence > 0`
4. Numeric answer within 1e-6 tolerance for deterministic cases

---

## 8. Logging Checklist

Every Type 2 request must log these fields:

```json
{
    "query_type": "type2",
    "physics_domain": "circuits",
    "physics_question_type": "single_formula",
    "formula_rag_layer": "keyword",
    "formula_rag_failed": false,
    "sympy_timeout": false,
    "self_verify_result": "ok",
    "solver_source": "sympy",
    "fallback_triggered": false,
    "confidence": 1.0
}
```

---

## 9. File Ownership

| File | Status | Owner |
|------|--------|-------|
| `pipeline/state.py` | **complete** — do not modify | shared |
| `pipeline/type2/type2_classifier.py` | **complete** — do not modify | shared |
| `pipeline/type2/type2_validation.py` | **complete** — do not modify | shared |
| `llm/llm_reasoner.py` | **Track 2 methods added** — `parse_physics_question()`, `explain_physics()` | shared |
| `llm/prompt_templates.py` | **Track 2 templates added** — `PHYSICS_PARSE_PROMPT`, `PHYSICS_EXPLANATION_PROMPT` | shared |
| `llm/inference.py` | **not needed** — logic merged into `llm_reasoner.py` | — |
| `pipeline/type2/physics_parser.py` | stub → implement (calls `llm_reasoner.parse_physics_question()`) | Member 2 |
| `pipeline/type2/formula_rag.py` | new file | Member 2 |
| `pipeline/type2/sympy_solver.py` | stub → implement | Member 2 |
| `pipeline/type2/cot_builder.py` | stub → implement | Member 2 |
| `pipeline/type2/explainer.py` | stub → implement (calls `llm_reasoner.explain_physics()`) | Member 2 |
| `scripts/build_faiss_index.py` | new file | Member 2 |
| `tests/physics_formula.py` | refactor to script with `main()` | Member 2 |
| `tests/test_type2.py` | expand stubs | Member 2 |
| `pipeline/type2/resonance_solver.py` | **new file (CHLT)** — T2-14 | Member 3 |
| `pipeline/type2/error_solver.py` | **new file (THCB)** — T2-15 | Member 3 |
| `pipeline/type2/sympy_solver.py` | **dispatch branch only** — T2-16 (coordinate with solver owner) | Member 3 |
