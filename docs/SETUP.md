# EXACT 2026 — Environment Setup Guide

You are an AI coding agent working on the **EXACT 2026** competition project.
Your job right now is to **set up the full development environment** from scratch.
Read this entire file before running any command.

---

## Project Overview (brief)

This project builds an **Explainable Educational QA API** for the EXACT 2026 competition.
The system handles two types of queries:

- **Type 1:** Logic-based questions over university regulation premises → uses Z3 Solver for symbolic reasoning
- **Type 2:** Physics problems (electric circuits / electrostatics) → uses SymPy for symbolic math

The API exposes a single `POST /query` endpoint and must always return `answer` + `explanation`.
Full context is in `CONTEXT.md`. Architecture details are in `APPROACHES.md`.

---

## Step 1 — Confirm Prerequisites

Before anything else, verify the following are available on this machine:

```bash
python --version        # Must be 3.10 or higher
pip --version
git --version
nvidia-smi              # Only needed if using GPU — check VRAM available
```

If Python < 3.10, stop and ask the user to upgrade before continuing.

---

## Step 2 — Create Project Structure

Create the following directory layout exactly as shown:

```
EXACT2026-NeuroSymbolic-QA/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── router.py            # Query type classifier (Type 1 / Type 2)
│   ├── schemas.py           # Pydantic request/response models
│   └── logger.py            # Structured JSON logging
├── pipeline/
│   ├── __init__.py
│   ├── type1/
│   │   ├── __init__.py
│   │   ├── nl_to_fol.py     # LLM-based NL → FOL translator
│   │   ├── z3_solver.py     # Z3 symbolic logic solver
│   │   └── explainer.py     # LLM explanation generator
│   └── type2/
│       ├── __init__.py
│       ├── physics_parser.py  # LLM-based value/formula extractor
│       ├── sympy_solver.py    # SymPy numerical solver
│       └── cot_builder.py     # Chain-of-Thought builder
├── llm/
│   ├── __init__.py
│   ├── loader.py            # Model loading (transformers / vLLM)
│   └── inference.py         # Unified LLM call wrapper with retry + fallback
├── data/
│   ├── train/               # Place official training data here after kick-off (May 4)
│   └── eval/                # Local evaluation samples
├── tests/
│   ├── test_type1.py
│   ├── test_type2.py
│   └── test_api.py
├── configs/
│   └── config.yaml          # Model paths, hyperparameters, timeouts
├── CONTEXT.md               # Competition context (do not edit)
├── APPROACHES.md            # Architecture decisions (do not edit)
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

Run this to create the skeleton:

```bash
mkdir -p EXACT2026-NeuroSymbolic-QA/{api,pipeline/type1,pipeline/type2,llm,data/train,data/eval,tests,configs}
cd EXACT2026-NeuroSymbolic-QA
touch api/{__init__,main,router,schemas,logger}.py
touch pipeline/{__init__}.py
touch pipeline/type1/{__init__,nl_to_fol,z3_solver,explainer}.py
touch pipeline/type2/{__init__,physics_parser,sympy_solver,cot_builder}.py
touch llm/{__init__,loader,inference}.py
touch tests/{test_type1,test_type2,test_api}.py
```

---

## Step 3 — Create Virtual Environment

```bash
cd EXACT2026-NeuroSymbolic-QA
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

Confirm activation:
```bash
which python   # Should point inside .venv/
```

---

## Step 4 — Install Dependencies

### 4a. Create `requirements.txt`

Write the following content to `requirements.txt`:

```
# API server
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.0.0

# Symbolic reasoning (Approach 1)
z3-solver>=4.13.0
sympy>=1.12

# LLM inference
transformers>=4.40.0
accelerate>=0.27.0
torch>=2.2.0

# Fine-tuning (Approach 2, optional during setup)
peft>=0.10.0
bitsandbytes>=0.43.0
trl>=0.8.0
datasets>=2.18.0

# Fast inference server (Approach 2)
# vllm>=0.4.0   # Uncomment only if on Linux with CUDA GPU

# Retrieval / RAG
sentence-transformers>=2.7.0
faiss-cpu>=1.8.0

# Orchestration
langchain>=0.2.0
langchain-community>=0.2.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0
httpx>=0.27.0
tenacity>=8.2.0
```

### 4b. Create `requirements-dev.txt`

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
black>=24.0.0
ruff>=0.4.0
```

### 4c. Install

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> **Note on `vllm`:** vLLM only works on Linux with a CUDA GPU. If on macOS or CPU-only, keep it commented out. Use `transformers` for inference instead.

> **Note on `bitsandbytes`:** On macOS, `bitsandbytes` may not install cleanly. If it fails, comment it out — it is only needed for QLoRA fine-tuning, not for inference.

---

## Step 5 — Create `.env.example` and `.env`

Write to `.env.example`:

```
# Model configuration
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
LLM_MODEL_PATH=./models/qwen2.5-7b
LLM_DEVICE=cuda          # or "cpu" or "mps" (Apple Silicon)
LLM_MAX_NEW_TOKENS=1024
LLM_TEMPERATURE=0.1

# API configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true           # Set to false in production

# Pipeline configuration
Z3_TIMEOUT_SECONDS=5
SYMPY_TIMEOUT_SECONDS=10
LLM_RETRY_ATTEMPTS=2

# Logging
LOG_LEVEL=INFO
```

Then copy to `.env`:
```bash
cp .env.example .env
```

Tell the user to edit `.env` and set `LLM_MODEL_PATH` to wherever they will store the model weights.

---

## Step 6 — Create `configs/config.yaml`

Write the following:

```yaml
llm:
  model_name: "Qwen/Qwen2.5-7B-Instruct"
  model_path: "./models/qwen2.5-7b"
  device: "cuda"           # cuda | cpu | mps
  max_new_tokens: 1024
  temperature: 0.1
  do_sample: false         # deterministic output preferred for competition

