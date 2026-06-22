# CV — Project Description: EXACT 2026 Neuro-Symbolic Physics QA

> Target roles: **Data Scientist / AI Engineer / ML Engineer**.
> Numbers below are taken from actual work in the project (no ranking claimed — official results not yet published).

---

## Short version (CV Projects section, 3–4 lines)

**Neuro-Symbolic Physics Question-Answering System** — *EXACT 2026 (IEEE IJCNN/WCCI 2026, URA Research Group @ HCMUT)* · **Team Leader & Lead Engineer (Track 2)**

Led the design and build of an explainable physics QA pipeline (rule-based classifier → formula RAG → SymPy/vector symbolic solvers → LLM Program-Aided fallback) over a **1,352-problem** dataset, constrained to **open-source LLMs ≤8B** served via vLLM. Raised the deterministic (no-LLM) solver accuracy **from 275 to 401 correct (+46%) with zero regression** through systematic root-cause debugging and an eval-gated workflow, and implemented a **PAL (Program-Aided LM) code-generation + sandboxed-execution fallback** to eliminate LLM arithmetic hallucination. Shipped a spec-compliant `/predict` HTTP service and vLLM model-verification endpoint for live grading.

---

## Medium version (final, ~5 bullets)

**Neuro-Symbolic Physics Question-Answering System — EXACT 2026 XAI Challenge**
*IEEE IJCNN / WCCI 2026, URA Research Group @ HCMUT* — **Team Leader & Lead Engineer, Track 2**

- Led the design of an explainable, neuro-symbolic physics QA pipeline (rule-based classifier → formula RAG → SymPy/vector symbolic solvers → LLM fallback) over a **1,352-problem** dataset, constrained to **open-source LLMs ≤8B** served via vLLM.
- Analyzed the dataset into **8 question families** and ran a gap analysis that grew the formula knowledge base from **20 to 53 formulas (2→5 domains)**, lifting estimated coverage from **~35% to ~85%**.
- Raised the deterministic (no-LLM) solver from **275 → 401 correct answers (+46%) with zero regression** via root-cause debugging (sign/magnitude, geometry mapping, prose value extraction, retrieval re-ranking) under a strict before/after, eval-gated workflow.
- Implemented a **Program-Aided LM (PAL) fallback** — the LLM writes Python, a hardened sandbox executes it — to eliminate arithmetic hallucination from a 7B model; measured it lifting arithmetic-heavy problems **59% → 85%**.
- Selected **Qwen2.5-7B-Instruct** (rejecting DeepSeek-R1-8B for the 60s-latency risk) and deployed a spec-compliant `POST /predict` service with a proxied `/v1/models` model-verification endpoint on cloud GPU.

---

## Long version (portfolio / LinkedIn / 2-page CV, 8–12 lines)

**Neuro-Symbolic Physics Question-Answering System — EXACT 2026 XAI Challenge**
*IEEE IJCNN / WCCI 2026 (Maastricht), hosted by URA Research Group, HCMUT* — **Team Leader & Lead Engineer, Track 2 (Physics QA)**

