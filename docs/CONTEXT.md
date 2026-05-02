# EXACT 2026 — Project Context

## Competition Overview

**Full name:** The 2nd International XAI Challenge for Transparent Educational Question-Answering  
**Host:** URA Research Group, Ho Chi Minh City University of Technology (HCMUT), Vietnam  
**Affiliated with:** IEEE IJCNN 2026 (WCCI 2026, Maastricht)  
**Website:** https://ura.hcmut.edu.vn/exact  
**Contact:** ura.hcmut@gmail.com

## Goal

Build an **educational QA system** that:
1. Produces **correct answers** to educational queries
2. Generates **natural language explanations** justifying each answer
3. Optionally provides structured reasoning evidence: FOL derivations, CoT steps, premise lists, confidence scores

The challenge promotes **Explainable AI (XAI)** — systems must not only be accurate but also transparent and verifiable.

## Hard Constraints

- **Only open-source LLMs with ≤ 8 billion parameters** are allowed (e.g. LLaMA, Mistral, Qwen, Phi)
- **Closed-source models are strictly prohibited**: GPT, Claude, Gemini, or any commercial API
- All external datasets used for fine-tuning must be fully disclosed
- Submissions that violate these rules are disqualified

## Task Description

### Dataset Type 1 — Logic-Based Educational Queries
- **Size:** 464 records, 913 questions
- **Domain:** University regulations (grading policies, enrollment rules, scholarship criteria)
- **Question types:** Multiple Choice (MCQ), Yes/No/Uncertain, Open-ended
- **Input at inference:** `question` + `premises-NL` (natural language premises)
- **Training data also includes:** `premises-FOL`, `answers`, `explanation`
- **Key challenge:** Multi-step logical reasoning over regulation rules

**Sample record:**
```json
{
  "premises-NL": [
    "If a curriculum is well-structured and has exercises, it enhances student engagement.",
    "If a curriculum enhances student engagement and provides access to advanced resources, it enhances critical thinking.",
    "The faculty prioritizes pedagogical training and curriculum development.",
    "The curriculum has practical exercises.",
    "The curriculum provides access to advanced resources."
  ],
  "premises-FOL": [
    "ForAll(c, (well_structured(c) ∧ has_exercises(c)) → enhances_engagement(c))",
    "ForAll(c, (enhances_engagement(c) ∧ advanced_resources(c)) → enhances_critical_thinking(c))"
  ],
  "questions": [
    "Based on the premises, what can we conclude about the curriculum?\nA. It enhances student engagement but not critical thinking\nB. It enhances critical thinking\nC. It needs more resources\nD. It is well-structured but lacks exercises"
  ],
  "answers": ["B"],
  "explanation": [
    "Faculty priorities satisfy premise 3, making the curriculum well-structured. Exercises and premise 1 lead to enhanced engagement, and with advanced resources, premise 2 confirms enhanced critical thinking."
  ]
}
```

### Dataset Type 2 — Physics Problems
- **Size:** 5,520 problems
- **Domain:** Electric circuits and electrostatics (resistance, voltage, current, power, capacitance, electric fields, energy)
- **Question types:** Numerical computation, multi-step
- **Input at inference:** `question` only (no premises given)
- **Training data also includes:** `cot` (chain-of-thought steps), `answer`, `unit`
- **Key challenge:** Requires physics domain knowledge and step-by-step numerical reasoning

**Sample record:**
```json
{
  "id": "TD401",
  "question": "Calculate the energy stored in capacitor C when C = 100 μF and U = 30 V.",
  "cot": "Step 1: Identify given values: C = 100 μF, U = 30 V.\nStep 2: Formula: E = 0.5 * C * U^2.\nStep 3: Convert: C = 1e-4 F.\nStep 4: E = 0.5 × 1e-4 × 900 = 0.045 J.",
  "answer": "45",
  "unit": "mJ"
}
```

## API Submission Format

Each team exposes an **HTTP API endpoint**. For every query, the endpoint must return:

```json
{
  "answer": "B",
  "explanation": "The voltage across R2 is calculated using Ohm's law...",

  "fol": "∀x (Resistor(x) → HasVoltage(x, V))",
  "cot": [
    "Step 1: Identify the circuit topology...",
    "Step 2: Apply Kirchhoff's voltage law...",
    "Step 3: Solve for the unknown voltage..."
  ],
  "premises": [
    "Ohm's law: V = IR",
    "KVL: sum of voltages in a loop = 0"
  ],
  "confidence": 0.92
}
```

