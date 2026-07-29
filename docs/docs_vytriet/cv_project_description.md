# CV — Project Description: EXACT 2026 Neuro-Symbolic Physics QA

> Target roles: **Data Scientist / AI Engineer / ML Engineer**.
> Numbers from actual work. Top-16 finish confirmed by the user (official competition result). All other metrics measured against the full dataset (1,352 problems) or the specific subset noted.

---

## Short version (CV Projects section, 3–4 lines)

**Neuro-Symbolic Physics Question-Answering System** — *EXACT 2026 (IEEE IJCNN/WCCI 2026, URA Research Group @ HCMUT)* · **Team Leader & Lead Engineer (Track 2)**

Physics QA competitions reward precision under strict constraints (≤8B open-source LLM, 60s/query hard limit) — yet most neuro-symbolic pipelines treat the LLM as the backbone and pay for it in hallucinated arithmetic and unpredictable latency. I led the design and build of an explainable pipeline that **inverts this priority**: deterministic SymPy/vector symbolic solvers handle ~85% of the dataset; the LLM acts only as a structured code-writer (PAL fallback) or last-resort CoT reasoner — raising the no-LLM correct-answer floor from **275 to 401 (+46%, zero regression)** and finishing in the **top 16 of all teams** in the EXACT 2026 competition.

---

## Medium version (final, ~5 bullets)

**Neuro-Symbolic Physics Question-Answering System — EXACT 2026 XAI Challenge**
*IEEE IJCNN / WCCI 2026, URA Research Group @ HCMUT* — **Team Leader & Lead Engineer, Track 2** · **Top 16 finish**

- **[Problem]** Explainable physics QA under hard constraints: open-source ≤8B LLM only, 60s/query limit, full interpretability required — standard LLM-first pipelines fail here because a 7B model hallucinates arithmetic and risks timeout on complex chains. Analyzed a **1,352-problem** dataset into **8 question families** to size the gap precisely.
- **[Solution]** Designed a neuro-symbolic pipeline that treats LLM as fallback, not backbone: rule-based classifier → hybrid keyword/FAISS **formula RAG** (20 → **53 formulas, 5 domains**, ~35% → ~**85% estimated coverage**) → SymPy/vector symbolic solvers → **PAL (Program-Aided LM) fallback** where the LLM writes sandboxed Python rather than doing arithmetic itself.
- **[Value]** Raised the deterministic no-LLM solver from **275 → 401 correct answers (+46%) with zero regression**, and confirmed arithmetic-heavy problems lift from **59% → 85%** with PAL. Team finished **top 16** in the EXACT 2026 competition (IEEE IJCNN/WCCI 2026).
- **[Value]** Reduced false-confidence errors in the vector solver (multi-charge Coulomb/E-field) from **79 → 25 (−68%)** through root-cause diagnosis of geometry-mapping and sign-selection bugs, each gated by a before/after eval to avoid overfitting.
- **[Strategy]** Selected **Qwen2.5-7B-Instruct** (rejecting DeepSeek-R1-8B, whose always-on reasoning chain risked the 60s limit and starved structured parsing), then deployed a spec-compliant `POST /predict` + proxied `/v1/models` model-verification endpoint so the committee could cryptographically confirm the ≤8B rule was met.

---

## Long version (portfolio / LinkedIn / 2-page CV, 8–12 bullets)

**Neuro-Symbolic Physics Question-Answering System — EXACT 2026 XAI Challenge**
*IEEE IJCNN / WCCI 2026 (Maastricht), URA Research Group @ HCMUT* — **Team Leader & Lead Engineer, Track 2 (Physics QA)** · **Top 16 finish**

