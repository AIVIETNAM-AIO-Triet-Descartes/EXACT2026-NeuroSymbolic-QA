# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EXACT 2026 competition entry — an explainable QA system for educational and physics problems, submitted to IEEE IJCNN 2026 (URA Research Group, HCMUT Vietnam). The system must use only **open-source LLMs ≤8B parameters** (LLaMA, Mistral, Qwen, Phi family) — calling closed-source APIs (OpenAI, Anthropic, Gemini, etc.) is a **competition rules violation**.

Competition timeline: submission **deadline extended to June 12, 2026** (Phase 1 eval Jun 1–2, Phase 2 Jun 5–7, Top 10 Jun 10, Public Test Day Jun 15). Live API round = **50 queries (25 Type 1 + 25 Type 2)**, 60s/query, no retry.

> ⚠️ **Official spec vs codebase:** the API layer + several assumptions are out of date vs the committee docs. See **`docs/official_spec_gaps.md`** (gap analysis from `docs/context/` PDFs) before touching `api/`. Key: endpoint is `POST /predict` (single, both types, route by `type` field), response is a **JSON list** of `{query_id, answer, unit, explanation, premises_used, reasoning}` — NOT the schema in the "API Response Schema" section below (that section is the OLD internal design).

## LLM Backend — vLLM (important)

Inference does **not** load model weights in-process. Instead the code calls a **vLLM OpenAI-compatible HTTP server** running locally, via the `openai` Python client.

Reasoning: the competition committee can inspect the `GET /v1/models` endpoint to confirm which model is loaded. vLLM loads real HF weights, so `model_id` comes from the model's `config.json` and is verifiable. (A previous `llama-cpp-python` GGUF setup returned a self-assigned, non-verifiable model name and has been removed.)

- All LLM access goes through `llm/llm_reasoner.py` (`LLMReasoner` + `create_reasoner()` factory). `llm/__init__.py` exposes `get_shared_reasoner()` — a config-driven singleton.
- vLLM is Linux-only; on this Windows machine it must run under **WSL2** with the CUDA Toolkit installed. See `docs/handoff.md` §4 (P1) for the exact setup steps.
- The pipeline runs **without** the LLM (SymPy + vector solver only); `--use-llm` enables LLM augmentation/fallback/explanation.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Key deps: `fastapi uvicorn z3-solver sympy openai sentence-transformers faiss-cpu transformers torch langchain pyyaml loguru`. (`openai` is the LLM transport to the vLLM server — NOT a closed-source API call.) Copy `.env.example` to `.env` if needed.

## Running

```bash
# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Type 2 physics demo + evaluation (primary dev loop)
.venv\Scripts\python scripts/demo_type2.py --limit 100            # SymPy + vector solver only
.venv\Scripts\python scripts/demo_type2.py --limit 100 --use-llm  # + LLM augment/fallback/explain

# Batch runner over a dataset → predictions JSON
python scripts/run_pipeline.py --input data.json --output output/predictions.json [--no-llm]

# Rebuild FAISS formula index after editing data/rag/physics_formulas.json
python scripts/build_faiss_index.py

# Tests
.venv\Scripts\python -m pytest tests/ -v
.venv\Scripts\python -m pytest tests/test_type2.py -v
```

vLLM server must be running (in WSL2) before any `--use-llm` run; verify with `curl http://localhost:8000/v1/models`.

## Architecture

Two processing pipelines selected by a **Type Router** (`api/router.py`). Nodes share a single `PipelineState` TypedDict (`pipeline/state.py`) and run **sequentially** (LangGraph-style without the orchestration runtime). Every solver populates a unified `SolverResult` before handing off to the explainer.

**Type 1 — Logic/Educational** (`Logic_Based_Educational_Queries.json`)
```
Request → NL→FOL Parser (LLM) → Z3 Solver (deterministic) → Explainer (LLM) → Response
```
Z3 provides deterministic correctness; LLM only handles NL↔FOL translation and explanation. **Status: not wired.** `pipeline/type1/{nl_to_fol,z3_solver,explainer}.py` are empty stubs; `api/main.py` returns a mock answer for Type 1. The Z3 codegen/refinement logic currently lives in `llm/llm_reasoner.py` (`generate_z3_code`, `refine_z3_code`, `_clean_code`) and `scripts/run_pipeline.py` imports the type1 modules defensively.

