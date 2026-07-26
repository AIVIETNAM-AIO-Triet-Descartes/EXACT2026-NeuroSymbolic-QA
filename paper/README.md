# EXACT 2026 paper experiments

`run_paper_experiments.py` is the only executable entrypoint. It aggregates the
official Round 1/2 logs, runs the public-data ablation matrix, records component
telemetry, profiles uncached latency, selects public case studies, and creates
paper-ready tables and an architecture figure.

## Google Colab

Open the cloned repository in Colab, select a GPU runtime, then run one command:

```bash
!python paper/run_paper_experiments.py --mode full --mount-drive
```

The two organizer aggregate logs are intentionally not copied into `paper/`
because they contain hidden-round records and are not tracked by Git. Upload or
copy both supplied JSON files to the repository root first. If they live in
Drive, pass their absolute paths:

```bash
!python paper/run_paper_experiments.py --mode full --mount-drive \
  --round1-log /content/drive/MyDrive/exact_eval_round1_Cay_Nha_La_Vuon.json \
  --round2-log /content/drive/MyDrive/exact_eval_round2_Cay_Nha_La_Vuon.json
```

The runner stops immediately if either log is missing; it records only each
file's name and SHA-256 in generated manifests and never copies hidden
questions into case studies.

The runner installs only missing, paper-specific dependencies. If Google Drive
is mounted, checkpoints default to:

```text
/content/drive/MyDrive/EXACT2026-paper-results/full_ablation/
```

Run the same command after a disconnect. Append-only JSONL checkpoints let it
resume completed `(phase, variant, repeat, query_id)` entries without overwriting
them. Failed or infrastructure-failed jobs are retried on the next invocation.
`--no-resume` always creates a fresh timestamped directory, so it cannot append
duplicates to an old run.

For a fast preflight before committing to the long run:

```bash
!python paper/run_paper_experiments.py --mode dry-run --mount-drive
!python paper/run_paper_experiments.py --mode smoke --mount-drive
```

The full experiment is large: 808 Type-1 and 200 Type-2 public examples. Neural
variants use three seeds; the deterministic Type-2 variant uses one repeat.
Type-1 CoT and first-pass Z3 generations are paired and cached across variants
within a repeat. The declared matrix contains 9,272 logical accuracy
evaluations plus 400 uncached latency evaluations (50 examples per variant);
shared-stage caching substantially reduces physical Type-1 LLM calls. A
separate uncached stratified profile supplies real latency.
The runner pins a mutable Hugging Face revision to its immutable commit before
choosing a run directory. GPU identity, code/prompt/config hashes, public-data
hashes, official-log hashes, retrieval mode, model condition and timeouts are
also part of the experiment identity; a changed condition cannot silently mix
with an earlier checkpoint.

## Model backends

With no endpoint argument, Colab loads `Qwen/Qwen2.5-7B-Instruct` through
Transformers. `--quantization auto` uses FP16 on a GPU with at least 22 GiB and
4-bit NF4 otherwise. Quantized results are automatically labeled as a
non-production-parity condition.

To use the production-like OpenAI-compatible endpoint instead:

```bash
!PAPER_LLM_BASE_URL=http://HOST:PORT/v1 \
  python paper/run_paper_experiments.py --mode full --mount-drive
```

If authentication is needed, put the token in `PAPER_LLM_API_KEY`. Secrets are
read from the environment and never written to logs. For a faithful FP16
condition, use an L4/A100-class runtime or the original endpoint; T4-class GPUs
normally require quantization.

Endpoint runs record the served model IDs and refuse a resume when those IDs
change. An API deployment can still change weights behind an unchanged ID, so
the paper must name/version the endpoint deployment separately when possible.

## Ablations

Type 1:

- `t1_cot_only`: CoT plus the same deterministic post-processing, with Z3 off.
- `t1_cot_z3_no_repair`: CoT plus exemplar-augmented Z3, repair off.
- `t1_full`: the current Type-1 control flow with at most one Z3 repair, using
  the paper-owned executor described below.

Type 2:

- `t2_cot_only`: direct CoT from the raw question.
- `t2_rag_solver`: regex parser, formula RAG, SymPy/specialized solvers.
- `t2_rag_solver_pal`: previous variant plus one first-pass PAL attempt.
- `t2_full`: LLM-augmented parser, RAG/solvers, PAL, one repair, then CoT.
- `t2_full_e2e`: latency-only profile adding the LLM presentation explainer.

All accuracy results are labeled retrospective public-data ablations. Type 1
is a retrospective public corpus with no
declared split; Type 2 is the public dev split. The public Type-1 request
contract treats its 360 embedded-option questions as MCQ and its remaining 448
questions as Yes/No/Uncertain, matching the repository's evaluation-set
builder. Hidden round questions are used only to compute aggregate official
scores and latency; they are never copied to case-study artifacts.

## Output

```text
outputs/<run_name>/
├── run_config.json
├── environment.json
├── dataset_manifest.json
├── warmup.json
├── stage_cache.jsonl
├── events.jsonl
├── predictions.jsonl
├── errors.jsonl
├── sessions.jsonl
├── logs/runner.log
├── metrics/
├── tables/
├── cases/
├── figures/
└── paper_results.md
```

`metrics/quality_gate.json` and `metrics/completeness.csv` contain the expected
and observed count for every phase/variant/repeat. A `PAPER_READY` marker is
created only after the full 808/200 protocol, three neural repeats, latency
profile and all jobs finish without failures. Smoke, dry, limited and partial
runs are prominently marked `NOT PAPER-READY`.

`predictions.jsonl` contains one complete record per query/variant/repeat,
including stage timings, physical versus cached LLM calls, generated public-data
Z3/PAL code, executor outcomes, repair state, final source, prediction and
score. `events.jsonl` is an append-only lifecycle log. Events are buffered until
the query timer stops so Drive I/O is excluded from the latency measurement.
Generated programs run in scrubbed child processes with validation and a hard
timeout. This reduces accidental side effects but is not a security sandbox;
run only the trusted public corpus supplied with the project.

Success definitions are fixed:

- Z3/PAL success: final accepted executable result divided by logical calls.
- Repair execution success: executable repaired result divided by repair
  activations.
- Repair task success: repaired output is accepted and the final benchmark
  answer is correct, divided by repair activations.
- Execution success and benchmark correctness are always separate columns.
- Missing, failed and unparseable predictions remain in the metric denominator.
- Type-1 answer accuracy uses all 808 examples; premise F1/combined/full-correct
  use the 797 examples with non-empty premise annotations.
- Type-2 numeric answers use 2% relative tolerance. Compatible scaled units
  (for example T↔mT, J↔mJ, kg↔g) are normalized; distinct reported unit families
  such as N/C and V/m are not conflated.

Controlled latency is one uncached, no-retry, stratified application-pipeline
profile. It reports scheduled/completed/failed counts, observed timeout counts
and the share of successful requests over 60 seconds. It is not model-only
inference time. Organizer `duration_seconds` is reported separately as official
per-request end-to-end latency.

Semantic formula retrieval must initialize successfully for the default full
run. To intentionally run a separately hashed keyword-only condition, pass
`--disable-semantic-rag`.

The runner intentionally omits other-team comparisons because no
organizer-published leaderboard was supplied.
