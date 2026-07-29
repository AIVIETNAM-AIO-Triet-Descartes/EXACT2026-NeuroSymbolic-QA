# EXACT 2026 paper evaluation

[![Open BTC replay notebook in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AIVIETNAM-AIO-Triet-Descartes/EXACT2026-NeuroSymbolic-QA/blob/main/paper/EXACT2026_BTC_Test_Replay_T4_Colab.ipynb)

The canonical paper protocol replays the two organizer-supplied EXACT 2026
round logs:

- Round 1: 25 Type 1 + 25 Type 2;
- Round 2: 25 Type 1 + 25 Type 2;
- pooled replay: 50 Type 1 + 50 Type 2.

The original organizer scores and end-to-end latency are recomputed directly
from the historical logs and remain the official evidence. The new ablation is
a **post-hoc organizer-test replay**: labels were available after the
competition, so replay values are not a second official result or a blind
unseen-test score.

## Canonical replay

The runner executes each ablation variant once with greedy decoding:

```text
Type 1: 50 questions × 3 variants = 150 jobs
Type 2: 50 questions × 4 variants = 200 jobs
Total:                              350 jobs
```

No separate latency replay is scheduled. The two organizer logs already contain
official per-request end-to-end duration; the 350 accuracy jobs still capture
stage-level, LLM, Z3, PAL, and self-repair telemetry.

Canonical command:

```bash
python paper/run_paper_experiments.py \
  --mode full \
  --evaluation-data btc-rounds \
  --temperature 0 \
  --repeats 1 \
  --deterministic-repeats 1 \
  --latency-samples 0 \
  --round1-log /private/path/exact_eval_round1_Cay_Nha_La_Vuon.json \
  --round2-log /private/path/exact_eval_round2_Cay_Nha_La_Vuon.json
```

On a Colab T4, use
[`EXACT2026_BTC_Test_Replay_T4_Colab.ipynb`](EXACT2026_BTC_Test_Replay_T4_Colab.ipynb).
It clones GitHub, validates both private logs, pins model revisions, installs
dependencies, runs public-data smoke validation, and then runs/resumes the
350-job private replay.

## Ablations

Type 1:

- `t1_cot_only`: CoT with Z3 disabled;
- `t1_cot_z3_no_repair`: CoT plus exemplar-augmented Z3, repair disabled;
- `t1_full`: CoT, Z3, and at most one Z3 repair.

Type 2:

- `t2_cot_only`: direct CoT;
- `t2_rag_solver`: parser, formula RAG, and deterministic solvers;
- `t2_rag_solver_pal`: previous variant plus first-pass PAL;
- `t2_full`: augmented parser, RAG/solver, PAL, one repair, then CoT fallback.

Type-1 answers are scored against the organizer answer and aliases. Organizer
premise indices are already zero-based and are not shifted. Type-2 uses
answer-and-unit strict accuracy with numeric unit conversion.

## Label isolation and provenance

`load_btc_test_replay()` enforces the boundary:

```text
request_payload ──> inference question, premises, options, original query ID
expected        ──> post-response scoring only
```

Historical `model_response`, `result`, status, points, and duration never enter
the inference example. Internal IDs are namespaced as `round1:<id>` and
`round2:<id>` so resume/cache keys cannot collide. Source hashes, sample
versions, code/model revisions, GPU identity, dependency versions, and all
protocol arguments are captured in the run manifest.

The canonical source identities are:

```text
Round 1 SHA-256  6d5e7a86a5e0a7ed1e1c3e9f43b7228bd930d0e4a7a6133f62ad302483b7fd4b
Round 2 SHA-256  03032ec92f384d3c0ccf76e9f7801cf0b107452805b97115b00061e9c6fdc813
```

## Model condition

The Colab notebook pins:

- `Qwen/Qwen2.5-7B-Instruct` at
  `a09a35458c702b33eeacc393d103063234e8bc28`;
- `sentence-transformers/all-MiniLM-L6-v2` at
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

A T4 loads Qwen with 4-bit NF4. This is a reproducible local replay condition,
not FP16 production parity. The paper must keep the historical official result
and the local 4-bit replay clearly separated.

## Outputs

The quality gate requires exactly 350/350 completed jobs, zero ordinary
failures, and zero infrastructure failures. A successful run creates
`PAPER_READY` and `TEST_REPLAY_READY`.

Important aggregate outputs:

```text
paper_results.md
metrics/summary.json
metrics/ablation.csv
metrics/replay_by_round.csv
metrics/component_stats.csv
metrics/paired_bootstrap.csv
metrics/quality_gate.json
tables/*.csv|*.md|*.tex
figures/architecture.{png,pdf,mmd}
```

Private audit outputs include `predictions.jsonl`, `events.jsonl`,
`errors.jsonl`, and `stage_cache.jsonl`. They can contain organizer questions,
premises, gold values, generated programs, or model text and must not be
published.

Raw case-study export is disabled for BTC replay. The runner writes only a
privacy notice to `cases/`; reproduce a hidden test case in the paper only
after receiving explicit organizer permission.

## Validation and resume

```bash
python paper/run_paper_experiments.py --mode self-test
python paper/run_paper_experiments.py \
  --mode dry-run \
  --evaluation-data btc-rounds \
  --temperature 0
```

Checkpoints are append-only. Re-run the exact same command after an interrupted
Colab session. Changing code, model revision, GPU, source hashes, or protocol
arguments produces a different config hash and a separate experiment directory.

The legacy retrospective public-data protocol remains available only when
explicitly requested with `--evaluation-data public`; it is not the default
paper evaluation.
