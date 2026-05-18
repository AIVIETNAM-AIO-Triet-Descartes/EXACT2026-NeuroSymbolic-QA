# 🧠 NeuroSymbolic-QA: A Hybrid Neuro-Symbolic System for Explainable Logic-Based Question Answering

[![EXACT 2026](https://img.shields.io/badge/EXACT%202026-Logic%20QA-blue)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Submission to EXACT 2026** — 2nd International XAI Challenge for Transparent Educational Question-Answering  
> **Track:** Part 1 — Logic-Based Educational Queries

---

## Abstract

We present **NeuroSymbolic-QA**, a hybrid neuro-symbolic reasoning system that combines a lightweight Large Language Model (Qwen 2.5 7B Instruct, ≤8B parameters) with the Z3 Theorem Prover and a novel **Logic Tree** inference structure for answering logic-based educational questions. Our architecture decomposes the problem into four stages: (1) FOL normalization and question classification, (2) Logic Tree construction via DAG-based forward/backward chaining, (3) formal verification through Z3 entailment checking with LLM-assisted translation, and (4) natural language explanation generation via structured Chain-of-Thought prompting. The system achieves guaranteed logical correctness through symbolic verification while maintaining natural language explainability through the neural component, addressing the core challenge of transparent educational QA.

**Keywords:** Neuro-Symbolic AI, First-Order Logic, Z3 Theorem Prover, Explainable AI, Educational QA, Logic Tree, Chain-of-Thought

---

## Table of Contents

- [1. Introduction](#1-introduction)
- [2. System Architecture](#2-system-architecture)
- [3. Methodology](#3-methodology)
- [4. Installation & Setup](#4-installation--setup)
- [5. Usage](#5-usage)
- [6. Project Structure](#6-project-structure)
- [7. Evaluation](#7-evaluation)
- [8. Technical Details](#8-technical-details)
- [9. References](#9-references)

---

## 1. Introduction

### 1.1 Problem Statement

The EXACT 2026 challenge requires building an educational QA system that:
- Answers logic-based questions derived from First-Order Logic (FOL) premises
- Generates transparent, step-by-step explanations
- Uses only open-source LLMs with ≤8B parameters
- Responds within 60 seconds per query

### 1.2 Dataset Overview

| Property | Value |
|:---|:---|
| Total Samples | 411 |
| Total Questions | ~808 |
| Question Types | MCQ (346), Yes/No (416), Unknown (43), Open (3) |
| Premises per Sample | min=3, max=36, avg=10.9 |
| FOL Operators | ∀, ∃, →, ∧, ∨, ¬, ↔, ≥, ≤ |

### 1.3 Our Approach

We adopt a **hybrid neuro-symbolic** approach inspired by Logic-LM (Pan et al., 2023) and LINC (Olausson et al., 2023), with three key innovations:

1. **Logic Tree (DAG-based Inference):** A directed acyclic graph that models the deductive chain from premises to conclusions, supporting both forward and backward chaining with automated contraposition generation.

2. **Multi-Strategy Reasoning:** A tiered solving strategy that prioritizes Z3 formal verification (highest confidence), falls back to Logic Tree heuristics, and uses LLM Chain-of-Thought as a final safety net.

3. **Premise Tracking via Unsat Core:** Z3's unsatisfiable core extraction identifies the minimal set of premises required for each conclusion, directly optimizing the P3 (Reasoning Depth) evaluation metric.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        📥 INPUT                                 │
│           JSON: premises-NL, premises-FOL, questions            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              STAGE 1: PREPROCESSING                             │
│                                                                 │
│   FOL Normalizer          Question Classifier                   │
│   (Unicode → Unified)     (MCQ / Yes-No / Unknown)              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
┌───────────────────┐ ┌──────────┐ ┌──────────────────┐
│ STAGE 2:          │ │ STAGE 3: │ │ STAGE 3-alt:     │
│ Logic Tree (DAG)  │ │ Z3       │ │ LLM-Assisted Z3  │
│                   │ │ Solver   │ │ Code Generation   │
│ Forward Chaining  │ │ (Rule-   │ │ + Self-Refinement │
│ Backward Chaining │ │  Based)  │ │ (Logic-LM style)  │
│ Contraposition    │ │          │ │                    │
└────────┬──────────┘ └────┬─────┘ └────────┬───────────┘
         │                 │                 │
         └─────────┬───────┴─────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│              STAGE 4: LLM REASONING                             │
│                                                                 │
│   Explanation Generator    │    CoT Fallback Solver              │
│   (Post-Z3: translate      │    (When Z3 fails: direct          │
│    proof → NL)             │     LLM reasoning)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        📤 OUTPUT                                │
│         answer | explanation | idx (premises used)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Methodology

### 3.1 FOL Normalization

The dataset contains two distinct FOL notations:
- **Unicode style:** `∀x (WT(x) → O(x))`
- **Text style:** `ForAll(x, completed_courses(x) → eligible(x))`

Our `FOLNormalizer` detects the notation style and converts all expressions to a unified format, extracting predicates, bound variables, and named constants for downstream processing.

### 3.2 Logic Tree Construction

We model the logical structure as a **Directed Acyclic Graph (DAG)** where:
- **Leaf nodes** = atomic facts from premises
- **Internal nodes** = derived propositions
- **Edges** = inference rules (implications)

The tree supports:
- **Forward Chaining:** Derives all reachable conclusions from known facts (O(|R| × |F| × D))
- **Backward Chaining:** Goal-directed proof search (O(|R|^D) worst case)
- **Contraposition:** Automatically generates ¬B → ¬A from A → B
- **Negation Handling:** Blocks inference paths when ¬P(x) is asserted

### 3.3 Z3 Formal Verification

We use the Z3 SMT solver for **entailment checking via proof by contradiction:**

```
Given premises P and conclusion C:
    If P ∧ ¬C is UNSATISFIABLE → C is entailed (answer: "Yes")
    If P ∧ ¬C is SATISFIABLE   → C is not entailed (answer: "No")
    If UNKNOWN                  → Insufficient information
```

Two translation strategies:
1. **Rule-based:** Pattern matching for common FOL structures
2. **LLM-assisted:** Qwen 2.5 generates Z3 Python code with self-refinement loop

### 3.4 LLM Explanation Generation

Post-verification, the LLM generates natural language explanations by receiving:
- The verified correct answer
- The proof trace (which premises were used)
- A structured template enforcing premise references and logical step names

---

## 4. Installation & Setup

### 4.1 Prerequisites

- Python 3.10+
- CUDA-compatible GPU (recommended: 4GB+ VRAM for Qwen 2.5 7B)
- Qwen 2.5 7B Instruct GGUF model files

### 4.2 Installation

```bash
# Clone repository
git clone https://github.com/your-org/EXACT2026-NeuroSymbolic-QA.git
cd EXACT2026-NeuroSymbolic-QA

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4.3 Model Setup

Download the Qwen 2.5 7B Instruct GGUF model and place it in the project root:

```bash
# The model files should be:
# ./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
# ./qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf
```

---

## 5. Usage

### 5.1 Full Pipeline (Z3 + LLM)

```bash
# Run on full dataset with evaluation
python -m src.main \
    --input Logic_Based_Educational_Queries.json \
    --output output/predictions.json \
    --evaluate

# Run on first 10 samples for testing
python -m src.main \
    --input Logic_Based_Educational_Queries.json \
    --output output/test_predictions.json \
    --max-samples 10 \
    --evaluate \
    --log-level DEBUG
```

### 5.2 Symbolic-Only Mode (No LLM)

```bash
# Use only Z3 + Logic Tree (faster, no GPU required)
python -m src.main \
    --input Logic_Based_Educational_Queries.json \
    --output output/symbolic_only.json \
    --no-llm \
    --evaluate
```

### 5.3 LLM-Only Mode (No Z3)

```bash
# Use only LLM Chain-of-Thought (no Z3)
python -m src.main \
    --input Logic_Based_Educational_Queries.json \
    --output output/llm_only.json \
    --no-z3 \
    --evaluate
```

### 5.4 Custom GPU Configuration

```bash
# Limit GPU layers for low-VRAM GPUs
python -m src.main \
    --input Logic_Based_Educational_Queries.json \
    --output output/predictions.json \
    --gpu-layers 20 \
    --evaluate
```

### 5.5 CLI Options

| Flag | Description | Default |
|:---|:---|:---|
| `--input, -i` | Path to input JSON dataset | `Logic_Based_Educational_Queries.json` |
| `--output, -o` | Path to output predictions JSON | `output/predictions.json` |
| `--model, -m` | Path to GGUF model file | `./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` |
| `--max-samples, -n` | Max samples to process (None = all) | `None` |
| `--no-llm` | Disable LLM component | `False` |
| `--no-z3` | Disable Z3 solver | `False` |
| `--gpu-layers` | Number of GPU layers (-1 = all) | `-1` |
| `--evaluate` | Evaluate accuracy vs ground truth | `False` |
| `--log-level` | Logging verbosity | `INFO` |

---

## 6. Project Structure

```
EXACT2026-NeuroSymbolic-QA/
│
├── src/                                # Source code
│   ├── __init__.py
│   ├── main.py                         # Main pipeline & CLI entry point
│   │
│   ├── preprocessor/                   # Stage 1: Preprocessing
│   │   ├── fol_normalizer.py           # FOL notation normalization
│   │   └── question_classifier.py      # Question type classification
│   │
│   ├── reasoning/                      # Stage 2 & 3: Symbolic Reasoning
│   │   ├── logic_tree.py               # Logic Tree DAG construction
│   │   └── z3_solver.py                # Z3 translation & entailment
│   │
│   └── llm/                            # Stage 4: Neural Reasoning
│       ├── llm_reasoner.py             # Qwen 2.5 wrapper via llama-cpp
│       └── prompt_templates.py         # Structured prompt templates
│
├── docs/                               # Design documentation (skills)
│   ├── 00_pipeline_overview.md         # Architecture overview
│   ├── 01_data_analysis.md             # Dataset analysis
│   ├── 02_fol_normalizer.md            # FOL normalizer design
│   ├── 03_logic_tree.md                # Logic Tree algorithms
│   ├── 04_z3_solver.md                 # Z3 integration guide
│   ├── 05_llm_reasoning.md             # Prompt engineering
│   ├── 06_pipeline_implementation.md   # Implementation guide
│   ├── 07_evaluation_strategy.md       # Scoring optimization
│   └── 08_project_structure.md         # Project organization
│
├── tests/                              # Unit tests
├── output/                             # Pipeline outputs
├── logs/                               # Execution logs
│
├── Logic_Based_Educational_Queries.json # Input dataset
├── requirements.txt                    # Python dependencies
├── .gitignore                          # Git ignore rules
└── README.md                           # This file
```

---

## 7. Evaluation

### 7.1 Scoring Criteria (EXACT 2026)

| Criterion | Weight | Our Strategy |
|:---|:---|:---|
| **P1: Correctness** | High | Z3 formal verification ensures logical soundness |
| **P2: Explanation Quality** | Medium | Structured LLM prompts with premise references |
| **P3: Reasoning Depth** | Supplementary | Z3 unsat core / Logic Tree proof trace for `idx` |

### 7.2 Solving Strategy Priority

| Priority | Method | Confidence | Speed |
|:---|:---|:---|:---|
| 1st | LLM-Assisted Z3 | 0.9 | ~10-20s |
| 2nd | Logic Tree (Forward/Backward) | 0.7 | <1s |
| 3rd | LLM Chain-of-Thought | 0.5 | ~5-15s |
| Fallback | Default "Unknown" | 0.0 | instant |

### 7.3 Running Evaluation

```bash
python -m src.main \
    --input Logic_Based_Educational_Queries.json \
    --output output/predictions.json \
    --evaluate

# Output includes:
# - output/predictions.json   (formatted for submission)
# - output/evaluation.json    (accuracy metrics by method)
# - logs/pipeline_*.log       (detailed execution log)
```

---

## 8. Technical Details

### 8.1 FOL Operator Support

| Operator | Unicode | Text | Z3 Mapping |
|:---|:---|:---|:---|
| Universal Quantifier | `∀` | `ForAll` | `z3.ForAll([x], ...)` |
| Existential Quantifier | `∃` | `Exists` | `z3.Exists([x], ...)` |
| Implication | `→` | `->` | `z3.Implies(a, b)` |
| Conjunction | `∧` | `&` | `z3.And(a, b)` |
| Disjunction | `∨` | `\|` | `z3.Or(a, b)` |
| Negation | `¬` | `~` | `z3.Not(a)` |
| Biconditional | `↔` | `<->` | `a == b` |

### 8.2 Hardware Requirements

| Component | Minimum | Recommended |
|:---|:---|:---|
| GPU VRAM | 4 GB | 8 GB |
| RAM | 8 GB | 16 GB |
| Storage | 10 GB (model files) | 10 GB |
| GPU | NVIDIA GTX 1060 | NVIDIA RTX 3050+ |

### 8.3 Constraints & Limitations

- **Model size:** ≤8B parameters (Qwen 2.5 7B Instruct)
- **Response time:** <60 seconds per query
- **No closed-source APIs:** No GPT-4, Claude, or Gemini
- **FOL ambiguity:** Some premises have inconsistent FOL ↔ NL mappings

---

## 9. References

1. **Logic-LM:** Pan, A., et al. "Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning." *Findings of ACL 2023*.

2. **LINC:** Olausson, T., et al. "LINC: A Neurosymbolic Approach for Logical Reasoning by Combining Language Models with First-Order Logic Provers." *EMNLP 2023*.

3. **Tree-of-Thought:** Yao, S., et al. "Tree of Thoughts: Deliberate Problem Solving with Large Language Models." *NeurIPS 2023*.

4. **Chain-of-Thought:** Wei, J., et al. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." *NeurIPS 2022*.

5. **Z3 Theorem Prover:** de Moura, L. & Bjørner, N. "Z3: An Efficient SMT Solver." *TACAS 2008*.

6. **ProofWriter:** Tafjord, O., et al. "ProofWriter: Generating Implications, Proofs, and Abductive Statements over Natural Language." *Findings of ACL 2021*.

7. **SAFE:** Liu, H., et al. "Towards Rigorous Verification of LLM Reasoning via Step-Aware Formal Proofs." *ACL 2025*.

8. **Qwen 2.5:** Bai, J., et al. "Qwen Technical Report." *arXiv 2024*.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- EXACT 2026 Organizing Committee
- Microsoft Research for Z3 Theorem Prover
- Alibaba Cloud for Qwen 2.5 model