- **Analyzed** the full **1,352-problem** physics dataset from scratch — classified it into **8 prefix-based families** (Coulomb-force, AC-RLC, EM-energy, capacitors, induction, measurement-error, point-field, resonance-Yes/No), characterizing answer types (numeric, vector, qualitative, multi-answer, Yes/No) and per-group distribution to drive pipeline design.
- **Ran a coverage gap analysis** showing the initial formula store (20 formulas, 2 domains) reached only **~35%** of the dataset; specified and built a **53-formula, 5-domain** knowledge base (circuits, electrostatics, AC circuits, electromagnetism, measurement) with hybrid **keyword + FAISS** retrieval, lifting estimated coverage to **~85%**, and documented every formula's source (textbooks / dataset-derived / generated) for the competition's Data Disclosure.
- **Designed the end-to-end neuro-symbolic architecture**: rule-based classifier → Formula RAG → SymPy + custom **vector solver** (multi-charge Coulomb/E-field geometry, strategies A–F) → specialized solvers (resonance, error-propagation, parallel-circuit, multi-formula dependency chaining) → **LLM Program-Aided (PAL) fallback** with a self-repair retry, prioritizing deterministic symbolic correctness over LLM fluency.
- **Improved the deterministic no-LLM floor from 275 → 401 correct answers (+46%, 0 regression)** by diagnosing and fixing real, general bugs — physical-magnitude sign selection, charge-to-vertex geometry mapping, prose ("phrasal") value extraction (~446 recovered cases), Unicode minus/notation normalization, retrieval solvability re-ranking, and classifier mis-routing — each measured before/after and gated against regressions, deliberately avoiding sample overfitting.
- **Built the PAL fallback** (LLM writes Python; a hardened deny-listed sandbox executes it) to remove arithmetic hallucination from a 7B model; empirically validated it (vector-aware prompt + error-driven self-repair improved a hard subset 24% → 40% and arithmetic-heavy problems 59% → 85%).
- **Engineered the production inference stack** under an 8GB-VRAM dev constraint: llama.cpp + Q4_K_M GGUF for local dev, vLLM + FP16 for the GPU server; **evaluated and rejected DeepSeek-R1-8B** (always-on reasoning risked the 60s/query limit and starved structured parsing) and **selected Qwen2.5-7B-Instruct** as the backbone.
- **Delivered a spec-compliant deployment**: a single unified `POST /predict` endpoint (type-routed, JSON-list output, ASCII units, structured `reasoning` object, graceful non-crashing error handling) plus a proxied `GET /v1/models` so the committee can verify the served ≤8B model — deployed on a cloud GPU (RunPod) with a documented restart/failover runbook.

---

## Key metrics (for quick reference)

| Metric | Value |
|--------|-------|
| Dataset size analyzed | 1,352 physics problems, 8 families |
| Formula KB | 20 → **53 formulas**, 2 → **5 domains** |
| Coverage (formula) | ~35% → ~85% (estimated) |
| Deterministic floor | **275 → 401 correct (+46%), 0 regression** |
| Confident-wrong (vector solver) | 79 → **25** (−68%) |
| PAL on arithmetic problems | 59% → **85%** (measured, hard subset 24%→40%) |
| Model | Qwen2.5-7B-Instruct (FP16 vLLM / Q4_K_M dev) — ≤8B compliant |
| Test suite | 99 tests passing |

## Tech stack / skills demonstrated

`Python` · `SymPy` (symbolic computation) · `FAISS` + `sentence-transformers` (RAG) · `vLLM` / `llama.cpp` (LLM serving, OpenAI-compatible) · `FastAPI` · `Program-Aided LM (PAL)` + sandboxed code execution · neuro-symbolic reasoning · evaluation methodology (before/after, regression gating, root-cause analysis) · cloud GPU deployment (RunPod) · prompt engineering · technical leadership.

---

### Notes on accuracy (for you to confirm before using)

- **Model:** reflected as *Qwen2.5-7B-Instruct* (the backbone actually served) with *DeepSeek-R1-8B evaluated-and-rejected* — this is what the work history shows; the original prompt's "DeepSeek backbone" is superseded.
- **Formula KB:** stated as **53 formulas / 5 domains** (verified in `data/rag/physics_formulas.json`), not 52/6.
- **Data split (944/200/208):** ✅ **VERIFIED** against `data/physics/physics_{train,dev,test}.csv` — exactly 944 / 200 / 208 = 1,352, with all 8 prefix families present in every split (stratified). Safe to use.
- **Coverage (~35%→~85%):** a documented **formula-coverage estimate** from the gap analysis (`docs/docs_vytriet/track2_reference.md §4`) — i.e. the formula KB has the formulas needed for ~85% of the dataset. It is NOT a measured solve-accuracy. Keep the word "estimated". (Separately, the measured deterministic no-LLM correct count is 401 — a distinct metric, already cited.)