pipeline:
  z3_timeout: 5            # seconds before Z3 fallback
  sympy_timeout: 10
  retry_attempts: 2

api:
  host: "0.0.0.0"
  port: 8000

logging:
  level: "INFO"
  format: "json"
```

---

## Step 7 — Scaffold Core Files

### `api/schemas.py`

```python
from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    question: str
    premises: list[str] = []  # Empty list for Type 2 queries

class QueryResponse(BaseModel):
    answer: str
    explanation: str
    fol: Optional[str] = None
    cot: Optional[list[str]] = None
    premises: Optional[list[str]] = None
    confidence: Optional[float] = None
```

### `api/main.py`

```python
from fastapi import FastAPI, HTTPException
from api.schemas import QueryRequest, QueryResponse
from api.logger import get_logger

logger = get_logger(__name__)
app = FastAPI(title="EXACT 2026 QA API", version="0.1.0")

@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    try:
        # TODO: wire up pipeline
        raise NotImplementedError("Pipeline not yet implemented")
    except NotImplementedError:
        raise
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### `api/logger.py`

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_obj, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

### `api/router.py`

```python
from typing import Literal

PHYSICS_KEYWORDS = {
    "calculate", "resistance", "voltage", "current",
    "capacitor", "circuit", "power", "energy", "charge",
    "ohm", "ampere", "farad", "watt", "coulomb",
    "electric", "parallel", "series", "kirchhoff"
}

def classify_query(question: str, premises: list[str]) -> Literal["type1", "type2"]:
    """
    Classify query as Type 1 (logic) or Type 2 (physics).
    - If premises are provided → Type 1
    - If physics keywords in question → Type 2
    - Default fallback → Type 1
    """
    if premises:
        return "type1"
    words = set(question.lower().split())
    if PHYSICS_KEYWORDS & words:
        return "type2"
    return "type1"
```

---

## Step 8 — Create `.gitignore`

```
.venv/
__pycache__/
*.pyc
.env
models/
data/train/
data/eval/
checkpoints/
*.egg-info/
.pytest_cache/
.ruff_cache/
```

---

## Step 9 — Verify Installation

Run these checks one by one and confirm each passes:

```bash
# 1. Check FastAPI can be imported
python -c "import fastapi; print('FastAPI OK:', fastapi.__version__)"

# 2. Check Z3 works
python -c "from z3 import *; s = Solver(); s.add(Bool('x')); print('Z3 OK:', s.check())"

# 3. Check SymPy works
python -c "from sympy import symbols, solve; x = symbols('x'); print('SymPy OK:', solve(x**2 - 4, x))"

# 4. Check transformers can load
python -c "from transformers import AutoTokenizer; print('Transformers OK')"

# 5. Start the API server (Ctrl+C to stop)
uvicorn api.main:app --reload --port 8000
# Then in another terminal:
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## Step 10 — Download Model Weights (do this when ready)

The competition requires **open-source LLMs ≤ 8B parameters**. Recommended options:

```bash
# Option A: Qwen2.5 7B Instruct (recommended — strong reasoning)
pip install huggingface_hub
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir ./models/qwen2.5-7b

# Option B: LLaMA 3.1 8B Instruct (requires HuggingFace access approval)
huggingface-cli download meta-llama/Meta-Llama-3.1-8B-Instruct --local-dir ./models/llama3.1-8b

# Option C: Phi-3 Mini 4K Instruct (lighter, faster, less accurate)
huggingface-cli download microsoft/Phi-3-mini-4k-instruct --local-dir ./models/phi3-mini
```

> **IMPORTANT:** Never download or use GPT, Claude, Gemini, or any closed-source model.
> Using a closed-source model results in immediate disqualification from EXACT 2026.

After downloading, update `LLM_MODEL_PATH` in `.env` and `model_path` in `configs/config.yaml`.

---

## Step 11 — Run Tests

```bash
pytest tests/ -v
```

All tests will fail at this stage (stubs not implemented yet) — that is expected.
The goal is to confirm pytest runs without import errors.

---

## Completion Checklist

After finishing all steps above, confirm:

- [ ] Virtual environment active and all packages installed without errors
- [ ] Directory structure matches Step 2 exactly
- [ ] `.env` file exists and `LLM_MODEL_PATH` is set
- [ ] `uvicorn api.main:app` starts without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Z3, SymPy, transformers import without errors
- [ ] `.gitignore` excludes `models/`, `.env`, `data/train/`

---

## What Comes Next (do NOT implement yet)

After setup is confirmed, the next tasks will be:

1. Implement `llm/loader.py` — load model from `LLM_MODEL_PATH`
2. Implement `llm/inference.py` — unified call with retry logic
3. Implement `pipeline/type1/nl_to_fol.py` — NL → FOL prompt
4. Implement `pipeline/type1/z3_solver.py` — Z3 proof engine
5. Implement `pipeline/type2/physics_parser.py` — extract values/formulas
6. Implement `pipeline/type2/sympy_solver.py` — compute answer
7. Wire everything into `api/main.py`

Full architecture and prompt templates for each module are in `APPROACHES.md`.

---

## Hard Rules (never violate)

- **No closed-source LLM API calls** — no OpenAI, Anthropic, Google, Cohere, etc.
- **No `idx` field** anywhere in request/response — it is not in the official API schema
- **`answer` and `explanation` are always required** in every `/query` response
- **Always use `json.loads()`** to parse LLM JSON output — never `eval()`
- **Always wrap LLM calls in try/except** — the API must never crash on a bad LLM response