- **[Problem — Analyzed]** Confronted a 1,352-problem explainable physics QA dataset with zero prior art for the task format, under hard constraints (open-source ≤8B LLM, 60s/query, full reasoning trace required). Classified the full dataset into **8 prefix-based families** (Coulomb-force, AC-RLC, EM-energy, capacitors, induction, measurement-error, point-field, Yes/No resonance), characterized answer types (numeric, vector, qualitative, multi-answer, Yes/No), and mapped per-group distribution — making the problem tractable rather than monolithic.
- **[Problem — Gap-Sized]** Ran a coverage audit showing the initial formula store (20 formulas, 2 domains) reached only **~35%** of the dataset. Specified and built a **53-formula, 5-domain** knowledge base (circuits, electrostatics, AC, electromagnetism, measurement) with documented sources (textbooks / dataset-derived / generated) for the competition's Data Disclosure requirement — lifting estimated coverage to **~85%**.
- **[Solution — Architecture]** Designed the end-to-end neuro-symbolic pipeline on the principle that "LLM is fallback, not backbone": rule-based classifier → hybrid **keyword + FAISS** Formula RAG → SymPy symbolic dispatch + custom **vector solver** (multi-charge Coulomb/E-field geometry, strategies A–F) → specialized solvers (resonance, error-propagation, parallel-circuit, multi-formula dependency chaining) → **PAL fallback** (LLM writes Python; hardened deny-listed sandbox executes it; self-repair retry on error). Every stage prioritizes deterministic correctness; LLM handles only what symbols cannot.
- **[Value — Headline]** Raised the deterministic no-LLM solver from **275 → 401 correct answers (+46%), zero regression** via root-cause debugging of general, non-sample-specific bugs — physical-magnitude sign selection, charge-to-vertex geometry mapping, prose ("phrasal") value extraction (~446 problem cases), Unicode minus/notation normalization, retrieval solvability re-ranking, and classifier mis-routing. Each fix measured before/after; regressions blocked merges.
- **[Value — PAL]** Validated the PAL fallback empirically: a vector-aware prompt + error-driven self-repair lifted arithmetic-heavy problems from **59% → 85%** (measured); a hard subset moved **24% → 40%**. The LLM never does arithmetic — it writes code, eliminating the hallucination mode while preserving interpretability (the generated code is the explanation).
- **[Value — Vector Solver]** Reduced false-confidence Coulomb/E-field errors from **79 → 25 (−68%)** by diagnosing and fixing systematic geometry-mapping and sign-selection bugs across all six vector strategies, not just the failing examples — a generalization-first debugging discipline.
- **[Strategy — Model Selection]** Evaluated and **rejected DeepSeek-R1-8B** despite its strong benchmark scores: always-on reasoning chain → token-budget starvation on structured JSON parse + >60s/query risk on complex problems. Selected **Qwen2.5-7B-Instruct** as the backbone (verified on the `/v1/models` endpoint); deployed on cloud GPU (RunPod) using vLLM FP16 for serving, llama.cpp Q4_K_M GGUF for local dev, with a config-only backend switch and a documented restart/failover runbook.
- **[Strategy — Spec & Verifiability]** Delivered a fully spec-compliant service: single `POST /predict` endpoint (type-routed, JSON-list response, ASCII units, structured `reasoning` object, graceful non-crashing fallback) plus a proxied `GET /v1/models` so the competition committee could independently verify the ≤8B open-source rule — a design choice that treats auditability as a first-class requirement, not an afterthought.
- **[Result]** Team finished **top 16** in EXACT 2026 (IEEE IJCNN/WCCI 2026), a competition requiring explainability, correctness, and live-graded API compliance under real-time constraints.

---

## Key metrics

| Metric | Value |
|--------|-------|
| Dataset size | 1,352 physics problems, 8 families |
| Formula knowledge base | 20 → **53 formulas**, 2 → **5 domains** |
| Coverage (formula, estimated) | ~35% → **~85%** (formula-coverage estimate, not solve-accuracy) |
| Deterministic no-LLM floor | **275 → 401 correct (+46%), 0 regression** |
| False-confidence errors (vector) | 79 → **25 (−68%)** |
| PAL on arithmetic-heavy problems | 59% → **85%** (measured); hard subset 24% → **40%** |
| Competition result | **Top 16**, EXACT 2026 (IEEE IJCNN/WCCI 2026) |
| Model | Qwen2.5-7B-Instruct (FP16 vLLM / Q4_K_M dev) — ≤8B compliant |
| Test suite | 99 tests passing |

---

## Tech stack / skills demonstrated

`Python` · `SymPy` (symbolic computation) · `FAISS` + `sentence-transformers` (hybrid RAG) · `vLLM` / `llama.cpp` (LLM serving, OpenAI-compatible) · `FastAPI` · **Program-Aided LM (PAL)** + sandboxed code execution · **neuro-symbolic reasoning** · evaluation methodology (before/after, regression gating, root-cause analysis) · cloud GPU deployment (RunPod) · prompt engineering · technical leadership.

---

## Notes on accuracy

- **Top 16** — confirmed as official by the user (this session). Safe to use.
- **Coverage (~35%→~85%)** — formula-coverage estimate from the gap analysis (`docs/docs_vytriet/track2_reference.md §4`), NOT measured solve-accuracy. Keep "estimated" qualifier.
- **Formula KB (53 / 5 domains)** — verified against `data/rag/physics_formulas.json`.
- **Deterministic floor (275→401)** — measured result against the full dataset, no-LLM mode. Distinct from coverage; both are real metrics.
- **PAL numbers (59%→85%, 24%→40%)** — measured on the respective subsets noted, not the full dataset.
- **Data split (944/200/208)** — verified against `data/physics/physics_{train,dev,test}.csv`.
- **DeepSeek-R1-8B rejected** — confirmed by work history (trialed, rejected for 60s latency risk and structured-parse issues). Safe to use as an engineering-judgment signal.
