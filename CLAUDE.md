# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EXACT 2026 competition entry — an explainable QA system for educational and physics problems, submitted to IEEE IJCNN 2026 (URA Research Group, HCMUT Vietnam). The system must use only **open-source LLMs ≤8B parameters** (LLaMA, Mistral, Qwen, Phi family) — calling closed-source APIs (OpenAI, Anthropic, Gemini, etc.) is a **competition rules violation**.

Competition timeline: Registration Apr 10–May 10, active competition May 5–30, final round Jun 15, paper due Jun 30–Jul 15 2026.

## Setup

```bash
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn z3-solver sympy transformers torch peft bitsandbytes \
    trl sentence-transformers faiss-cpu langchain pytest python-dotenv pyyaml
```

Copy `.env.example` to `.env` and set `LLM_MODEL_NAME`, `LLM_MODEL_PATH`, `API_HOST`, `API_PORT`.

## Running

```bash
# Start API server
uvicorn exact2026.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_type1_pipeline.py -v

# Run tests matching a keyword
pytest tests/ -k "type1" -v
```

## Architecture

Two independent processing pipelines selected by a **Type Router** at the API entry point:

**Type 1 — Logic/Educational (464 records, 913 questions)**
```
Request → NL→FOL Parser (LLM) → Z3 Solver (deterministic) → Explainer Agent (LLM) → Response
```
Queries are university regulation / FOL reasoning questions. Z3 provides deterministic correctness; LLM only handles NL↔FOL translation and explanation generation.

**Type 2 — Physics (5,520 records)**
```
Request → Physics Parser (LLM) → SymPy Solver (symbolic math) → CoT Builder (LLM) → Response
```
Covers circuits and electrostatics. SymPy handles numerical/symbolic computation; LLM extracts variables and narrates the solution.

**Fallback strategy**: if Z3/SymPy fails, fall back to LLM-only generation. Log the failure and include a lower confidence score.

## Planned Project Structure

```
exact2026/
├── api/           # FastAPI app, request/response schemas
├── pipeline/
│   ├── type1/     # FOL parsing, Z3 integration, explainer
│   └── type2/     # Physics parsing, SymPy integration, CoT builder
├── llm/           # Model loading, inference wrapper
├── data/          # Dataset loaders, preprocessing
├── configs/       # config.yaml, prompt templates
tests/
configs/
```

## API Response Schema

The competition API expects JSON with these fields:

```python
{
    "answer": str,        # required
    "explanation": str,   # required
    # optional extended fields:
    "fol": str,           # first-order logic formula (Type 1)
    "cot": str,           # chain-of-thought steps
    "premises": list,     # supporting premises used
    "confidence": float,  # 0.0–1.0
}
```

**Never include an `idx` field** — it is stripped and will cause evaluation errors.

## Hard Rules

- **No closed-source LLM API calls.** All inference must use locally-loaded open-source models ≤8B params.
- Always parse LLM JSON output with `json.loads()`, never `eval()`.
- Wrap every LLM call and every Z3/SymPy call in `try/except`; surface failures as structured error responses rather than exceptions.
- `answer` and `explanation` are always required in every response, even on fallback paths.
- Evaluation criteria weight: P1 Correctness > P2 Explanation Quality > P3 Reasoning Depth. Prioritize deterministic solver correctness (Z3/SymPy) over fluency.

## Model Download (first-time)

```bash
# Recommended: Qwen2.5-7B-Instruct (best instruction following)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir models/qwen2.5-7b

# Alternative: LLaMA 3.1 8B (requires Meta access approval)
# Alternative: Phi-3 Mini 3.8B (faster, lower VRAM)
```

Set `LLM_MODEL_PATH` in `.env` to point to the downloaded directory.