**Type 2 — Physics** (`Physics_Problems_Text_Only.csv`, ~1352 problems, 8 prefixes — see `docs/track2_reference.md`) — **fully implemented**:
```
Request → PhysicsClassifier → PhysicsParser → FormulaRAG (FAISS) → SymPy Solver
        → vector_solver fallback → Self-Verifier → CoT Builder → Explainer → Response
```
- `physics_parser.py` — variable/find extraction (regex in `demo_type2.py`, LLM augment via `--use-llm`).
- `formula_rag.py` — hybrid retrieval: Layer 1 keyword/exact match → Layer 2 FAISS semantic search over `data/rag/physics_formulas.json` (index in `data/formula_index/`).
- `sympy_solver.py` — symbolic dispatch by `PhysicsQuestionType`; ThreadPoolExecutor timeout (Windows-safe, no SIGALRM). Wires `vector_solver` as fallback.
- `vector_solver.py` — multi-charge Coulomb / E-field problems the scalar solver can't handle. **6 strategies A–F**: A force+angle (parallelogram), B coordinate geometry, C centroid of equilateral triangle, D perpendicular bisector, E inverse-angle, F E-field at point. (`solve_vector_problem()` is the entry; module docstring still says "three strategies" — stale, it's six.)
- `type2_validation.py` — Self-Verifier; downgrades confidence on failed validation.
- `cot_builder.py` / `explainer.py` — narrate steps and generate NL explanation.

**Type Router logic** (`api/router.py`): ⚠️ **OBSOLETE for the official API.** The committee sends an explicit `type` field (`"type1"`/`"type2"`) — route on that, not keywords. The keyword classifier below may stay only as an internal fallback. (See `docs/official_spec_gaps.md`.)
1. ~~`premises` list non-empty → **Type 1**~~
2. ~~physics keywords in question → **Type 2**~~
3. ~~default → **Type 1**~~

**Fallback strategy**: if Z3/SymPy/vector solver fails, fall back to LLM CoT (`solve_physics_cot` / `solve_with_cot`). Log the failure and lower the confidence score.

## Project Structure

```
api/
├── main.py            # FastAPI /query (+ sequential Type 2 pipeline) and /health
├── schemas.py         # QueryRequest / QueryResponse Pydantic models
├── router.py          # Type 1/2 classifier
├── response_builder.py
└── logger.py          # JSON log formatter
pipeline/
├── state.py           # PipelineState + SolverResult TypedDicts (shared contract)
├── type1/
│   ├── type1_classifier.py  # QuestionClassifier / QuestionType (implemented)
│   ├── nl_to_fol.py         # EMPTY stub
│   ├── z3_solver.py         # EMPTY stub
│   └── explainer.py         # EMPTY stub
└── type2/                   # all implemented
    ├── type2_classifier.py  # PhysicsClassifier / PhysicsQuestionType
    ├── physics_parser.py
    ├── formula_rag.py       # keyword + FAISS hybrid retrieval
    ├── sympy_solver.py      # symbolic dispatch + timeout
    ├── vector_solver.py     # Coulomb/E-field strategies A–F
    ├── type2_validation.py  # self-verifier
    ├── cot_builder.py
    └── explainer.py
llm/
├── __init__.py        # get_shared_reasoner() singleton + config loader
├── llm_reasoner.py    # LLMReasoner — OpenAI client → vLLM server
├── prompt_templates.py# all prompts incl. PHYSICS_COT_PROMPT
└── loader.py
scripts/
├── demo_type2.py      # primary Type 2 demo + accuracy eval (regex extraction, LLM hooks)
├── run_pipeline.py    # batch runner over a dataset → predictions JSON
└── build_faiss_index.py
configs/config.yaml    # vLLM endpoint + pipeline/api/logging config
data/
├── train/             # Physics_Problems_Text_Only.csv, Logic_Based_Educational_Queries.json
├── rag/               # physics_formulas.json (formula DB)
├── formula_index/     # FAISS index.faiss + metadata.pkl
└── eval/              # (empty)
docs/
├── handoff.md         # session handoff — read FIRST when resuming
├── TODO.md            # worklist + weakness tracker (gộp)
├── SYSTEM.md          # full architecture + competition spec (gộp CONTEXT)
├── track2_reference.md # data analysis + formula format + gaps + impl plan (gộp 4 file)
├── proposals.md       # PAL code-gen fallback + formula_rag review (gộp)
├── run_demo_llm_local.md, exact2026_pipeline.mermaid
└── teammates/         # task-handoff cho teammate khác (handoff_teammate2, teammate2-log)
tests/                 # test_type2.py, test_pipeline.py substantive; type1 minimal
```

**Implementation status**: Type 2 physics pipeline complete and evaluable (demo ~78% on the vector-solver subset). Type 1 logic pipeline is scaffolded but not wired (empty solver stubs, mock API response). vLLM server not yet set up locally (needs WSL2 + CUDA Toolkit). See `docs/handoff.md` for the prioritized next steps (P1 vLLM setup → P2 LLM test → P3 expand formulas → P4 CHLT Yes/No solver → P5 DT routing → P6 commit).

