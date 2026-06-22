# 🧠 NeuroSymbolic-QA — Explainable Educational & Physics Question Answering

[![EXACT 2026](https://img.shields.io/badge/EXACT%202026-IEEE%20IJCNN-blue)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Submission to EXACT 2026** — The 2nd International XAI Challenge for Transparent Educational Question-Answering (IEEE IJCNN / WCCI 2026, hosted by URA Research Group, HCMUT).
> **Team:** *Cây Nhà Lá Vườn* · **Team Lead:** Trịnh Vỹ Triết.

A hybrid **neuro-symbolic** QA system that answers both **logic-based educational** questions (Track 1) and **physics** problems (Track 2), with transparent step-by-step explanations, using only **open-source LLMs ≤ 8B parameters**.

> **Design philosophy:** *the LLM never does the arithmetic or the proof — it translates and explains; the math and logic are delegated to dedicated symbolic engines (Z3, SymPy) and verified code.*

---

## Table of Contents
- [1. Overview](#1-overview)
- [2. Architecture](#2-architecture)
- [3. Track 1 — Logic](#3-track-1--logic-based-educational-qa)
- [4. Track 2 — Physics](#4-track-2--physics-qa)
- [5. LLM Backend](#5-llm-backend-vllm--llamacpp)
- [6. API Contract](#6-api-contract-official-spec)
- [7. Installation](#7-installation)
- [8. Usage](#8-usage)
- [9. Project Structure](#9-project-structure)
- [10. Evaluation](#10-evaluation)
- [11. References](#11-references)

---

## 1. Overview

The system is evaluated as a **single live HTTP endpoint** (`POST /predict`) that handles both query types, routed internally by a `type` field. The committee sends **50 queries** (25 Type 1 + 25 Type 2) sequentially during a one-hour grading slot, **60 s/query, no retries**, and verifies the served model via `GET /v1/models`.

| | Track 1 — Logic | Track 2 — Physics |
|---|---|---|
| **Dataset** | 411 records / ~808 questions (FOL premises) | 1,352 problems, 8 families |
| **Engines** | Logic Tree (DAG) + Z3 + LLM CoT (consensus) | Classifier → Formula RAG → SymPy + vector/specialized solvers → PAL |
| **Scoring** | answer 50% + `premises_used` 50% | answer **and** unit 100% |
| **Answer** | chosen option / number / text | numeric value + ASCII unit |

**Compliance:** open-source LLM ≤ 8B (Qwen2.5-7B-Instruct), served via vLLM so the model id is verifiable; no closed-source API calls; symbolic tools / RAG / code execution do not count toward the parameter budget.

---

## 2. Architecture

```
                          POST /predict  { query_id, type, query, premises, options }
                                         │
                               route by  │  type
                    ┌────────────────────┴─────────────────────┐
                    ▼                                           ▼
        ════ TRACK 1 — LOGIC ════                  ════ TRACK 2 — PHYSICS ════
        Preprocess (FOL norm, classify)            PhysicsClassifier
                    │                                           │
        Logic Tree (DAG: fwd/bwd chaining,         Formula RAG (keyword + FAISS)
        negation, contraposition)                              │
                    │                              SymPy solver  ─┐
        Z3 Theorem Prover (entailment)             vector solver  ├─ symbolic
                    │                              resonance/error/circuit/chain ─┘
        LLM Chain-of-Thought                                     │
                    │                              PAL fallback (LLM writes Python →
        Consensus Hybridization                    sandbox exec + self-repair)
                    │                              → CoT fallback
                    └─────────────────────┬─────────────────────┘
                                          ▼
                          Explainer + Response Builder (ASCII units)
                                          ▼
            [ { query_id, answer, unit, explanation, premises_used, reasoning } ]
```

Nodes share a single `PipelineState` (`pipeline/state.py`) and run sequentially (LangGraph-style, no orchestration runtime). Every solver populates a unified `SolverResult` before the explainer. **All LLM calls go through one config-driven OpenAI-client singleton** (`llm/__init__.py::get_shared_reasoner`).

---

## 3. Track 1 — Logic-Based Educational QA

A **consensus hybrid** over three reasoners:

1. **Logic Tree (DAG)** — forward/backward chaining over FOL facts + rules, with negation handling, automatic contraposition, negation proof (`can_prove_negation` → real "No" answers) and missing-condition detection. Sub-millisecond, deterministic.
2. **Z3 Theorem Prover** — formal entailment via proof by contradiction (`P ∧ ¬C` UNSAT → entailed), with LLM-assisted Z3 code generation + self-refinement.
3. **LLM Chain-of-Thought** — Qwen2.5-7B for semantic reasoning + explanation when symbolic paths are insufficient.

**Consensus:** Logic Tree ∩ CoT agree → high confidence; on conflict, **trust the Logic Tree**; Z3 as fallback; ultimate fallback `"Unknown"`. `premises_used` (50% of the Track-1 score) is recovered from the Logic Tree / Z3 proof trace.

- **Offline batch** (full symbolic consensus over the dataset's `premises-FOL`): `scripts/run_track1.py`.
- **Live `/predict`**: runs LLM CoT over the NL premises (the live request carries no `premises-FOL`).

Full Track-1 guide: [`docs/readme_track1.md`](docs/readme_track1.md). Dataset label-fix report (33 mismatches found & corrected): [`docs/logic_dataset_analysis_report.md`](docs/logic_dataset_analysis_report.md).

---

## 4. Track 2 — Physics QA

A neuro-symbolic pipeline, **symbolic-first, LLM as last resort**:

```
PhysicsClassifier → regex/LLM parse (given, find, domain)
  → Formula RAG (keyword + FAISS over 53 formulas, 5 domains)
  → SymPy solver  ┐
    vector solver │  multi-charge Coulomb / E-field geometry (strategies A–F)
    resonance     │  CHLT Yes/No (f₀ = 1/2π√LC)
    error solver  │  THCB measurement error + propagation + multi-answer
    circuit solver│  parallel networks (per-branch I, R_p, P, KCL)
    multi-step    ┘  dependency-chain solving (e.g. RLC: ω→Z_L→Z_C→Z)
  → PAL fallback (LLM writes sympy/math code → hardened sandbox executes + 1 self-repair retry)
  → CoT fallback → Self-Verifier → CoT Builder → Explainer
```

**Highlights**
- **53-formula knowledge base** (5 domains: circuits, electrostatics, ac_circuits, electromagnetism, measurement), hybrid keyword + FAISS retrieval with solvability re-ranking. Sources documented in [`docs/formula_sources.md`](docs/formula_sources.md).
- **PAL (Program-Aided LM)** — the LLM emits Python; a deny-listed / whitelisted-import sandbox executes it, eliminating arithmetic hallucination. Vector-aware prompt + error-driven self-repair.
- **Deterministic floor:** with the LLM off, the symbolic pipeline alone answers **401 / 1,352** problems correctly (measured before/after every change with a strict zero-regression gate).
- Units emitted as **ASCII** (`ohm`, `uF`, `nC`, `V/m`, …) per the official matching rules.

Reference: [`docs/docs_vytriet/track2_reference.md`](docs/docs_vytriet/track2_reference.md).

---

## 5. LLM Backend (vLLM / llama.cpp)

Inference is **not** loaded in-process. The pipeline calls an **OpenAI-compatible HTTP server** via the `openai` client, so the served model is verifiable through `GET /v1/models`.

| Profile | Server | Use |
|---|---|---|
| `prod` | **vLLM** (FP16 safetensors) | production / grading (GPU ≥ 24 GB) |
| `dev`  | **llama.cpp** (Q4_K_M GGUF) | local dev / Colab (≈ 4.5 GB VRAM) |

Switching backend = flip **one line** `llm.active: dev → prod` in `configs/config.yaml` — no code change. Current served model: **Qwen/Qwen2.5-7B-Instruct** (DeepSeek-R1-8B was evaluated and rejected — always-on reasoning risked the 60 s budget).

Production serve (RunPod GPU): `bash scripts/serve.sh` — launches vLLM (internal `:8002`) + FastAPI (public `:8000`, which proxies `/v1/models`). See [`docs/deployment_plan.md`](docs/deployment_plan.md) and [`docs/restart_runbook.md`](docs/restart_runbook.md).

---

## 6. API Contract (official spec)

**Request** — one unified JSON object (every field always present):
```json
{ "query_id": "T2_0001", "type": "type2",
  "query": "Two resistors R1=4 ohm and R2=6 ohm in parallel across 12V. Find total current.",
  "premises": [], "options": [] }
```

**Response** — a JSON **list** (one object per query):
```json
[{ "query_id": "T2_0001", "answer": "5", "unit": "A",
   "explanation": "Two resistors in parallel give 2.4 ohm; 12V / 2.4 = 5 A.",
   "premises_used": [], "reasoning": { "type": "cot", "steps": ["1/Req=1/4+1/6", "Req=2.4 ohm", "I=12/2.4=5 A"] } }]
```

- `answer`/`explanation` always present; `unit` ASCII (`""` for Type 1); `premises_used` = 0-based indices (Type 1) / `[]` (Type 2); `reasoning` optional (`null` if absent).
- Endpoints: `POST /predict` (both types), `GET /v1/models` (proxied to vLLM), `GET /health`.
- Pipeline errors return a **valid 200 response** (never a 500) so a single failing query can't break the run.

---

## 7. Installation

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # dev only (pytest, etc.)
cp .env.example .env              # if needed
```

Key deps: `fastapi uvicorn z3-solver sympy openai sentence-transformers faiss-cpu transformers pyyaml loguru`. The `openai` package is only the HTTP transport to the local vLLM/llama.cpp server — **not** a closed-source API call.

---

## 8. Usage

```bash
# ── API server (both tracks) ─────────────────────────────────────
uvicorn api.main:app --host 0.0.0.0 --port 8000

# ── Track 2 — physics demo + accuracy eval (primary dev loop) ────
python scripts/demo_type2.py --limit 100            # symbolic only (no LLM)
python scripts/demo_type2.py --limit 100 --use-llm  # + LLM augment / PAL / explain
python scripts/demo_type2.py --ids LD010,CH001     # run specific problem ids

# ── Track 1 — logic batch runner (full symbolic consensus) ───────
python scripts/run_track1.py -n 5 --evaluate        # quick 5-sample check
python scripts/run_track1.py --no-llm --evaluate    # symbolic-only (no GPU)

# ── Evaluation / index ───────────────────────────────────────────
python scripts/evaluate.py --pred output/preds.json --truth data/physics/...csv
python scripts/build_faiss_index.py                 # rebuild formula index

# ── Tests (99 passing) ───────────────────────────────────────────
python -m pytest tests/ -v

# ── Production serve (RunPod / Linux GPU) ────────────────────────
bash scripts/serve.sh
```

`--use-llm` / live LLM paths require a reachable server at `llm.profiles[active].api_base`.

---

## 9. Project Structure

```
api/                    # FastAPI: /predict (unified), /v1/models proxy, /health
  ├── main.py           #   type-routed pipelines + graceful error handling
  ├── schemas.py        #   UnifiedRequest / UnifiedResponse / ReasoningBlock
  └── response_builder.py  #   official schema + ASCII-unit conversion
pipeline/
  ├── state.py          # shared PipelineState + SolverResult contract
  ├── type1/            # Logic: logic_tree, z3_solver, fol_normalizer, preprocessing, classifier
  └── type2/            # Physics: classifier, physics_parser, formula_rag, sympy_solver,
                        #          vector_solver (A–F), resonance/error/circuit solvers,
                        #          regex_extract, type2_validation, cot_builder, explainer
llm/                    # get_shared_reasoner() singleton (OpenAI client → vLLM/llama.cpp),
                        # llm_reasoner (CoT, Z3 codegen, PAL codegen + self-repair), prompts
scripts/                # run_track1.py · demo_type2.py · evaluate*.py · build_faiss_index.py · serve.sh
configs/config.yaml     # LLM profiles (dev/prod) + pipeline/api config
data/                   # train/ (datasets) · physics/ (stratified split) · rag/ (formulas) · formula_index/
evaluation/             # answer comparison + metrics harness
docs/                   # SYSTEM.md, official_spec_gaps.md, deployment_plan.md, restart_runbook.md,
                        # formula_sources.md, readme_track1.md, docs_vytriet/ (Track-2 working notes)
tests/                  # test_type2.py, test_api.py, test_pipeline.py, test_eval.py
Logic_Based_Educational_Queries.json   # Track-1 input dataset (run_track1 default)
run_track1_colab.ipynb  # Colab runner for Track 1
```

---

## 10. Evaluation

| | Method | Notes |
|---|---|---|
| Track 1 | `scripts/run_track1.py --evaluate` | accuracy by solver source (Z3 / Logic Tree / CoT) + `premises_used` |
| Track 2 | `scripts/demo_type2.py` → `scripts/evaluate.py` | accuracy by prefix / kind / source; SI-normalized comparison |

Engineering discipline: every solver/pipeline change is measured **before/after** on the full set and gated for **zero regression**; root causes are diagnosed rather than overfit to individual samples.

---

## 11. References

1. Pan et al. **Logic-LM** — Empowering LLMs with Symbolic Solvers. *Findings of ACL 2023.*
2. Olausson et al. **LINC** — Neurosymbolic Logical Reasoning with FOL Provers. *EMNLP 2023.*
3. Gao et al. **PAL** — Program-Aided Language Models. *ICML 2023.*
4. Wei et al. **Chain-of-Thought Prompting.** *NeurIPS 2022.*
5. de Moura & Bjørner. **Z3: An Efficient SMT Solver.** *TACAS 2008.*
6. Qwen Team. **Qwen2.5 Technical Report.** *2024.*

---

## License

MIT License — Copyright (c) 2026 Trịnh Vỹ Triết / Team *Cây Nhà Lá Vườn*. See [LICENSE](LICENSE).

**Acknowledgments:** EXACT 2026 Organizing Committee (URA Research Group, HCMUT) · Microsoft Research (Z3) · Alibaba Cloud (Qwen2.5).
