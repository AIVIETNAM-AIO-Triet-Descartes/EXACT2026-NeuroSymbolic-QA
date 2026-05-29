# Track 2 — Known Weaknesses

## 1. Coulomb Vector Problems (LD* rows)

**Affected:** All LD* rows (multi-charge electrostatics)

**Symptom:** `source=llm_fallback`, `answer=""`

**Root cause:** LD* problems require vector superposition — compute force from each charge pair, decompose into x/y components using sin/cos, sum components, find magnitude. The scalar SymPy solver (`_solve_single`, `_solve_multi_step`) has no concept of vector direction or geometric configuration.

**Example:**
> Three charges q1, q2, q3 at corners of equilateral triangle. Find net force on q1.

SymPy can solve `F = k*q1*q2/r**2` for a single pair but cannot handle angle decomposition or superposition across multiple pairs.

**Fix needed:** Extend `sympy_solver.py` with a vector solver that:
- Detects multi-charge geometry from `parsed_physics`
- Builds coordinate system from given positions
- Computes pairwise Coulomb forces as vectors
- Sums and returns magnitude

---

## 2. Formula Database Coverage (20 formulas only)

**Affected:** Any question whose formula is not in `data/rag/physics_formulas.json`

**Symptom:** `formula_rag_node` returns no candidates → SymPy has no formula → `llm_fallback`

**Root cause:** Formula DB has only 20 entries covering basic circuits and electrostatics. Missing: magnetic fields, optics, thermodynamics, mechanics, AC circuits, etc.

**Fix needed:** Expand `physics_formulas.json` with more formulas. Each entry needs `formula_sympy`, `domain`, `variables`, `keywords` for retrieval to work.

---

## 3. Variable Extraction Reliability (LLM-dependent)

**Affected:** Full pipeline (physics_parser node)

**Symptom:** `given={}` or `find=""` → confidence drops to 0.3 → solver cannot proceed

**Root cause:** `physics_parser_node` delegates to `LLMReasoner.parse_physics_question()`. If LLM returns malformed JSON or misses variables, downstream nodes have no data to work with. Regex fallback in `demo_type2.py` shows this is fixable without LLM but covers limited patterns.

**Fix needed:** Improve `PHYSICS_PARSE_PROMPT` with more few-shot examples, or add a regex pre-pass before LLM call to extract obvious `sym = value unit` assignments.

---

## 4. Voltage Symbol Inconsistency (U vs V) ✅ RESOLVED

**Affected:** ~~Formulas using `U` for voltage (formula_012)~~

**Fix applied (2026-05-28):**
1. **DB fix** — `formula_012` normalized: `U → V` in `formula_sympy`, `variables`, `example_cot`, `keywords`. `formula_015` normalized: `E_field → E` (consistent with `formula_020`). FAISS index rebuilt.
2. **Runtime normalize** — `_inject_symbol_aliases()` added to `formula_rag.py`. After retrieval, compares `formula_doc["variables"]` against `parsed["given"]` and injects bidirectional aliases for known pairs: `U↔V` (voltage), `W↔E` (energy), `t↔T` (time). Handles Vietnamese curriculum notation without requiring DB changes.

---

## 5. MULTI_STEP Chain Termination

**Affected:** Multi-step problems where intermediate variable names differ between formulas

**Symptom:** `_solve_multi_step` loops through all formulas but never accumulates `find` variable

**Root cause:** Chain propagation checks `str(unknown) == find`. If SymPy names the solved symbol differently (e.g., subscript vs plain), the check fails silently.

**Fix needed:** Add fuzzy symbol matching in `_solve_multi_step` accumulated dict lookup.