## API Schema — OFFICIAL (Submission Guide §3–4)

**This is the binding contract. The current `api/` code does NOT match it yet — see `docs/official_spec_gaps.md`.**

Single endpoint `POST /predict` handles both types, routed by the input `type` field.

**Request** (one JSON object; every field always present, empty `""`/`[]` when N/A):
```python
{ "query_id": str, "type": "type1"|"type2", "query": str,
  "premises": list[str],   # Type 1 NL premises (0-indexed); [] for Type 2
  "options":  list[str] }  # MCQ choice set; [] for free-form / Type 2
```

**Response** — a JSON **LIST** (one object per query, even for one):
```python
[{
  "query_id": str,         # MUST echo input query_id
  "answer": str,           # Type 2: numeric value ONLY (unit separate). Type 1: chosen option / number / text
  "unit": str,             # ASCII only: "ohm","uF","nC","V/m","A","W","J"...  ""  for Type 1
  "explanation": str,      # required, non-empty (NOT scored this round)
  "premises_used": list[int],  # 0-based premise indices used (Type 1); [] for Type 2
  "reasoning": {"type": "fol"|"cot"|"proof", "steps": list[str]} | None  # optional (P3)
}]
```

- **`query_id` is mandatory** (echo input). The old ban on `idx` still holds — `idx` ≠ `query_id`.
- **There is NO `confidence` field in the official output.** Keep confidence/source INTERNAL only (for fallback selection), do not emit.
- Type 2 scoring = answer + unit BOTH correct (use ASCII units). Type 1 = answer 50% + `premises_used` 50%.

Confidence convention (INTERNAL, `pipeline/state.py`): 1.0 symbolic solver success · 0.6 RAG+LLM fallback · 0.5 LLM-only fallback · 0.4 SymPy succeeded but self-verification failed · 0.3 LLM generation error.

## Hard Rules

- **No closed-source LLM API calls.** All inference goes to the local vLLM server (open-source model ≤8B). The `openai` package is only the HTTP transport to that local server.
- Always parse LLM JSON output with `json.loads()`, never `eval()`.
- Wrap every LLM call and every Z3/SymPy/vector-solver call in `try/except`; surface failures as structured results, not exceptions.
- `answer` and `explanation` are always required in every response, even on fallback paths.
- Evaluation weight: P1 Correctness > P2 Explanation Quality > P3 Reasoning Depth. Prioritize deterministic solver correctness (Z3/SymPy) over fluency.

## Model Serving (first-time, in WSL2)

```bash
# Download HF safetensors (~14GB) — required by vLLM
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir ~/models/qwen2.5-7b

# Serve (OpenAI-compatible API on :8000)
vllm serve Qwen/Qwen2.5-7B-Instruct --model ~/models/qwen2.5-7b --port 8000 --host 0.0.0.0
```

`model_name` in `config.yaml` must match the served model. Alternatives ≤8B: LLaMA 3.1 8B (Meta access required), Phi-3 Mini 3.8B (lower VRAM). Full WSL2/CUDA setup in `docs/handoff.md` §4.

## Config Reference (`configs/config.yaml`)

The `llm` block is **profile-based** — `llm.active` selects a backend; `get_shared_reasoner()` (`llm/__init__.py`) merges `llm.profiles[active]` over the shared `llm` keys. Both backends (llama.cpp dev / vLLM prod) speak the same OpenAI `/v1` API, so switching is **config-only — no code change**. A flat `llm` block with no `profiles` still works (backward-compatible).

```yaml
llm:
  active: dev                 # dev (llama.cpp GGUF) | prod (vLLM FP16)
  api_key: "not-needed"       # shared across profiles
  temperature: 0.1
  max_tokens: 1024
  profiles:
    dev:                      # llama.cpp server, Q4_K_M GGUF, Windows-native
      api_base: "http://localhost:8000/v1"
      model_name: "Qwen/Qwen2.5-7B-Instruct"   # = llama-server --alias
    prod:                     # vLLM, FP16 safetensors, VPS Linux
      api_base: "http://localhost:8000/v1"      # → http://<vps-ip>:8000/v1
      model_name: "Qwen/Qwen2.5-7B-Instruct"   # must match real /v1/models id

pipeline:
  z3_timeout: 5
  sympy_timeout: 10
  retry_attempts: 2

api:
  host: "0.0.0.0"
  port: 8000

logging:
  level: "INFO"
  format: "json"
```