| Field | Required | Notes |
|---|---|---|
| `answer` | ✅ Mandatory | Final answer string |
| `explanation` | ✅ Mandatory | Natural language justification |
| `fol` | Optional | First-Order Logic derivation |
| `cot` | Optional | Chain-of-Thought steps as list |
| `premises` | Optional | Supporting rules/laws used |
| `confidence` | Optional | Float 0–1 |

Optional fields improve **P3 (Reasoning Depth)** scores and are strongly encouraged.

## Evaluation Criteria

| Criterion | Description | Priority |
|---|---|---|
| **P1: Correctness** | Accurate final answer | Highest |
| **P2: Explanation Quality** | Clear, coherent, verifiable NL explanation | High |
| **P3: Reasoning Depth** | FOL, CoT, premises, structured proofs | Medium |

**Evaluation process:**
- **Phase 1 & 2:** Automated scoring against ground-truth + committee review of explanation quality
- **Final Round (Top 10):** Live demo on unseen queries; chairs assess answer, explanation, reasoning depth in real time
- **Final score:** Weighted combination of P1 + P2 + P3 (weights announced at kick-off)

## Timeline

| Phase | Date |
|---|---|
| Team Registration | Apr 10 – May 10, 2026 |
| Kick-off & Dataset Release | May 4, 2026 |
| Main Competition (submit API) | May 5 – May 30, 2026 |
| Phase 1 Evaluation Results | Jun 1–2, 2026 |
| Model Refinement Window | Jun 3–4, 2026 |
| Phase 2 Evaluation Results | Jun 5–7, 2026 |
| Top 10 Announcement | Jun 10, 2026 |
| Public Test Day (live demo) | Jun 15, 2026 |
| Paper Submission (Top 10) | Jun 30 – Jul 15, 2026 |
| Awards at CSoNet 2026 | Nov 16–18, 2026 |

## Recommended System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Endpoint                         │
│                     (FastAPI / Flask)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │    Query Classifier  │
              │  (Type 1 or Type 2) │
              └────┬────────────┬───┘
                   │            │
       ┌───────────▼──┐    ┌────▼──────────────┐
       │  Logic Track  │    │  Physics Track     │
       │  (Type 1)     │    │  (Type 2)          │
       │               │    │                    │
       │ 1. NL→FOL     │    │ 1. Formula RAG     │
       │ 2. Z3 Solver  │    │ 2. CoT Reasoner    │
       │ 3. NL Explain │    │ 3. Numerical Calc  │
       └───────┬───────┘    └────────┬───────────┘
               │                     │
               └──────────┬──────────┘
                          │
               ┌──────────▼──────────┐
               │   Response Builder   │
               │  answer + explanation│
               │  + fol/cot/premises  │
               └─────────────────────┘
```

## Suggested Tech Stack

| Component | Options |
|---|---|
| **Base LLM** | LLaMA 3.1 8B Instruct, Qwen2.5 7B Instruct, Mistral 7B Instruct, Phi-3 Mini |
| **Fine-tuning** | LoRA / QLoRA via HuggingFace PEFT |
| **Symbolic engine** | Z3 Solver (`pip install z3-solver`) |
| **Orchestration** | LangChain, LlamaIndex |
| **Retrieval** | FAISS, ChromaDB |
| **API server** | FastAPI + Uvicorn |
| **Containerization** | Docker |

## Key References

- EXACT 2025 findings paper: https://ceur-ws.org/Vol-4152/paper98.pdf
- Z3 Solver (Python): https://github.com/Z3Prover/z3
- LLaMA 3.1 8B: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
- Qwen2.5 7B: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- LangChain: https://python.langchain.com
- FastAPI: https://fastapi.tiangolo.com

## Notes for the Agent

- The system must handle **two distinct input formats** depending on dataset type — always detect which type a query belongs to before processing
- For Type 1, the `premises-NL` field is provided in the request and should be used as context
- For Type 2, no context is provided — the model must rely on internal physics knowledge or a retrieval system
- `answer` and `explanation` are **always required** in every response — never return a response without them
- Richer optional fields (`fol`, `cot`, `premises`) directly improve the final score; include them whenever feasible
- All LLM calls must route through a **local or self-hosted** model — no external commercial API calls
