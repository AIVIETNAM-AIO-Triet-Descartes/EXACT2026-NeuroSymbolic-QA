#!/usr/bin/env python3
"""
One-file, Colab-friendly experiment harness for the EXACT 2026 paper.

Default behaviour:
  1. aggregate the two official round logs without copying hidden questions;
  2. run controlled public-data ablations;
  3. capture structured Z3/PAL/self-repair telemetry;
  4. run an uncached latency profile;
  5. generate paper-ready CSV/Markdown/LaTeX tables, case studies, and figures.

The harness deliberately does not change the public /predict schema or any
production module. Generated Z3/PAL programs are executed in scrubbed child
processes with a hard timeout; this is safer than the in-process production
executors and is recorded as an experimental condition in the manifest.

Typical Colab command (one Python entrypoint):

    !python paper/run_paper_experiments.py --mode full --mount-drive

Quick validation:

    python paper/run_paper_experiments.py --mode self-test
    python paper/run_paper_experiments.py --mode dry-run
    python paper/run_paper_experiments.py --mode smoke
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import contextvars
import csv
import dataclasses
import datetime as dt
import functools
import hashlib
import importlib
import importlib.metadata
import io
import json
import logging
import math
import os
import platform
import random
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional


SCHEMA_VERSION = "1.0"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DEFAULT_SEEDS = (2026, 2027, 2028)
TYPE1_VARIANTS = (
    "t1_cot_only",
    "t1_cot_z3_no_repair",
    "t1_full",
)
TYPE2_VARIANTS = (
    "t2_cot_only",
    "t2_rag_solver",
    "t2_rag_solver_pal",
    "t2_full",
)

BASE_IMPORTS = {
    "fastapi": "fastapi>=0.110",
    "pydantic": "pydantic>=2",
    "httpx": "httpx>=0.27",
    "yaml": "pyyaml>=6",
    "loguru": "loguru>=0.7",
    "openai": "openai>=1.30",
    "z3": "z3-solver>=4.13",
    "sympy": "sympy>=1.12",
    "numpy": "numpy>=1.24",
    "matplotlib": "matplotlib>=3.7",
}
LOCAL_MODEL_IMPORTS = {
    "torch": "torch>=2.2",
    "transformers": "transformers>=4.46",
    "accelerate": "accelerate>=0.30",
    "bitsandbytes": "bitsandbytes>=0.43",
}
RAG_IMPORTS = {
    "faiss": "faiss-cpu>=1.8",
    "sentence_transformers": "sentence-transformers>=2.7",
}

UNIT_FACTORS = {
    "": 1.0,
    "1": 1.0,
    "-": 1.0,
    "pf": 1e-12,
    "nf": 1e-9,
    "uf": 1e-6,
    "mf": 1e-3,
    "f": 1.0,
    "mohm": 1e-3,
    "ohm": 1.0,
    "kohm": 1e3,
    "megohm": 1e6,
    "ua": 1e-6,
    "ma": 1e-3,
    "a": 1.0,
    "mv": 1e-3,
    "v": 1.0,
    "kv": 1e3,
    "mw": 1e-3,
    "w": 1.0,
    "kw": 1e3,
    "nj": 1e-9,
    "uj": 1e-6,
    "mj": 1e-3,
    "j": 1.0,
    "kj": 1e3,
    "nc": 1e-9,
    "uc": 1e-6,
    "mc": 1e-3,
    "c": 1.0,
    "uh": 1e-6,
    "mh": 1e-3,
    "h": 1.0,
    "mm": 1e-3,
    "cm": 1e-2,
    "m": 1.0,
    "km": 1e3,
    "ms": 1e-3,
    "us": 1e-6,
    "s": 1.0,
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "n": 1.0,
    "n/c": 1.0,
    "v/m": 1.0,
    "kv/m": 1e3,
    "mv/m": 1e6,
    "t": 1.0,
    "mt": 1e-3,
    "wb": 1.0,
    "pa": 1.0,
    "kpa": 1e3,
    "g": 1e-3,
    "kg": 1.0,
    "m/s": 1.0,
    "km/h": 1000.0 / 3600.0,
    "m/s^2": 1.0,
    "degreec": 1.0,
    "times": 1.0,
    "degree": 1.0,
    "%": 1.0,
}

UNIT_FAMILIES = {
    **{unit: "dimensionless" for unit in {"", "1", "-"}},
    **{unit: "capacitance" for unit in {"pf", "nf", "uf", "mf", "f"}},
    **{
        unit: "resistance"
        for unit in {"mohm", "ohm", "kohm", "megohm"}
    },
    **{unit: "current" for unit in {"ua", "ma", "a"}},
    **{unit: "voltage" for unit in {"mv", "v", "kv"}},
    **{unit: "power" for unit in {"mw", "w", "kw"}},
    **{unit: "energy" for unit in {"nj", "uj", "mj", "j", "kj"}},
    **{unit: "charge" for unit in {"nc", "uc", "mc", "c"}},
    **{unit: "inductance" for unit in {"uh", "mh", "h"}},
    **{unit: "length" for unit in {"mm", "cm", "m", "km"}},
    **{unit: "time" for unit in {"ms", "us", "s"}},
    **{unit: "frequency" for unit in {"hz", "khz", "mhz"}},
    **{unit: "electric_field_v_per_m" for unit in {"v/m", "kv/m", "mv/m"}},
    "n/c": "electric_field_n_per_c",
    "n": "force",
    **{unit: "magnetic_field" for unit in {"t", "mt"}},
    "wb": "magnetic_flux",
    **{unit: "pressure" for unit in {"pa", "kpa"}},
    **{unit: "mass" for unit in {"g", "kg"}},
    **{unit: "velocity" for unit in {"m/s", "km/h"}},
    "m/s^2": "acceleration",
    "degreec": "temperature_celsius",
    "times": "dimensionless_multiplier",
    "degree": "angle",
    "%": "percent",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def json_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return repr(value)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=json_default,
    )


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truncate(value: Any, limit: int = 4000) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "…<truncated>"


def safe_url(url: str) -> str:
    """Remove userinfo, query parameters, and fragments before logging a URL."""
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname or ""
        if parsed.port:
            hostname += f":{parsed.port}"
        return urllib.parse.urlunsplit(
            (parsed.scheme, hostname, parsed.path, "", "")
        )
    except Exception:
        return "<invalid-url>"


def find_repo_root(start: Path) -> Path:
    candidates = [start.resolve(), *start.resolve().parents]
    script_root = Path(__file__).resolve().parents[1]
    if script_root not in candidates:
        candidates.insert(0, script_root)
    for candidate in candidates:
        if (
            (candidate / "api" / "main.py").exists()
            and (candidate / "pipeline").is_dir()
            and (candidate / "Logic_Based_Educational_Queries.json").exists()
        ):
            return candidate
    raise RuntimeError(
        "Cannot locate repository root. Run this file from the cloned repository."
    )


def is_colab() -> bool:
    return bool(
        os.environ.get("COLAB_RELEASE_TAG")
        or os.environ.get("COLAB_BACKEND_VERSION")
        or "google.colab" in sys.modules
    )


def maybe_mount_drive(enabled: bool, logger: logging.Logger) -> None:
    if not enabled:
        return
    if not is_colab():
        logger.warning("--mount-drive was requested outside Google Colab; skipped.")
        return
    mount_path = Path("/content/drive")
    if (mount_path / "MyDrive").exists():
        logger.info("Google Drive is already mounted.")
        return
    try:
        from google.colab import drive  # type: ignore

        drive.mount(str(mount_path), force_remount=False)
        logger.info("Google Drive mounted at %s.", mount_path)
    except Exception as exc:
        raise RuntimeError(f"Could not mount Google Drive: {exc}") from exc


def missing_packages(import_map: dict[str, str]) -> list[str]:
    missing: list[str] = []
    for module, package in import_map.items():
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(package)
    return missing


def ensure_dependencies(args: argparse.Namespace) -> None:
    if args.mode in {"dry-run", "official-only"}:
        return

    if args.mode == "self-test":
        packages = {
            key: value
            for key, value in BASE_IMPORTS.items()
            if key in {"yaml", "loguru", "z3", "sympy", "numpy"}
        }
    else:
        packages = dict(BASE_IMPORTS)
        # A smoke run validates control flow and always emits Mermaid; raster/
        # PDF rendering is required for full runs but may be absent in a lean
        # local validation environment.
        if args.mode == "smoke":
            packages.pop("matplotlib", None)
    if args.backend == "transformers" or (
        args.backend == "auto" and not args.api_base
    ):
        packages.update(LOCAL_MODEL_IMPORTS)
    if not args.disable_semantic_rag:
        packages.update(RAG_IMPORTS)

    missing = missing_packages(packages)
    if not missing:
        return

    should_install = args.install_deps == "yes" or (
        args.install_deps == "auto" and is_colab()
    )
    if not should_install:
        raise RuntimeError(
            "Missing dependencies: "
            + ", ".join(missing)
            + ". On Colab use the default --install-deps auto; elsewhere run "
              "with --install-deps yes or install the packages manually."
        )

    if os.environ.get("PAPER_DEPS_BOOTSTRAPPED") == "1":
        raise RuntimeError(
            "Dependency bootstrap completed but imports still fail: "
            + ", ".join(missing)
        )

    print("[setup] Installing minimal paper dependencies:", " ".join(missing))
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--quiet", *missing]
    )
    os.environ["PAPER_DEPS_BOOTSTRAPPED"] = "1"
    os.execv(sys.executable, [sys.executable, *sys.argv])


class JsonlWriter:
    def __init__(self, path: Path, *, fsync: bool = False):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("a", encoding="utf-8", buffering=1)
        self.fsync = fsync

    def write(self, row: dict[str, Any]) -> None:
        self.handle.write(
            json.dumps(row, ensure_ascii=False, default=json_default) + "\n"
        )
        self.handle.flush()
        if self.fsync:
            os.fsync(self.handle.fileno())

    def close(self) -> None:
        self.handle.close()


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                # A Colab disconnect can leave only the final line incomplete.
                continue
            if isinstance(value, dict):
                yield value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=json_default)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def setup_logging(output_dir: Path, verbose: bool) -> logging.Logger:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("paper_experiments")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )
    stream = logging.StreamHandler()
    stream.setLevel(logging.DEBUG if verbose else logging.INFO)
    stream.setFormatter(formatter)
    file_handler = logging.FileHandler(log_dir / "runner.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(stream)
    logger.addHandler(file_handler)
    return logger


def package_version(name: str) -> Optional[str]:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def git_metadata(repo_root: Path) -> dict[str, Any]:
    def run(*argv: str) -> str:
        result = subprocess.run(
            ["git", *argv],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        return result.stdout.strip()

    status = run("status", "--short")
    return {
        "commit_sha": run("rev-parse", "HEAD") or None,
        "branch": run("rev-parse", "--abbrev-ref", "HEAD") or None,
        "dirty": bool(status),
        "status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "status_entries": len(status.splitlines()) if status else 0,
    }


def code_source_manifest(repo_root: Path) -> dict[str, Any]:
    """Fingerprint the code, prompts and configuration that affect predictions."""
    candidates: list[Path] = []
    for directory_name in ("api", "llm", "pipeline", "evaluation", "configs"):
        directory = repo_root / directory_name
        if directory.exists():
            candidates.extend(
                path
                for path in directory.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix.lower() in {".py", ".json", ".yaml", ".yml", ".toml"}
            )
    for relative in (
        "data/z3_examples.json",
        "requirements.txt",
        "pyproject.toml",
    ):
        path = repo_root / relative
        if path.exists():
            candidates.append(path)
    rows = [
        {
            "path": str(path.relative_to(repo_root)),
            "sha256": sha256_file(path),
        }
        for path in sorted(set(candidates))
    ]
    return {
        "aggregate_sha256": stable_hash(rows),
        "file_count": len(rows),
        "files": rows,
    }


def environment_metadata(
    repo_root: Path,
    args: argparse.Namespace,
    backend: str,
    quantization: str,
) -> dict[str, Any]:
    packages = [
        "torch",
        "transformers",
        "accelerate",
        "bitsandbytes",
        "openai",
        "z3-solver",
        "sympy",
        "numpy",
        "faiss-cpu",
        "sentence-transformers",
        "pydantic",
        "fastapi",
        "matplotlib",
    ]
    gpu: dict[str, Any] = {}
    try:
        import torch

        gpu = {
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
            "devices": [
                {
                    "name": torch.cuda.get_device_name(i),
                    "total_memory_bytes": torch.cuda.get_device_properties(i).total_memory,
                }
                for i in range(torch.cuda.device_count())
            ],
        }
    except Exception as exc:
        gpu = {"cuda_available": False, "probe_error": str(exc)}

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "executable": sys.executable,
        "colab": is_colab(),
        "backend": backend,
        "api_base": safe_url(args.api_base) if args.api_base else None,
        "model_id": args.model,
        "requested_model_revision": args.model_revision,
        "embedding_model_id": args.embedding_model,
        "requested_embedding_model_revision": args.embedding_model_revision,
        "quantization": quantization,
        "temperature": args.temperature,
        "packages": {name: package_version(name) for name in packages},
        "gpu": gpu,
        "git": git_metadata(repo_root),
        "executor": {
            "kind": "paper-owned restricted subprocess",
            "hard_timeout_seconds": args.code_timeout,
            "environment_scrubbed": True,
            "production_parity": False,
        },
    }


def resolve_backend(args: argparse.Namespace) -> str:
    if args.backend != "auto":
        return args.backend
    env_url = os.environ.get("PAPER_LLM_BASE_URL", "").strip()
    if not args.api_base and env_url:
        args.api_base = env_url
    return "openai" if args.api_base else "transformers"


def accelerator_identity(backend: str) -> dict[str, Any]:
    if backend != "transformers":
        return {"kind": "endpoint_defined"}
    try:
        import torch

        return {
            "kind": "local_cuda",
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
            "devices": [
                {
                    "name": torch.cuda.get_device_name(index),
                    "total_memory_bytes": torch.cuda.get_device_properties(
                        index
                    ).total_memory,
                }
                for index in range(torch.cuda.device_count())
            ],
        }
    except Exception as exc:
        return {"kind": "local_cuda", "probe_error": str(exc)}


def resolve_hf_revision(
    model: str,
    requested_revision: str,
    logger: logging.Logger,
) -> str:
    if re.fullmatch(r"[0-9a-fA-F]{40}", requested_revision):
        return requested_revision.lower()
    try:
        from huggingface_hub import HfApi

        resolved = str(
            HfApi().model_info(model, revision=requested_revision).sha or ""
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not resolve the mutable Hugging Face revision before the run. "
            "Retry with network access or pass an immutable 40-character commit "
            f"to --model-revision. Root cause: {type(exc).__name__}: {exc}"
        ) from exc
    if not re.fullmatch(r"[0-9a-fA-F]{40}", resolved):
        raise RuntimeError(
            f"Hugging Face returned a non-commit revision for {model}: {resolved!r}"
        )
    logger.info(
        "Pinned local model %s revision %s to commit %s.",
        model,
        requested_revision,
        resolved,
    )
    return resolved.lower()


def resolve_quantization(args: argparse.Namespace, backend: str) -> str:
    if backend != "transformers":
        return "endpoint-defined"
    if args.quantization != "auto":
        return args.quantization
    try:
        import torch

        if torch.cuda.is_available():
            gib = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return "none" if gib >= 22 else "4bit"
    except Exception:
        pass
    return "none"


def output_root(repo_root: Path, args: argparse.Namespace) -> Path:
    if args.output_dir:
        base = Path(args.output_dir).expanduser()
    elif os.environ.get("PAPER_OUTPUT_DIR"):
        base = Path(os.environ["PAPER_OUTPUT_DIR"]).expanduser()
    elif Path("/content/drive/MyDrive").exists():
        base = Path("/content/drive/MyDrive/EXACT2026-paper-results")
    else:
        base = repo_root / "paper" / "outputs"
    if not base.is_absolute():
        base = repo_root / base
    return base.resolve() / args.run_name


def percentile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def latency_stats(values: Iterable[float]) -> dict[str, Any]:
    data = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not data:
        return {
            "n": 0,
            "mean_s": None,
            "std_s": None,
            "median_s": None,
            "p90_s": None,
            "p95_s": None,
            "min_s": None,
            "max_s": None,
        }
    return {
        "n": len(data),
        "mean_s": statistics.fmean(data),
        "std_s": statistics.pstdev(data) if len(data) > 1 else 0.0,
        "median_s": statistics.median(data),
        "p90_s": percentile(data, 0.90),
        "p95_s": percentile(data, 0.95),
        "min_s": min(data),
        "max_s": max(data),
    }


def mean_std(values: Iterable[Optional[float]]) -> tuple[Optional[float], Optional[float]]:
    data = [float(v) for v in values if v is not None]
    if not data:
        return None, None
    return (
        statistics.fmean(data),
        statistics.stdev(data) if len(data) > 1 else 0.0,
    )


def normalize_unit(unit: Any) -> str:
    text = str(unit or "").strip()
    if text in {"", "-", "—", "–", "unitless", "dimensionless"}:
        return ""
    text = (
        text.replace("Ω", "ohm")
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("°", "degree")
        .replace("·", "*")
        .replace(" ", "")
    )
    text = re.sub(r"(?i)megohm", "megohm", text)
    return text.lower()


def unit_factor(unit: Any) -> Optional[float]:
    return UNIT_FACTORS.get(normalize_unit(unit))


def unit_exact_match(predicted: Any, gold: Any) -> bool:
    return normalize_unit(predicted) == normalize_unit(gold)


def unit_compatible(predicted: Any, gold: Any) -> bool:
    pred = normalize_unit(predicted)
    target = normalize_unit(gold)
    if pred == target:
        return True
    pred_family = UNIT_FAMILIES.get(pred)
    target_family = UNIT_FAMILIES.get(target)
    return bool(
        pred_family
        and target_family
        and pred_family == target_family
        and pred_family != "dimensionless"
    )


def split_semicolon(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(";")]


def parse_numeric(value: Any) -> Optional[float]:
    try:
        from evaluation.answer_compare import parse_number

        return parse_number(str(value or ""))
    except Exception:
        text = str(value or "").strip().replace("×", "*").replace("^", "**")
        try:
            return float(text)
        except Exception:
            return None


def qualitative_match(predicted: Any, gold: Any) -> bool:
    def tokens(value: Any) -> set[str]:
        return set(re.findall(r"\w+", str(value or "").lower()))

    pred_tokens = tokens(predicted)
    gold_tokens = tokens(gold)
    if not gold_tokens:
        return pred_tokens == gold_tokens
    return len(pred_tokens & gold_tokens) / len(gold_tokens) >= 0.75


def score_answer_component(
    predicted_answer: Any,
    predicted_unit: Any,
    gold_answer: Any,
    gold_unit: Any,
    rel_tol: float,
) -> tuple[bool, str, dict[str, Any]]:
    pred_text = str(predicted_answer or "").strip()
    gold_text = str(gold_answer or "").strip()
    if gold_text.lower() in {"yes", "no"}:
        correct = pred_text.lower() == gold_text.lower()
        return correct, "yes_no", {"normalized_pred": pred_text.lower()}

    gold_num = parse_numeric(gold_text)
    if gold_num is not None:
        pred_num = parse_numeric(pred_text)
        if pred_num is None:
            return False, "numeric", {"error": "prediction_unparseable"}
        gold_factor = unit_factor(gold_unit)
        pred_factor = unit_factor(predicted_unit)
        if gold_factor is None:
            gold_factor = 1.0
        if pred_factor is None:
            pred_factor = 1.0
        gold_si = gold_num * gold_factor
        pred_si = pred_num * pred_factor
        if abs(gold_si) > 1e-15:
            relative_error = abs(pred_si - gold_si) / abs(gold_si)
        else:
            relative_error = abs(pred_si - gold_si)
        return (
            relative_error <= rel_tol,
            "numeric",
            {
                "pred_si": pred_si,
                "gold_si": gold_si,
                "relative_error": relative_error,
            },
        )

    correct = qualitative_match(pred_text, gold_text)
    return correct, "qualitative", {}


def score_type2(
    predicted_answer: Any,
    predicted_unit: Any,
    gold_answer: Any,
    gold_unit: Any,
    rel_tol: float = 0.02,
) -> dict[str, Any]:
    gold_parts = split_semicolon(gold_answer)
    pred_parts = split_semicolon(predicted_answer)
    gold_units = split_semicolon(gold_unit)
    pred_units = split_semicolon(predicted_unit)
    is_multi = len(gold_parts) > 1

    if len(pred_parts) != len(gold_parts):
        return {
            "answer_correct": False,
            "unit_correct": False,
            "strict_correct": False,
            "kind": "multi" if is_multi else "unparseable",
            "detail": "component_count_mismatch",
        }

    answer_results: list[bool] = []
    unit_results: list[bool] = []
    kinds: list[str] = []
    details: list[dict[str, Any]] = []
    for index, gold_part in enumerate(gold_parts):
        pred_part = pred_parts[index]
        gold_u = gold_units[index] if index < len(gold_units) else ""
        pred_u = pred_units[index] if index < len(pred_units) else ""
        answer_ok, kind, detail = score_answer_component(
            pred_part, pred_u, gold_part, gold_u, rel_tol
        )
        answer_results.append(answer_ok)
        unit_results.append(unit_compatible(pred_u, gold_u))
        kinds.append(kind)
        details.append(detail)

    answer_correct = all(answer_results)
    unit_correct = all(unit_results)
    kind = "multi" if is_multi else kinds[0]
    return {
        "answer_correct": answer_correct,
        "unit_correct": unit_correct,
        "strict_correct": answer_correct and unit_correct,
        "kind": kind,
        "detail": details,
    }


def premise_prf(
    predicted: Iterable[int], gold: Optional[Iterable[int]]
) -> dict[str, Optional[float]]:
    if gold is None:
        return {
            "premise_precision": None,
            "premise_recall": None,
            "premise_f1": None,
            "premise_exact": None,
        }
    pred_set = {int(x) for x in predicted}
    gold_set = {int(x) for x in gold}
    if not pred_set and not gold_set:
        precision = recall = f1 = 1.0
    else:
        intersection = len(pred_set & gold_set)
        precision = intersection / len(pred_set) if pred_set else 0.0
        recall = intersection / len(gold_set) if gold_set else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
    return {
        "premise_precision": precision,
        "premise_recall": recall,
        "premise_f1": f1,
        "premise_exact": float(pred_set == gold_set),
    }


def normalize_logic_answer(value: Any) -> str:
    text = str(value or "").strip()
    match = re.match(r"^([A-D])(?:[.)\s]|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    lowered = text.lower()
    mapping = {
        "yes": "Yes",
        "true": "Yes",
        "no": "No",
        "false": "No",
        "unknown": "Unknown",
        "uncertain": "Unknown",
        "cannot determine": "Unknown",
        "cannot be determined": "Unknown",
    }
    return mapping.get(lowered, text)


def score_type1(
    predicted_answer: Any,
    predicted_premises: Iterable[int],
    gold_answer: Any,
    gold_premises: Optional[Iterable[int]],
) -> dict[str, Any]:
    pred_norm = normalize_logic_answer(predicted_answer)
    gold_norm = normalize_logic_answer(gold_answer)
    answer_correct = pred_norm == gold_norm
    premise = premise_prf(predicted_premises, gold_premises)
    combined = (
        0.5 * float(answer_correct) + 0.5 * float(premise["premise_f1"])
        if premise["premise_f1"] is not None
        else None
    )
    full_correct = (
        float(answer_correct and bool(premise["premise_exact"]))
        if premise["premise_exact"] is not None
        else None
    )
    return {
        "answer_correct": answer_correct,
        "normalized_prediction": pred_norm,
        "normalized_gold": gold_norm,
        **premise,
        "combined_score": combined,
        "full_correct": full_correct,
    }


@dataclasses.dataclass
class PublicExample:
    track: str
    query_id: str
    question: str
    premises: list[str]
    options: list[str]
    gold_answer: str
    gold_unit: str = ""
    gold_premises: Optional[list[int]] = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)


def load_type1_public(path: Path) -> list[PublicExample]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    examples: list[PublicExample] = []
    for record_index, record in enumerate(raw):
        premises = [str(x) for x in record.get("premises-NL", [])]
        questions = record.get("questions", [])
        answers = record.get("answers", [])
        indices = record.get("idx", [])
        separate_choices = record.get("choices")
        for question_index, question_value in enumerate(questions):
            question = str(question_value)
            has_embedded_options = bool(
                re.search(r"(?m)^\s*A[.)]\s+", question)
                and re.search(r"(?m)^\s*B[.)]\s+", question)
            )
            if separate_choices and not has_embedded_options:
                question += "\n" + "\n".join(
                    f"{letter}. {choice}"
                    for letter, choice in zip("ABCD", separate_choices)
                )
                has_embedded_options = True

            # Reconstruct the public-corpus request contract without consulting
            # the per-example gold answer. All non-MCQ records in this corpus
            # belong to its Y/N/uncertain task family (including six questions
            # whose surface form begins with What/Which/How). Explicit options
            # therefore prevent the live classifier from misreading those six
            # as open questions. Embedded MCQs already carry their option text.
            options = [] if has_embedded_options else ["Yes", "No", "Uncertain"]
            raw_idx = indices[question_index] if question_index < len(indices) else []
            gold_premises = (
                [int(index) - 1 for index in raw_idx]
                if isinstance(raw_idx, list) and raw_idx
                else None
            )
            answer = str(answers[question_index]) if question_index < len(answers) else ""
            examples.append(
                PublicExample(
                    track="type1",
                    query_id=f"public_t1_r{record_index:04d}_q{question_index:02d}",
                    question=question,
                    premises=premises,
                    options=options,
                    gold_answer=answer,
                    gold_premises=gold_premises,
                    metadata={
                        "record_index": record_index,
                        "question_index": question_index,
                        "format": "mcq" if has_embedded_options else "ynu",
                        "request_contract": (
                            "embedded_mcq"
                            if has_embedded_options
                            else "ynu_options"
                        ),
                        "premise_annotation_available": gold_premises is not None,
                        "z3_eligible": len(premises) <= 12,
                    },
                )
            )
    return examples


def load_type2_public(path: Path) -> list[PublicExample]:
    examples: list[PublicExample] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            query_id = str(row.get("id") or f"public_t2_{index:04d}")
            examples.append(
                PublicExample(
                    track="type2",
                    query_id=query_id,
                    question=str(row.get("question") or ""),
                    premises=[],
                    options=[],
                    gold_answer=str(row.get("answer") or ""),
                    gold_unit=str(row.get("unit") or ""),
                    metadata={
                        "row_index": index,
                        "prefix": (
                            re.match(r"^[A-Z]+", query_id).group(0)
                            if re.match(r"^[A-Z]+", query_id)
                            else "UNKNOWN"
                        ),
                    },
                )
            )
    return examples


def public_dataset_manifest(repo_root: Path) -> dict[str, Any]:
    t1 = repo_root / "Logic_Based_Educational_Queries.json"
    t2 = repo_root / "data/physics/physics_dev.csv"
    formula_db = repo_root / "data/rag/physics_formulas.json"
    index = repo_root / "data/formula_index/index.faiss"
    metadata = repo_root / "data/formula_index/metadata.pkl"
    encoder = repo_root / "data/formula_index/encoder.json"
    return {
        "type1": {
            "path": str(t1.relative_to(repo_root)),
            "sha256": sha256_file(t1),
            "examples": len(load_type1_public(t1)),
            "label": "retrospective public development corpus",
        },
        "type2": {
            "path": str(t2.relative_to(repo_root)),
            "sha256": sha256_file(t2),
            "examples": len(load_type2_public(t2)),
            "label": "public development split",
            "known_formula_example_overlap": ["DDT361"],
        },
        "formula_db": {
            "path": str(formula_db.relative_to(repo_root)),
            "sha256": sha256_file(formula_db),
        },
        "formula_index": {
            "index_sha256": sha256_file(index) if index.exists() else None,
            "metadata_sha256": sha256_file(metadata) if metadata.exists() else None,
            "encoder_sha256": sha256_file(encoder) if encoder.exists() else None,
        },
        "hidden_round_data_policy": "aggregate_only; no hidden query copied",
    }


def official_round_metrics(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    logs = list(data.get("logs") or [])
    summary = data.get("summary") or {}
    by_type = {
        "type1": [item for item in logs if item.get("type") == "type1"],
        "type2": [item for item in logs if item.get("type") == "type2"],
    }

    def field(item: dict[str, Any], name: str, default: Any = None) -> Any:
        if name in item:
            return item.get(name, default)
        return (item.get("result") or {}).get(name, default)

    p1_t1 = [float(field(item, "p1_score", 0.0)) / 100 for item in by_type["type1"]]
    p2_t1 = [float(field(item, "p2_score", 0.0)) / 100 for item in by_type["type1"]]
    p1_t2 = [float(field(item, "p1_score", 0.0)) / 100 for item in by_type["type2"]]

    # Regression check: official Type-1 P2 is set-F1, not Jaccard.
    p2_mismatches: list[dict[str, Any]] = []
    for item in by_type["type1"]:
        expected = item.get("expected") or {}
        response = item.get("model_response") or {}
        gold = expected.get("premises_used")
        predicted = response.get("premises_used") or []
        if gold is None:
            continue
        recomputed = premise_prf(predicted, gold)["premise_f1"]
        official = float(field(item, "p2_score", 0.0)) / 100
        if recomputed is None or abs(recomputed - official) > 1e-4:
            p2_mismatches.append(
                {
                    "query_id": item.get("query_id"),
                    "recomputed": recomputed,
                    "official": official,
                }
            )
    t2_mismatches: list[dict[str, Any]] = []
    for item in by_type["type2"]:
        expected = item.get("expected") or {}
        response = item.get("model_response") or {}
        recomputed = score_type2(
            response.get("answer"),
            response.get("unit"),
            expected.get("answer"),
            expected.get("unit"),
        )["strict_correct"]
        official = float(field(item, "p1_score", 0.0)) >= 100
        if bool(recomputed) != bool(official):
            t2_mismatches.append(
                {
                    "query_id": item.get("query_id"),
                    "recomputed": bool(recomputed),
                    "official": bool(official),
                }
            )

    durations_all = [float(field(item, "duration_seconds", 0.0)) for item in logs]
    durations_t1 = [
        float(field(item, "duration_seconds", 0.0)) for item in by_type["type1"]
    ]
    durations_t2 = [
        float(field(item, "duration_seconds", 0.0)) for item in by_type["type2"]
    ]
    correct_durations = [
        float(field(item, "duration_seconds", 0.0))
        for item in logs
        if float(field(item, "p1_score", 0.0)) >= 100
    ]
    type1_points_unrounded = (
        25.0
        * (statistics.fmean(p1_t1) + statistics.fmean(p2_t1))
        / 2.0
        if p1_t1 and p2_t1
        else 0.0
    )
    type2_points_unrounded = (
        25.0 * statistics.fmean(p1_t2) if p1_t2 else 0.0
    )
    time_bonus_unrounded = sum(
        0.1
        * (float(field(item, "p1_score", 0.0)) / 100.0)
        * max(
            0.0,
            1.0 - float(field(item, "duration_seconds", 0.0)) / 60.0,
        )
        for item in logs
    )
    data_points = float(summary.get("data_correct_points", 0.0) or 0.0)
    penalty_points = float(summary.get("penalty_points", 0.0) or 0.0)
    total_unrounded = (
        type1_points_unrounded
        + type2_points_unrounded
        + time_bonus_unrounded
        + data_points
        - penalty_points
    )
    score_regression_mismatches: list[dict[str, Any]] = []
    portal_checks = {
        "type1_points": (type1_points_unrounded, summary.get("type1_points")),
        "type2_points": (type2_points_unrounded, summary.get("type2_points")),
        "time_bonus_points": (
            time_bonus_unrounded,
            summary.get("time_bonus_points"),
        ),
        "total_score": (
            total_unrounded,
            summary.get("score", summary.get("total_points")),
        ),
    }
    for name, (recomputed, portal) in portal_checks.items():
        if portal is None or abs(round(recomputed, 2) - float(portal)) > 1e-9:
            score_regression_mismatches.append(
                {
                    "field": name,
                    "recomputed_unrounded": recomputed,
                    "recomputed_rounded": round(recomputed, 2),
                    "portal": portal,
                }
            )

    return {
        "source": {"filename": path.name, "sha256": sha256_file(path)},
        "round": data.get("eval_round") or summary.get("eval_round"),
        "sample_version": data.get("sample_version"),
        "n": len(logs),
        "type1_n": len(by_type["type1"]),
        "type2_n": len(by_type["type2"]),
        "total_score": summary.get("score", summary.get("total_points")),
        "type1_points": summary.get("type1_points"),
        "type2_points": summary.get("type2_points"),
        "time_bonus": summary.get("time_bonus_points"),
        "data_correctness_points": summary.get("data_correct_points", 0),
        "data_correctness_status": summary.get("data_correct_status", "unknown"),
        "penalty_points": summary.get("penalty_points", 0),
        "score_formula": {
            "type1_points_unrounded": type1_points_unrounded,
            "type2_points_unrounded": type2_points_unrounded,
            "time_bonus_unrounded": time_bonus_unrounded,
            "total_unrounded": total_unrounded,
            "type1_denominator": len(by_type["type1"]),
            "type2_denominator": len(by_type["type2"]),
            "time_bonus_denominator": len(logs),
        },
        "score_regression_mismatches": score_regression_mismatches,
        "type1_answer_accuracy": statistics.fmean(p1_t1) if p1_t1 else None,
        "type1_premise_f1": statistics.fmean(p2_t1) if p2_t1 else None,
        "type1_combined": (
            0.5 * statistics.fmean(p1_t1) + 0.5 * statistics.fmean(p2_t1)
            if p1_t1 and p2_t1
            else None
        ),
        "type1_full_correct": (
            sum(
                1
                for item in by_type["type1"]
                if bool(field(item, "ok", False))
            )
            / len(by_type["type1"])
            if by_type["type1"]
            else None
        ),
        "type2_strict_accuracy": statistics.fmean(p1_t2) if p1_t2 else None,
        "overall_p1_accuracy": (
            statistics.fmean(
                [float(field(item, "p1_score", 0.0)) / 100 for item in logs]
            )
            if logs
            else None
        ),
        "overall_full_correct": (
            sum(1 for item in logs if bool(field(item, "ok", False))) / len(logs)
            if logs
            else None
        ),
        "latency_all": latency_stats(durations_all),
        "latency_type1": latency_stats(durations_t1),
        "latency_type2": latency_stats(durations_t2),
        "latency_p1_correct": latency_stats(correct_durations),
        "p2_regression_mismatches": p2_mismatches,
        "type2_regression_mismatches": t2_mismatches,
    }


class StageCache:
    def __init__(self, path: Path, enabled: bool):
        self.path = path
        self.enabled = enabled
        self.values: dict[str, dict[str, Any]] = {}
        if enabled:
            for row in read_jsonl(path):
                key = row.get("key")
                if isinstance(key, str):
                    self.values[key] = row
        self.writer = JsonlWriter(path, fsync=True) if enabled else None

    def get(self, key: str) -> Optional[dict[str, Any]]:
        return self.values.get(key) if self.enabled else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        if not self.enabled or key in self.values:
            return
        row = {"key": key, **value}
        self.values[key] = row
        assert self.writer is not None
        self.writer.write(row)

    def close(self) -> None:
        if self.writer:
            self.writer.close()


@dataclasses.dataclass
class QueryTrace:
    run_id: str
    config_hash: str
    phase: str
    track: str
    variant: str
    repeat: int
    seed: int
    query_id: str
    events_writer: JsonlWriter
    cache: StageCache
    cache_enabled: bool
    code_timeout: float
    started_at: str = dataclasses.field(default_factory=utc_now)
    stages: dict[str, list[dict[str, Any]]] = dataclasses.field(
        default_factory=lambda: defaultdict(list)
    )
    component_logs: list[str] = dataclasses.field(default_factory=list)
    llm_calls: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    z3: dict[str, Any] = dataclasses.field(
        default_factory=lambda: {"executions": []}
    )
    pal: dict[str, Any] = dataclasses.field(
        default_factory=lambda: {"executions": []}
    )
    flags: dict[str, Any] = dataclasses.field(default_factory=dict)
    artifacts: dict[str, Any] = dataclasses.field(default_factory=dict)
    infrastructure_error: Optional[str] = None
    llm_call_index: int = 0
    pending_events: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def emit(self, event: str, **payload: Any) -> None:
        # Buffer telemetry until the query timer has stopped. In particular,
        # Google Drive flush latency must not contaminate the latency profile.
        self.pending_events.append(
            {
                "schema_version": SCHEMA_VERSION,
                "timestamp": utc_now(),
                "run_id": self.run_id,
                "config_hash": self.config_hash,
                "phase": self.phase,
                "track": self.track,
                "variant": self.variant,
                "repeat": self.repeat,
                "seed": self.seed,
                "query_id": self.query_id,
                "event": event,
                **payload,
            }
        )

    def flush_events(self) -> None:
        for row in self.pending_events:
            self.events_writer.write(row)
        self.pending_events.clear()

    def add_stage(self, name: str, payload: dict[str, Any]) -> None:
        self.stages[name].append(payload)
        event_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"result", "raw_code", "raw_output"}
        }
        self.emit("stage", stage=name, **event_payload)

    def next_llm_seed(self) -> int:
        value = self.seed + self.llm_call_index * 100_003
        self.llm_call_index += 1
        return value

    def logical_duration(self) -> float:
        total = 0.0
        for entries in self.stages.values():
            for entry in entries:
                if entry.get("logical_called", entry.get("called", False)):
                    total += float(entry.get("logical_duration_s") or 0.0)
        return total


CURRENT_TRACE: contextvars.ContextVar[Optional[QueryTrace]] = contextvars.ContextVar(
    "paper_query_trace", default=None
)


def current_trace() -> Optional[QueryTrace]:
    return CURRENT_TRACE.get()


@contextlib.contextmanager
def trace_context(trace: QueryTrace) -> Iterator[None]:
    token = CURRENT_TRACE.set(trace)
    try:
        yield
    finally:
        CURRENT_TRACE.reset(token)


def loguru_sink(message: Any) -> None:
    trace = current_trace()
    if trace is None:
        return
    text = truncate(str(message).strip(), 2000)
    trace.component_logs.append(text)


@contextlib.contextmanager
def temporary_attr(obj: Any, name: str, value: Any) -> Iterator[None]:
    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


def stage_key(
    trace: QueryTrace, stage_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    return stable_hash(
        {
            "schema": SCHEMA_VERSION,
            "config_hash": trace.config_hash,
            "track": trace.track,
            "repeat": trace.repeat,
            "seed": trace.seed,
            "query_id": trace.query_id,
            "stage": stage_name,
            "args": args,
            "kwargs": kwargs,
        }
    )


class PaperReasonerMixin:
    """Instrumentation and ablation switches layered over LLMReasoner."""

    backend_name: str
    cache: StageCache
    llm_timeout: float

    def _record_public_method(
        self,
        stage_name: str,
        fn: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        allow_cache: bool = True,
    ) -> Any:
        trace = current_trace()
        if trace is None:
            return fn(*args, **kwargs)
        key = stage_key(trace, stage_name, args, kwargs)
        cached = trace.cache.get(key) if trace.cache_enabled and allow_cache else None
        if cached is not None and cached.get("status") != "ok":
            cached = None
        if cached is not None:
            trace.llm_call_index += int(cached.get("llm_calls_consumed", 1))
            payload = {
                "called": True,
                "logical_called": True,
                "physical_call": False,
                "cache_hit": True,
                "status": cached.get("status", "ok"),
                "wall_duration_s": 0.0,
                "logical_duration_s": cached.get("logical_duration_s", 0.0),
                "result": cached.get("result"),
            }
            trace.add_stage(stage_name, payload)
            return cached.get("result")

        started = time.perf_counter()
        llm_call_index_before = trace.llm_call_index
        infrastructure_before = trace.infrastructure_error
        status = "ok"
        error = None
        try:
            result = fn(*args, **kwargs)
            if result in (None, "", {}):
                status = "empty"
        except Exception as exc:
            result = None
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
            trace.infrastructure_error = error
        duration = time.perf_counter() - started
        llm_calls_consumed = trace.llm_call_index - llm_call_index_before
        infrastructure_during_call = (
            trace.infrastructure_error
            if trace.infrastructure_error != infrastructure_before
            else None
        )
        if infrastructure_during_call:
            status = "infrastructure_error"
            error = infrastructure_during_call
        payload = {
            "called": True,
            "logical_called": True,
            "physical_call": True,
            "cache_hit": False,
            "status": status,
            "wall_duration_s": duration,
            "logical_duration_s": duration,
            "error": error,
            "result": result,
            "llm_calls_consumed": llm_calls_consumed,
        }
        trace.add_stage(stage_name, payload)
        if (
            trace.cache_enabled
            and allow_cache
            and status == "ok"
            and result not in (None, "", {})
        ):
            trace.cache.put(
                key,
                {
                    "status": status,
                    "logical_duration_s": duration,
                    "result": result,
                    "llm_calls_consumed": llm_calls_consumed,
                },
            )
        return result

    def solve_with_cot(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        result = self._record_public_method(
            "t1_cot",
            functools.partial(super().solve_with_cot),  # type: ignore[misc]
            args,
            kwargs,
        )
        trace = current_trace()
        if trace is not None and isinstance(result, dict):
            trace.artifacts["cot_answer"] = result.get("answer")
            trace.artifacts["cot_premises_used"] = result.get("premises_used") or []
        return result or {}

    def generate_z3_code(self, *args: Any, **kwargs: Any) -> str:
        trace = current_trace()
        if trace is not None and not trace.flags.get("z3_enabled", True):
            trace.add_stage(
                "z3_codegen",
                {
                    "called": False,
                    "logical_called": False,
                    "physical_call": False,
                    "cache_hit": False,
                    "status": "disabled_by_variant",
                    "wall_duration_s": 0.0,
                    "logical_duration_s": 0.0,
                },
            )
            return ""
        result = self._record_public_method(
            "z3_codegen",
            functools.partial(super().generate_z3_code),  # type: ignore[misc]
            args,
            kwargs,
        )
        if trace is not None:
            trace.z3["called"] = True
            trace.z3["codegen_success"] = bool(result)
            trace.artifacts["z3_code"] = result or ""
            trace.z3["code_sha256"] = (
                hashlib.sha256(str(result).encode()).hexdigest() if result else None
            )
        return str(result or "")

    def refine_z3_code(self, *args: Any, **kwargs: Any) -> str:
        trace = current_trace()
        if trace is not None and not trace.flags.get("z3_repair_enabled", True):
            trace.add_stage(
                "z3_repair_codegen",
                {
                    "called": False,
                    "logical_called": False,
                    "physical_call": False,
                    "cache_hit": False,
                    "status": "disabled_by_variant",
                    "wall_duration_s": 0.0,
                    "logical_duration_s": 0.0,
                },
            )
            return ""
        result = self._record_public_method(
            "z3_repair_codegen",
            functools.partial(super().refine_z3_code),  # type: ignore[misc]
            args,
            kwargs,
            allow_cache=False,
        )
        if trace is not None:
            trace.z3["repair_triggered"] = True
            trace.z3["repair_codegen_success"] = bool(result)
            trace.artifacts["z3_repaired_code"] = result or ""
        return str(result or "")

    def parse_physics_question(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        result = self._record_public_method(
            "t2_llm_parse",
            functools.partial(super().parse_physics_question),  # type: ignore[misc]
            args,
            kwargs,
            allow_cache=False,
        )
        return result or {}

    def solve_physics_cot(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        result = self._record_public_method(
            "t2_cot",
            functools.partial(super().solve_physics_cot),  # type: ignore[misc]
            args,
            kwargs,
            allow_cache=True,
        )
        return result or {}

    def generate_sympy_code(self, *args: Any, **kwargs: Any) -> str:
        result = self._record_public_method(
            "pal_codegen",
            functools.partial(super().generate_sympy_code),  # type: ignore[misc]
            args,
            kwargs,
            allow_cache=True,
        )
        trace = current_trace()
        if trace is not None:
            trace.pal["called"] = True
            trace.pal["codegen_success"] = bool(result)
            trace.artifacts["pal_code"] = result or ""
            trace.pal["code_sha256"] = (
                hashlib.sha256(str(result).encode()).hexdigest() if result else None
            )
        return str(result or "")

    def refine_sympy_code(self, *args: Any, **kwargs: Any) -> str:
        result = self._record_public_method(
            "pal_repair_codegen",
            functools.partial(super().refine_sympy_code),  # type: ignore[misc]
            args,
            kwargs,
            allow_cache=False,
        )
        trace = current_trace()
        if trace is not None:
            trace.pal["repair_triggered"] = True
            trace.pal["repair_codegen_success"] = bool(result)
            trace.artifacts["pal_repaired_code"] = result or ""
        return str(result or "")

    def explain_physics(self, *args: Any, **kwargs: Any) -> str:
        result = self._record_public_method(
            "t2_explainer",
            functools.partial(super().explain_physics),  # type: ignore[misc]
            args,
            kwargs,
            allow_cache=False,
        )
        return str(result or "")


def build_reasoner_class() -> type:
    from llm.llm_reasoner import LLMReasoner

    class PaperReasoner(PaperReasonerMixin, LLMReasoner):
        def __init__(
            self,
            *,
            backend: str,
            api_base: str,
            api_key: str,
            model_name: str,
            model_revision: str,
            temperature: float,
            max_tokens: int,
            llm_timeout: float,
            quantization: str,
            cache: StageCache,
            logger: logging.Logger,
        ):
            super().__init__(
                api_base=api_base or "http://127.0.0.1:8001/v1",
                model_name=model_name,
                api_key=api_key or "not-needed",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.backend_name = backend
            self.model_revision = model_revision
            self.llm_timeout = llm_timeout
            self.quantization = quantization
            self.cache = cache
            self.paper_logger = logger
            self._local_model = None
            self._local_tokenizer = None
            self.resolved_model_revision = model_revision

        def _get_client(self) -> Any:
            if self._client is None:
                from openai import OpenAI

                self._client = OpenAI(
                    base_url=self.api_base,
                    api_key=self.api_key,
                    timeout=self.llm_timeout,
                    max_retries=0,
                )
            return self._client

        def check_server(self) -> bool:
            if self.backend_name == "transformers":
                return True
            return super().check_server()

        def _chat(
            self,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int = 512,
            temperature: Optional[float] = None,
        ) -> str:
            trace = current_trace()
            call_seed = trace.next_llm_seed() if trace is not None else DEFAULT_SEEDS[0]
            temp = self.temperature if temperature is None else temperature
            max_tokens = min(int(max_tokens), int(self.max_tokens))
            started = time.perf_counter()
            call: dict[str, Any] = {
                "backend": self.backend_name,
                "seed": call_seed,
                "temperature": temp,
                "max_tokens": max_tokens,
                "prompt_chars": len(system_prompt) + len(user_prompt),
                "model": self.model_name,
            }
            try:
                if self.backend_name == "openai":
                    text, usage = self._chat_openai(
                        system_prompt,
                        user_prompt,
                        max_tokens,
                        temp,
                        call_seed,
                    )
                else:
                    text, usage = self._chat_transformers(
                        system_prompt,
                        user_prompt,
                        max_tokens,
                        temp,
                        call_seed,
                    )
                call.update(usage)
                call["status"] = "ok" if text else "empty"
                call["output_chars"] = len(text)
                return text
            except Exception as exc:
                call["status"] = "error"
                call["error"] = f"{type(exc).__name__}: {exc}"
                if trace is not None:
                    trace.infrastructure_error = call["error"]
                self.paper_logger.error("LLM call failed: %s", call["error"])
                return ""
            finally:
                call["duration_s"] = time.perf_counter() - started
                if trace is not None:
                    trace.llm_calls.append(call)
                    trace.emit("llm_call", **call)

        def _chat_openai(
            self,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int,
            temperature: float,
            seed: int,
        ) -> tuple[str, dict[str, Any]]:
            client = self._get_client()
            request_kwargs = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "seed": seed,
                "timeout": self.llm_timeout,
            }
            seed_supported = True
            try:
                response = client.chat.completions.create(**request_kwargs)
            except Exception as exc:
                if "seed" not in str(exc).lower():
                    raise
                seed_supported = False
                request_kwargs.pop("seed", None)
                response = client.chat.completions.create(**request_kwargs)
            text = (response.choices[0].message.content or "").strip()
            usage_obj = getattr(response, "usage", None)
            usage = {
                "finish_reason": getattr(response.choices[0], "finish_reason", None),
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
                "completion_tokens": getattr(usage_obj, "completion_tokens", None),
                "total_tokens": getattr(usage_obj, "total_tokens", None),
                "seed_supported": seed_supported,
            }
            return text, usage

        def _load_local_model(self) -> None:
            if self._local_model is not None:
                return
            import torch
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )

            if not torch.cuda.is_available():
                raise RuntimeError(
                    "Local Qwen full run requires a CUDA GPU. Use --api-base for "
                    "an external OpenAI-compatible endpoint or run --mode dry-run."
                )
            quantization_config = None
            if self.quantization == "4bit":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
            elif self.quantization == "8bit":
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)

            self.paper_logger.info(
                "Loading %s revision=%s quantization=%s",
                self.model_name,
                self.model_revision,
                self.quantization,
            )
            self._local_tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                revision=self.model_revision,
                trust_remote_code=False,
            )
            kwargs: dict[str, Any] = {
                "revision": self.model_revision,
                "device_map": "auto",
                "trust_remote_code": False,
                "low_cpu_mem_usage": True,
            }
            if quantization_config is not None:
                kwargs["quantization_config"] = quantization_config
            else:
                kwargs["torch_dtype"] = torch.float16
            self._local_model = AutoModelForCausalLM.from_pretrained(
                self.model_name, **kwargs
            )
            self._local_model.eval()
            resolved = getattr(self._local_model.config, "_commit_hash", None)
            if resolved:
                self.resolved_model_revision = str(resolved)

        def _chat_transformers(
            self,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int,
            temperature: float,
            seed: int,
        ) -> tuple[str, dict[str, Any]]:
            self._load_local_model()
            import torch

            assert self._local_tokenizer is not None
            assert self._local_model is not None
            tokenizer = self._local_tokenizer
            model = self._local_model
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(rendered, return_tensors="pt")
            device = next(model.parameters()).device
            inputs = {key: value.to(device) for key, value in inputs.items()}
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            do_sample = temperature > 0
            generation_kwargs: dict[str, Any] = {
                "max_new_tokens": max_tokens,
                # Transformers checks this between decoding iterations. This is
                # a soft generation deadline, unlike the endpoint hard timeout.
                "max_time": self.llm_timeout,
                "do_sample": do_sample,
                "pad_token_id": tokenizer.eos_token_id,
                "eos_token_id": tokenizer.eos_token_id,
            }
            if do_sample:
                generation_kwargs.update(
                    {"temperature": max(temperature, 1e-5), "top_p": 0.95}
                )
            with torch.inference_mode():
                output = model.generate(**inputs, **generation_kwargs)
            input_tokens = int(inputs["input_ids"].shape[-1])
            generated = output[0, input_tokens:]
            text = tokenizer.decode(generated, skip_special_tokens=True).strip()
            return text, {
                "prompt_tokens": input_tokens,
                "completion_tokens": int(generated.shape[-1]),
                "total_tokens": input_tokens + int(generated.shape[-1]),
                "finish_reason": "stop_or_length",
            }

    return PaperReasoner


def scrubbed_child_env(repo_root: Path) -> dict[str, str]:
    import site

    dependency_paths: list[str] = [str(repo_root)]
    candidates: list[str] = []
    try:
        candidates.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        candidates.append(site.getusersitepackages())
    except Exception:
        pass
    candidates.extend(
        value
        for value in sys.path
        if "site-packages" in value or "dist-packages" in value
    )
    for candidate in candidates:
        if candidate and candidate not in dependency_paths:
            dependency_paths.append(candidate)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.pathsep.join(dependency_paths),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    return env


def child_limits(timeout: float) -> None:
    try:
        import resource

        cpu_seconds = max(1, math.ceil(timeout) + 1)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except Exception:
        pass


Z3_DENIED_NAMES = {
    "open",
    "eval",
    "exec",
    "compile",
    "input",
    "__import__",
    "breakpoint",
    "help",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "os",
    "sys",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "pathlib",
    "shutil",
    "pickle",
    "marshal",
    "ctypes",
}


def validate_generated_z3(code: str) -> Optional[str]:
    if not code or len(code) > 20_000:
        return "empty_or_oversized_code"
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"syntax_error:{exc.msg}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name != "z3" for alias in node.names):
                return "disallowed_import"
        elif isinstance(node, ast.ImportFrom):
            if node.module != "z3":
                return "disallowed_import"
        elif isinstance(node, ast.Name):
            if node.id in Z3_DENIED_NAMES or (
                node.id.startswith("__") and node.id != "__name__"
            ):
                return f"disallowed_name:{node.id}"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return f"disallowed_attribute:{node.attr}"
    return None


Z3_CHILD = r"""
import json
import sys
from pipeline.type1.z3_solver import execute_z3_code
try:
    value = execute_z3_code(sys.stdin.read())
    print(json.dumps({"ok": value is not None and value != "", "output": value}))
except BaseException as exc:
    print(json.dumps({"ok": False, "output": None,
                      "error": type(exc).__name__ + ": " + str(exc)}))
"""


PAL_CHILD = r"""
import json
import sys
from pipeline.type2.sympy_solver import _run_pal_code
try:
    value = _run_pal_code(sys.stdin.read())
    print(json.dumps({"ok": bool(value and value.get("answer") not in (None, "")),
                      "result": value}))
except BaseException as exc:
    print(json.dumps({"ok": False, "result": None,
                      "error": type(exc).__name__ + ": " + str(exc)}))
"""


def run_code_child(
    repo_root: Path,
    child_program: str,
    code: str,
    timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-c", child_program],
            cwd=repo_root,
            env=scrubbed_child_env(repo_root),
            input=code,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            preexec_fn=(
                functools.partial(child_limits, timeout)
                if os.name == "posix"
                else None
            ),
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "timeout": True,
            "error": f"hard_timeout_after_{timeout}s",
            "duration_s": time.perf_counter() - started,
        }
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    parsed: dict[str, Any]
    try:
        parsed = json.loads(lines[-1]) if lines else {}
    except json.JSONDecodeError:
        parsed = {}
    parsed.update(
        {
            "returncode": result.returncode,
            "timeout": False,
            "duration_s": time.perf_counter() - started,
            "stderr": truncate(result.stderr, 4000),
        }
    )
    if not parsed.get("ok") and not parsed.get("error"):
        parsed["error"] = (
            f"child_returncode_{result.returncode}"
            if result.returncode
            else "empty_or_unparseable_child_output"
        )
    return parsed


def safe_z3_execute(
    repo_root: Path, code: str, timeout: float, cache: Optional[StageCache] = None
) -> Optional[str]:
    trace = current_trace()
    attempt = (
        len(trace.z3.setdefault("executions", [])) + 1 if trace is not None else 1
    )
    rejection = validate_generated_z3(code)
    if rejection:
        result = {
            "attempt": attempt,
            "ok": False,
            "timeout": False,
            "error": rejection,
            "duration_s": 0.0,
            "cache_hit": False,
            "physical_call": False,
        }
    else:
        key = stable_hash(
            {
                "kind": "z3_execution",
                "config_hash": trace.config_hash if trace else None,
                "repeat": trace.repeat if trace else 0,
                "code": code,
                "timeout": timeout,
            }
        )
        cached = (
            cache.get(key)
            if cache is not None and trace is not None and trace.cache_enabled
            else None
        )
        if cached:
            child = dict(cached.get("result") or {})
            child["cache_hit"] = True
            child["physical_call"] = False
        else:
            child = run_code_child(repo_root, Z3_CHILD, code, timeout)
            child["cache_hit"] = False
            child["physical_call"] = True
            if cache is not None and trace is not None and trace.cache_enabled:
                cache.put(
                    key,
                    {
                        "status": "ok" if child.get("ok") else "failed",
                        "logical_duration_s": child.get("duration_s", 0.0),
                        "result": child,
                    },
                )
        result = {"attempt": attempt, **child}
    if trace is not None:
        trace.z3.setdefault("executions", []).append(result)
        trace.add_stage(
            "z3_execute",
            {
                "called": True,
                "logical_called": True,
                "physical_call": result.get("physical_call", not result.get("cache_hit")),
                "cache_hit": result.get("cache_hit", False),
                "status": "ok" if result.get("ok") else "failed",
                "wall_duration_s": (
                    0.0 if result.get("cache_hit") else result.get("duration_s", 0.0)
                ),
                "logical_duration_s": result.get("duration_s", 0.0),
                "attempt": attempt,
                "timeout": result.get("timeout", False),
                "error": result.get("error"),
                "raw_output": result.get("output"),
            },
        )
    # Preserve the production distinction: None triggers Z3 repair, while empty
    # stdout does not. Telemetry still marks empty stdout as execution failure.
    if "output" in result and result.get("output") is not None:
        return str(result.get("output"))
    return None


def safe_pal_execute(
    repo_root: Path,
    code: str,
    timeout: float,
    *,
    return_error: bool = False,
) -> Any:
    trace = current_trace()
    attempt = (
        len(trace.pal.setdefault("executions", [])) + 1 if trace is not None else 1
    )
    if not code or len(code) > 4000:
        child = {
            "ok": False,
            "timeout": False,
            "error": "empty_or_oversized_code",
            "duration_s": 0.0,
            "physical_call": False,
        }
    else:
        from pipeline.type2.sympy_solver import _PAL_FORBIDDEN

        lowered = code.lower()
        forbidden = next((token for token in _PAL_FORBIDDEN if token in lowered), None)
        if forbidden:
            child = {
                "ok": False,
                "timeout": False,
                "error": f"forbidden_token:{forbidden}",
                "duration_s": 0.0,
                "physical_call": False,
            }
        else:
            child = run_code_child(repo_root, PAL_CHILD, code, timeout)
            child["physical_call"] = True
    result = {"attempt": attempt, **child}
    if trace is not None:
        trace.pal.setdefault("executions", []).append(result)
        trace.add_stage(
            "pal_execute",
            {
                "called": True,
                "logical_called": True,
                "physical_call": result.get("physical_call", False),
                "cache_hit": False,
                "status": "ok" if result.get("ok") else "failed",
                "wall_duration_s": result.get("duration_s", 0.0),
                "logical_duration_s": result.get("duration_s", 0.0),
                "attempt": attempt,
                "timeout": result.get("timeout", False),
                "error": result.get("error"),
                "result": result.get("result"),
            },
        )
    value = result.get("result") if result.get("ok") else None
    return (value, result.get("error")) if return_error else value


@contextlib.contextmanager
def timed_stage(
    trace: QueryTrace,
    name: str,
    *,
    details: Optional[dict[str, Any]] = None,
) -> Iterator[dict[str, Any]]:
    payload: dict[str, Any] = {
        "called": True,
        "logical_called": True,
        "physical_call": True,
        "cache_hit": False,
        **(details or {}),
    }
    started = time.perf_counter()
    try:
        yield payload
        payload.setdefault("status", "ok")
    except Exception as exc:
        payload["status"] = "error"
        payload["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        duration = time.perf_counter() - started
        payload["wall_duration_s"] = duration
        payload["logical_duration_s"] = duration
        trace.add_stage(name, payload)


def install_reasoner_hooks(reasoner: Any, logger: logging.Logger) -> Callable[[], None]:
    """Point every runtime LLM seam at the paper-owned reasoner."""
    import llm
    import llm.llm_reasoner as reasoner_module
    from loguru import logger as loguru_logger

    originals = {
        "get_shared_reasoner": llm.get_shared_reasoner,
        "llm_server_available": llm.llm_server_available,
        "select_exemplars": reasoner_module.select_exemplars,
    }
    llm.get_shared_reasoner = lambda: reasoner
    llm.llm_server_available = lambda: True

    def instrumented_select_exemplars(*args: Any, **kwargs: Any) -> Any:
        trace = current_trace()
        started = time.perf_counter()
        try:
            selected = originals["select_exemplars"](*args, **kwargs)
            if trace is not None:
                trace.artifacts["z3_exemplars"] = [
                    {
                        key: value
                        for key, value in exemplar.items()
                        if key in {"id", "tags", "question_type", "pattern", "name"}
                    }
                    for exemplar in (selected or [])
                    if isinstance(exemplar, dict)
                ]
            return selected
        finally:
            if trace is not None:
                duration = time.perf_counter() - started
                trace.add_stage(
                    "z3_exemplar_retrieval",
                    {
                        "called": True,
                        "logical_called": True,
                        "physical_call": True,
                        "cache_hit": False,
                        "status": "ok",
                        "wall_duration_s": duration,
                        "logical_duration_s": duration,
                    },
                )

    reasoner_module.select_exemplars = instrumented_select_exemplars
    sink_id = loguru_logger.add(loguru_sink, level="DEBUG")
    logger.debug("Installed paper-owned LLM and Loguru telemetry hooks.")

    def restore() -> None:
        llm.get_shared_reasoner = originals["get_shared_reasoner"]
        llm.llm_server_available = originals["llm_server_available"]
        reasoner_module.select_exemplars = originals["select_exemplars"]
        loguru_logger.remove(sink_id)

    return restore


def classify_z3_outcome(trace: QueryTrace, response: dict[str, Any]) -> None:
    explanation = str(response.get("explanation") or "")
    final_answer = normalize_logic_answer(response.get("answer"))
    cot_answer = normalize_logic_answer(trace.artifacts.get("cot_answer"))
    executions = trace.z3.get("executions") or []
    last_output = str(executions[-1].get("output") or "") if executions else ""
    formal_marker = "[Formal Verification]" in explanation
    logs = "\n".join(trace.component_logs)
    decision = "not_available"
    if "Z3 OVERRIDES CoT" in logs or "Z3 override:" in explanation:
        decision = "override"
    elif formal_marker and not cot_answer:
        decision = "fill_empty"
    elif formal_marker and final_answer == cot_answer:
        decision = "agree"
    elif "logical insufficiency detected" in logs:
        decision = "logical_insufficiency_override"
    elif "type mismatch" in logs:
        decision = "rejected_type"
    elif "fallback (no proof)" in logs:
        decision = "rejected_no_proof"
    elif "Goal hallucination detected" in logs:
        decision = "rejected_goal_hallucination"
    elif "Z3=Unknown, keeping CoT" in logs:
        decision = "rejected_unknown"
    elif trace.z3.get("called") and executions:
        decision = "not_accepted"
    elif trace.z3.get("called"):
        decision = "codegen_or_execution_failed"

    accepted = formal_marker or decision == "logical_insufficiency_override"
    trace.z3.update(
        {
            "decision": decision,
            "final_accepted": accepted,
            "affected_final_answer": bool(cot_answer and final_answer != cot_answer),
            "cot_answer": cot_answer,
            "final_answer": final_answer,
            "last_output": last_output,
            "first_execution_success": bool(
                executions and executions[0].get("ok")
            ),
            "repair_execution_success": bool(
                len(executions) > 1 and executions[-1].get("ok")
            ),
        }
    )
    if not trace.z3.get("called"):
        failure = "not_called"
    elif not trace.z3.get("codegen_success"):
        failure = "empty_codegen"
    elif not executions:
        failure = "executor_not_called"
    elif not executions[0].get("ok") and len(executions) == 1:
        failure = executions[0].get("error") or "first_execution_failed"
    elif trace.z3.get("repair_triggered") and not trace.z3.get(
        "repair_execution_success"
    ):
        failure = (
            executions[-1].get("error") if executions else "repair_execution_failed"
        )
    elif not accepted:
        failure = decision
    else:
        failure = None
    trace.z3["failure_reason"] = failure


def run_type1_pipeline(
    repo_root: Path,
    example: PublicExample,
    variant: str,
    trace: QueryTrace,
    cache: StageCache,
    code_timeout: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from api.main import _run_type1_pipeline
    from api.schemas import UnifiedRequest
    import pipeline.type1.z3_solver as z3_solver_module

    trace.flags.update(
        {
            "z3_enabled": variant != "t1_cot_only",
            "z3_repair_enabled": variant == "t1_full",
            "z3_eligible": bool(example.metadata.get("z3_eligible")),
        }
    )

    def patched_execute(code: str, timeout_sec: int = 30) -> Optional[str]:
        del timeout_sec
        return safe_z3_execute(repo_root, code, code_timeout, cache)

    request = UnifiedRequest(
        query_id=example.query_id,
        type="type1",
        query=example.question,
        premises=example.premises,
        options=example.options,
        logs=False,
    )
    started = time.perf_counter()
    with temporary_attr(z3_solver_module, "execute_z3_code", patched_execute):
        response_obj = _run_type1_pipeline(request)
    wall_duration = time.perf_counter() - started
    response = response_obj.model_dump()
    classify_z3_outcome(trace, response)
    scores = score_type1(
        response.get("answer"),
        response.get("premises_used") or [],
        example.gold_answer,
        example.gold_premises,
    )
    trace.z3["task_correct"] = scores["answer_correct"]
    trace.z3["task_correct_among_accepted"] = bool(
        trace.z3.get("final_accepted") and scores["answer_correct"]
    )
    trace.z3["helpful_override"] = bool(
        trace.z3.get("final_accepted")
        and trace.z3.get("affected_final_answer")
        and not (
            normalize_logic_answer(trace.artifacts.get("cot_answer"))
            == normalize_logic_answer(example.gold_answer)
        )
        and scores["answer_correct"]
    )
    trace.z3["harmful_override"] = bool(
        trace.z3.get("final_accepted")
        and trace.z3.get("affected_final_answer")
        and (
            normalize_logic_answer(trace.artifacts.get("cot_answer"))
            == normalize_logic_answer(example.gold_answer)
        )
        and not scores["answer_correct"]
    )
    timing = {
        "wall_duration_s": wall_duration,
        "logical_stage_duration_s": trace.logical_duration(),
        "answer_ready_duration_s": wall_duration,
    }
    return response, {**scores, **timing}


def initial_type2_state(example: PublicExample) -> dict[str, Any]:
    return {
        "question": example.question,
        "query_id": example.query_id,
        "options": [],
        "premises": [],
        "query_type": "type2",
        "fol_translation": None,
        "fol_valid": None,
        "z3_result": None,
        "parsed_physics": None,
        "sympy_result": None,
        "cot": None,
        "answer": None,
        "explanation": None,
        "confidence": 1.0,
        "solver_result": None,
        "fol_retries": 0,
    }


def run_type2_parser(
    state: dict[str, Any], use_llm: bool, trace: QueryTrace
) -> dict[str, Any]:
    import pipeline.type2.physics_parser as parser_module

    with timed_stage(trace, "t2_parser", details={"llm_augment": use_llm}) as stage:
        with temporary_attr(
            parser_module, "llm_server_available", lambda: bool(use_llm)
        ):
            result = parser_module.physics_parser_node(state)
        parsed = result.get("parsed_physics") or {}
        stage.update(
            {
                "domain": parsed.get("domain"),
                "question_type": parsed.get("question_type"),
                "find": parsed.get("find"),
                "given_keys": sorted((parsed.get("given") or {}).keys()),
                "phrasal_used": bool(parsed.get("_phrasal_used")),
            }
        )
        trace.artifacts["parsed_physics"] = parsed
        return result


def run_type2_rag(state: dict[str, Any], trace: QueryTrace) -> dict[str, Any]:
    from pipeline.type2.formula_rag import formula_rag_node

    with timed_stage(trace, "t2_formula_rag") as stage:
        result = formula_rag_node(state)
        parsed = result.get("parsed_physics") or {}
        formula_doc = parsed.get("_formula_doc") or {}
        formulas = parsed.get("formulas") or []
        stage.update(
            {
                "failed": bool(result.get("_formula_rag_failed")),
                "formula_id": formula_doc.get("id"),
                "topic": formula_doc.get("topic"),
                "domain": formula_doc.get("domain"),
                "chain_length": len(formulas),
            }
        )
        trace.artifacts["formula"] = {
            "id": formula_doc.get("id"),
            "topic": formula_doc.get("topic"),
            "domain": formula_doc.get("domain"),
            "formulas": formulas,
        }
        return result


def deterministic_type2_solve(
    state: dict[str, Any], trace: QueryTrace
) -> dict[str, Any]:
    from pipeline.type2.type2_classifier import PhysicsQuestionType
    from pipeline.type2.sympy_solver import _solve_resonance_zr, solve_physics

    parsed = state.get("parsed_physics") or {}
    question = state.get("question") or ""
    q_type_text = parsed.get(
        "question_type", PhysicsQuestionType.SINGLE_FORMULA.value
    )
    try:
        q_type = PhysicsQuestionType(q_type_text)
    except ValueError:
        q_type = PhysicsQuestionType.SINGLE_FORMULA
    given = parsed.get("given") or {}
    result: Optional[dict[str, Any]] = None
    attempted: list[str] = []

    with timed_stage(trace, "t2_deterministic_solver") as stage:
        attempted.append("resonance_z_equals_r")
        result = _solve_resonance_zr(parsed, question)
        if result is None and (
            q_type == PhysicsQuestionType.YES_NO
            and parsed.get("domain") == "ac_circuits"
            and all(key in given for key in ("L", "C", "f"))
        ):
            attempted.append("resonance")
            from pipeline.type2.resonance_solver import solve_resonance

            result = solve_resonance(parsed, question)
        elif result is None and q_type in (
            PhysicsQuestionType.ERROR_CALC,
            PhysicsQuestionType.MULTI_ANSWER,
        ):
            attempted.append("error")
            from pipeline.type2.error_solver import solve_error

            result = solve_error(parsed, question)
        elif result is None:
            if q_type == PhysicsQuestionType.YES_NO:
                q_type = PhysicsQuestionType.SINGLE_FORMULA
            if parsed.get("domain") == "circuits":
                attempted.append("circuit")
                from pipeline.type2.circuit_solver import solve_circuit

                result = solve_circuit(parsed, question)
            if result is None:
                attempted.append("sympy")
                result = solve_physics(parsed, q_type)

        if not result:
            result = {
                "answer": "",
                "unit": "",
                "steps": [],
                "source": "llm_fallback",
            }
        if result.get("source") == "llm_fallback":
            attempted.append("vector")
            from pipeline.type2.vector_solver import solve_vector_problem

            vector_result = solve_vector_problem(state)
            if vector_result:
                result = vector_result

        stage.update(
            {
                "attempted_strategies": attempted,
                "source": result.get("source"),
                "returned_answer": result.get("answer") not in (None, ""),
            }
        )
        trace.artifacts["deterministic_attempts"] = attempted
        return result


def pal_fallback(
    repo_root: Path,
    state: dict[str, Any],
    parsed: dict[str, Any],
    reasoner: Any,
    *,
    repair_enabled: bool,
    cot_enabled: bool,
    code_timeout: float,
) -> Optional[dict[str, Any]]:
    trace = current_trace()
    assert trace is not None
    question = state.get("question") or ""
    given = parsed.get("given") or {}
    find = parsed.get("find") or ""
    formulas = parsed.get("formulas") or []

    code = reasoner.generate_sympy_code(question, given, find, formulas)
    pal, error = safe_pal_execute(
        repo_root, code, code_timeout, return_error=True
    )
    if pal and pal.get("answer") not in (None, ""):
        trace.pal["first_execution_success"] = True
        trace.pal["final_accepted"] = True
        trace.pal["final_source"] = "llm_pal"
        return {
            "answer": pal["answer"],
            "unit": pal.get("unit") or "",
            "steps": [code],
            "source": "llm_pal",
        }
    trace.pal["first_execution_success"] = False

    if repair_enabled:
        code2 = reasoner.refine_sympy_code(
            code, error or "", question, given, find
        )
        if code2 and code2 != code:
            pal2 = safe_pal_execute(repo_root, code2, code_timeout)
            if pal2 and pal2.get("answer") not in (None, ""):
                trace.pal["repair_execution_success"] = True
                trace.pal["final_accepted"] = True
                trace.pal["final_source"] = "llm_pal"
                return {
                    "answer": pal2["answer"],
                    "unit": pal2.get("unit") or "",
                    "steps": [code2],
                    "source": "llm_pal",
                }
        trace.pal["repair_execution_success"] = False

    executions = trace.pal.get("executions") or []
    if not trace.pal.get("codegen_success"):
        trace.pal["failure_reason"] = "empty_codegen"
    elif executions:
        trace.pal["failure_reason"] = (
            executions[-1].get("error") or "execution_not_accepted"
        )
    else:
        trace.pal["failure_reason"] = "executor_not_called"

    if cot_enabled:
        cot = reasoner.solve_physics_cot(question, given, find, formulas)
        if cot and cot.get("answer") not in (None, ""):
            trace.pal["final_accepted"] = False
            trace.pal["final_source"] = "llm_cot"
            return cot

    trace.pal["final_accepted"] = False
    trace.pal["final_source"] = "none"
    return None


def type2_result_to_state(
    state: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    source = result.get("source", "llm_fallback")
    confidence = float(state.get("confidence", 1.0))
    if source in {"llm_fallback", "llm_cot"}:
        confidence = min(confidence, 0.5)
    elif source == "llm_pal":
        confidence = min(confidence, 0.6)
    solver_result = {
        "answer": result.get("answer") or "",
        "unit": result.get("unit") or "",
        "steps": result.get("steps") or [],
        "fol": None,
        "source": source,
        "confidence": confidence,
    }
    return {
        **state,
        "sympy_result": result,
        "solver_result": solver_result,
        "answer": result.get("answer") or "",
        "confidence": confidence,
    }


def run_type2_pipeline(
    repo_root: Path,
    example: PublicExample,
    variant: str,
    trace: QueryTrace,
    reasoner: Any,
    code_timeout: float,
    *,
    include_explainer: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from api.main import _snap_and_convert
    from api.response_builder import build_response
    from pipeline.type2.cot_builder import cot_builder_node
    from pipeline.type2.type2_validation import validate_sympy_result

    pipeline_variant = "t2_full" if variant == "t2_full_e2e" else variant
    state = initial_type2_state(example)
    started = time.perf_counter()

    if pipeline_variant == "t2_cot_only":
        trace.flags["pal_eligible"] = False
        result = reasoner.solve_physics_cot(example.question, {}, "", [])
        if not result:
            result = {
                "answer": "",
                "unit": "",
                "steps": [],
                "source": "llm_cot",
            }
        state = type2_result_to_state(state, result)
        trace.artifacts["parsed_physics"] = {}
        trace.artifacts["formula"] = {}
    else:
        use_llm_parser = pipeline_variant == "t2_full"
        state = run_type2_parser(state, use_llm_parser, trace)
        state = run_type2_rag(state, trace)
        parsed = state.get("parsed_physics") or {}
        result = deterministic_type2_solve(state, trace)
        needs_fallback = result.get("source") == "llm_fallback"

        # Preserve the production phrasal-value safety gate for the full variant.
        if (
            pipeline_variant == "t2_full"
            and not needs_fallback
            and parsed.get("_phrasal_used")
            and result.get("source") in {"sympy", "circuit"}
        ):
            try:
                validation = validate_sympy_result(
                    result.get("answer") or None, parsed.get("find")
                )
                needs_fallback = bool(validation and not validation.is_valid)
            except Exception:
                needs_fallback = False
        trace.flags["pal_eligible"] = bool(needs_fallback)

        if needs_fallback and pipeline_variant in {"t2_rag_solver_pal", "t2_full"}:
            pal_result = pal_fallback(
                repo_root,
                state,
                parsed,
                reasoner,
                repair_enabled=pipeline_variant == "t2_full",
                cot_enabled=pipeline_variant == "t2_full",
                code_timeout=code_timeout,
            )
            if pal_result:
                result = pal_result
        state = type2_result_to_state(state, result)

    answer_ready_duration = time.perf_counter() - started
    parsed = state.get("parsed_physics") or {}
    result = state.get("sympy_result") or {}

    with timed_stage(trace, "t2_validation") as validation_stage:
        try:
            if result.get("source") in {"resonance", "error_calc"}:
                validation = None
            else:
                validation = validate_sympy_result(
                    result.get("answer") or None, parsed.get("find")
                )
            validation_stage["valid"] = (
                validation.is_valid if validation is not None else None
            )
            validation_stage["errors"] = (
                validation.errors if validation is not None else []
            )
        except Exception as exc:
            validation_stage["status"] = "skipped"
            validation_stage["error"] = f"{type(exc).__name__}: {exc}"

    with timed_stage(trace, "t2_cot_builder"):
        state = cot_builder_node(state)

    raw_answer = state.get("answer") or ""
    raw_unit = (state.get("solver_result") or {}).get("unit") or ""
    explanation = f"The answer is {raw_answer} {raw_unit}".strip() + "."
    if include_explainer:
        explanation = reasoner.explain_physics(
            example.question,
            str(raw_answer),
            str(raw_unit),
            (state.get("solver_result") or {}).get("steps") or [],
        )

    with timed_stage(trace, "t2_postprocess") as post_stage:
        answer, unit = _snap_and_convert(
            raw_answer,
            raw_unit,
            example.question,
            parsed.get("find", ""),
        )
        response_obj = build_response(
            query_id=example.query_id,
            query_type="type2",
            answer=answer,
            explanation=explanation,
            raw_unit=unit,
            steps=state.get("cot") or [],
            premises_used=[],
        )
        response = response_obj.model_dump()
        post_stage.update(
            {
                "raw_answer": raw_answer,
                "raw_unit": raw_unit,
                "normalized_answer": response.get("answer"),
                "normalized_unit": response.get("unit"),
            }
        )

    wall_duration = time.perf_counter() - started
    scores = score_type2(
        response.get("answer"),
        response.get("unit"),
        example.gold_answer,
        example.gold_unit,
    )
    source = (state.get("solver_result") or {}).get("source", "llm_fallback")
    trace.artifacts["solver_source"] = source
    trace.pal["task_correct"] = scores["strict_correct"]
    trace.pal["task_correct_among_accepted"] = bool(
        trace.pal.get("final_accepted") and scores["strict_correct"]
    )
    timing = {
        "wall_duration_s": wall_duration,
        "logical_stage_duration_s": trace.logical_duration(),
        "answer_ready_duration_s": answer_ready_duration,
        "presentation_duration_s": wall_duration,
    }
    return response, {**scores, **timing, "solver_source": source}


def public_input_payload(example: PublicExample) -> dict[str, Any]:
    return {
        "question": example.question,
        "premises": example.premises,
        "options": example.options,
        "question_sha256": hashlib.sha256(
            example.question.encode("utf-8")
        ).hexdigest(),
        "metadata": example.metadata,
    }


def result_record(
    trace: QueryTrace,
    example: PublicExample,
    response: Optional[dict[str, Any]],
    scores: Optional[dict[str, Any]],
    *,
    status: str,
    error: Optional[str],
    attempt: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": utc_now(),
        "run_id": trace.run_id,
        "config_hash": trace.config_hash,
        "phase": trace.phase,
        "track": trace.track,
        "variant": trace.variant,
        "repeat": trace.repeat,
        "seed": trace.seed,
        "query_id": trace.query_id,
        "dataset_source": (
            "Logic_Based_Educational_Queries.json"
            if trace.track == "type1"
            else "data/physics/physics_dev.csv"
        ),
        "status": status,
        "attempt": attempt,
        "error": error,
        "input": public_input_payload(example),
        "gold": {
            "answer": example.gold_answer,
            "unit": example.gold_unit,
            "premises_used": example.gold_premises,
        },
        "response": response,
        "scores": scores,
        "stages": dict(trace.stages),
        "llm_calls": trace.llm_calls,
        "flags": trace.flags,
        "z3": trace.z3,
        "pal": trace.pal,
        "artifacts": trace.artifacts,
        "component_logs": trace.component_logs,
    }


def completion_key(
    config_hash: str,
    phase: str,
    variant: str,
    repeat: int,
    query_id: str,
) -> tuple[str, str, str, int, str]:
    return config_hash, phase, variant, repeat, query_id


STOP_REQUESTED = False


def install_signal_handlers(logger: logging.Logger) -> None:
    def handler(signum: int, frame: Any) -> None:
        del frame
        global STOP_REQUESTED
        STOP_REQUESTED = True
        logger.warning(
            "Signal %s received; the runner will stop after the current query.",
            signum,
        )

    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), handler)


def run_one_query(
    *,
    repo_root: Path,
    run_id: str,
    config_hash: str,
    phase: str,
    example: PublicExample,
    variant: str,
    repeat: int,
    seed: int,
    reasoner: Any,
    cache: StageCache,
    cache_enabled: bool,
    code_timeout: float,
    include_explainer: bool,
    events_writer: JsonlWriter,
    errors_writer: JsonlWriter,
    logger: logging.Logger,
    max_retries: int,
) -> dict[str, Any]:
    final_record: Optional[dict[str, Any]] = None
    for attempt in range(1, max_retries + 2):
        trace = QueryTrace(
            run_id=run_id,
            config_hash=config_hash,
            phase=phase,
            track=example.track,
            variant=variant,
            repeat=repeat,
            seed=seed,
            query_id=example.query_id,
            events_writer=events_writer,
            cache=cache,
            cache_enabled=cache_enabled,
            code_timeout=code_timeout,
        )
        trace.emit("query_started", attempt=attempt)
        try:
            with trace_context(trace):
                if example.track == "type1":
                    response, scores = run_type1_pipeline(
                        repo_root,
                        example,
                        variant,
                        trace,
                        cache,
                        code_timeout,
                    )
                else:
                    response, scores = run_type2_pipeline(
                        repo_root,
                        example,
                        variant,
                        trace,
                        reasoner,
                        code_timeout,
                        include_explainer=include_explainer,
                    )
            if trace.infrastructure_error and attempt <= max_retries:
                trace.emit(
                    "query_retry",
                    attempt=attempt,
                    error=trace.infrastructure_error,
                )
                trace.flush_events()
                errors_writer.write(
                    {
                        "timestamp": utc_now(),
                        "run_id": run_id,
                        "phase": phase,
                        "variant": variant,
                        "repeat": repeat,
                        "query_id": example.query_id,
                        "attempt": attempt,
                        "kind": "infrastructure_retry",
                        "error": trace.infrastructure_error,
                    }
                )
                logger.warning(
                    "Retrying %s/%s after LLM infrastructure error: %s",
                    variant,
                    example.query_id,
                    trace.infrastructure_error,
                )
                continue
            if trace.infrastructure_error:
                final_record = result_record(
                    trace,
                    example,
                    response,
                    scores,
                    status="infrastructure_failed",
                    error=trace.infrastructure_error,
                    attempt=attempt,
                )
                trace.emit(
                    "query_failed",
                    attempt=attempt,
                    kind="infrastructure",
                    error=trace.infrastructure_error,
                )
                trace.flush_events()
                break
            final_record = result_record(
                trace,
                example,
                response,
                scores,
                status="completed",
                error=trace.infrastructure_error,
                attempt=attempt,
            )
            trace.emit(
                "query_completed",
                attempt=attempt,
                wall_duration_s=scores.get("wall_duration_s"),
            )
            trace.flush_events()
            break
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            stack = traceback.format_exc()
            errors_writer.write(
                {
                    "timestamp": utc_now(),
                    "run_id": run_id,
                    "phase": phase,
                    "variant": variant,
                    "repeat": repeat,
                    "query_id": example.query_id,
                    "attempt": attempt,
                    "kind": "query_exception",
                    "error": error,
                    "traceback": stack,
                }
            )
            logger.error("%s/%s failed: %s", variant, example.query_id, error)
            if attempt <= max_retries:
                trace.emit(
                    "query_retry",
                    attempt=attempt,
                    error=error,
                )
                trace.flush_events()
                continue
            final_record = result_record(
                trace,
                example,
                None,
                None,
                status="failed",
                error=error,
                attempt=attempt,
            )
            trace.emit("query_failed", attempt=attempt, error=error)
            trace.flush_events()
    assert final_record is not None
    return final_record


def stratified_subset(
    examples: list[PublicExample], n: int, seed: int
) -> list[PublicExample]:
    if n <= 0 or n >= len(examples):
        return list(examples)
    key_name = "format" if examples[0].track == "type1" else "prefix"
    groups: dict[str, list[PublicExample]] = defaultdict(list)
    for example in examples:
        groups[str(example.metadata.get(key_name, "UNKNOWN"))].append(example)
    rng = random.Random(seed)
    selected: list[PublicExample] = []
    remainders: list[tuple[float, str]] = []
    for key, group in sorted(groups.items()):
        exact = n * len(group) / len(examples)
        count = min(len(group), math.floor(exact))
        shuffled = list(group)
        rng.shuffle(shuffled)
        selected.extend(shuffled[:count])
        groups[key] = shuffled[count:]
        remainders.append((exact - count, key))
    for _, key in sorted(remainders, reverse=True):
        if len(selected) >= n:
            break
        if groups[key]:
            selected.append(groups[key].pop())
    if len(selected) < n:
        leftovers = [item for group in groups.values() for item in group]
        rng.shuffle(leftovers)
        selected.extend(leftovers[: n - len(selected)])
    return sorted(selected[:n], key=lambda item: item.query_id)


def estimate_work(
    type1: list[PublicExample],
    type2: list[PublicExample],
    repeats: int,
    deterministic_repeats: int,
    latency_samples: int,
) -> dict[str, Any]:
    t1_eligible = sum(bool(x.metadata.get("z3_eligible")) for x in type1)
    return {
        "type1_examples": len(type1),
        "type1_z3_eligible": t1_eligible,
        "type2_examples": len(type2),
        "accuracy_pipeline_evaluations": (
            len(type1) * len(TYPE1_VARIANTS) * repeats
            + len(type2) * (3 * repeats + deterministic_repeats)
        ),
        "approx_physical_t1_cot_calls_with_cache": len(type1) * repeats,
        "approx_physical_t1_z3_codegen_calls_with_cache": t1_eligible * repeats,
        "uncached_latency_evaluations": min(latency_samples, len(type1))
        * len(TYPE1_VARIANTS)
        + min(latency_samples, len(type2))
        * (len(TYPE2_VARIANTS) + 1),
        "note": (
            "Type-1 CoT and first-pass Z3 outputs are paired/cached across variants "
            "within each repeat. Logical component calls remain separately counted."
        ),
    }


def completed_keys(path: Path, config_hash: str) -> set[tuple[str, str, str, int, str]]:
    keys: set[tuple[str, str, str, int, str]] = set()
    for row in read_jsonl(path):
        if row.get("config_hash") != config_hash:
            continue
        if row.get("status") != "completed":
            continue
        keys.add(
            completion_key(
                config_hash,
                str(row.get("phase")),
                str(row.get("variant")),
                int(row.get("repeat", 0)),
                str(row.get("query_id")),
            )
        )
    return keys


def run_matrix(
    *,
    repo_root: Path,
    output_dir: Path,
    args: argparse.Namespace,
    run_id: str,
    config_hash: str,
    reasoner: Any,
    cache: StageCache,
    type1_examples: list[PublicExample],
    type2_examples: list[PublicExample],
    logger: logging.Logger,
) -> None:
    predictions_path = output_dir / "predictions.jsonl"
    predictions_writer = JsonlWriter(predictions_path, fsync=True)
    events_writer = JsonlWriter(output_dir / "events.jsonl")
    errors_writer = JsonlWriter(output_dir / "errors.jsonl", fsync=True)
    done = completed_keys(predictions_path, config_hash) if args.resume else set()
    install_signal_handlers(logger)

    def execute_jobs(
        phase: str,
        examples: list[PublicExample],
        variants: tuple[str, ...],
        *,
        latency: bool,
    ) -> None:
        nonlocal done
        for repeat in range(args.repeats):
            if STOP_REQUESTED:
                return
            seed = args.seed + repeat
            ordered = list(examples)
            random.Random(seed).shuffle(ordered)
            for variant in variants:
                if STOP_REQUESTED:
                    return
                variant_repeat_count = args.repeats
                if variant == "t2_rag_solver" and not latency:
                    variant_repeat_count = args.deterministic_repeats
                if repeat >= variant_repeat_count:
                    continue
                include_explainer = variant == "t2_full_e2e"
                logger.info(
                    "Phase=%s variant=%s repeat=%d/%d samples=%d",
                    phase,
                    variant,
                    repeat + 1,
                    variant_repeat_count,
                    len(ordered),
                )
                for index, example in enumerate(ordered, start=1):
                    if STOP_REQUESTED:
                        return
                    key = completion_key(
                        config_hash, phase, variant, repeat, example.query_id
                    )
                    if key in done:
                        continue
                    sample_seed = seed + int(
                        hashlib.sha256(example.query_id.encode()).hexdigest()[:8],
                        16,
                    )
                    record = run_one_query(
                        repo_root=repo_root,
                        run_id=run_id,
                        config_hash=config_hash,
                        phase=phase,
                        example=example,
                        variant=variant,
                        repeat=repeat,
                        seed=sample_seed,
                        reasoner=reasoner,
                        cache=cache,
                        cache_enabled=(args.cache_shared_stages and not latency),
                        code_timeout=args.code_timeout,
                        include_explainer=include_explainer,
                        events_writer=events_writer,
                        errors_writer=errors_writer,
                        logger=logger,
                        max_retries=0 if latency else args.max_retries,
                    )
                    predictions_writer.write(record)
                    if record.get("status") == "completed":
                        done.add(key)
                    if index == 1 or index % args.progress_every == 0:
                        logger.info(
                            "%s r%d progress %d/%d",
                            variant,
                            repeat + 1,
                            index,
                            len(ordered),
                        )

    try:
        if args.tracks in {"both", "type1"}:
            execute_jobs(
                "accuracy", type1_examples, TYPE1_VARIANTS, latency=False
            )
        if args.tracks in {"both", "type2"}:
            execute_jobs(
                "accuracy", type2_examples, TYPE2_VARIANTS, latency=False
            )

        if args.latency_samples > 0 and not STOP_REQUESTED:
            # One real, uncached repeat per variant is enough for the latency profile.
            original_repeats = args.repeats
            args.repeats = 1
            try:
                if args.tracks in {"both", "type1"}:
                    subset = stratified_subset(
                        type1_examples, args.latency_samples, args.seed
                    )
                    execute_jobs("latency", subset, TYPE1_VARIANTS, latency=True)
                if args.tracks in {"both", "type2"}:
                    subset = stratified_subset(
                        type2_examples, args.latency_samples, args.seed
                    )
                    execute_jobs(
                        "latency",
                        subset,
                        (*TYPE2_VARIANTS, "t2_full_e2e"),
                        latency=True,
                    )
            finally:
                args.repeats = original_repeats
    finally:
        predictions_writer.close()
        events_writer.close()
        errors_writer.close()


def current_records(path: Path, config_hash: str) -> list[dict[str, Any]]:
    # Append-only checkpoints may contain a failed attempt followed by a
    # successful resume. Metrics use only the latest record per logical job.
    latest: dict[tuple[str, str, str, int, str], dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("config_hash") != config_hash:
            continue
        key = completion_key(
            config_hash,
            str(row.get("phase")),
            str(row.get("variant")),
            int(row.get("repeat", 0)),
            str(row.get("query_id")),
        )
        latest[key] = row
    return list(latest.values())


def expected_experiment_jobs(
    args: argparse.Namespace,
    *,
    type1_total: int = 808,
    type2_total: int = 200,
) -> list[dict[str, Any]]:
    """Return the exact logical job matrix used by the completeness gate."""
    t1_n = min(args.type1_limit or type1_total, type1_total)
    t2_n = min(args.type2_limit or type2_total, type2_total)
    rows: list[dict[str, Any]] = []

    if args.tracks in {"both", "type1"}:
        for variant in TYPE1_VARIANTS:
            for repeat in range(args.repeats):
                rows.append(
                    {
                        "phase": "accuracy",
                        "track": "type1",
                        "variant": variant,
                        "repeat": repeat,
                        "expected": t1_n,
                    }
                )
    if args.tracks in {"both", "type2"}:
        for variant in TYPE2_VARIANTS:
            repeat_count = (
                args.deterministic_repeats
                if variant == "t2_rag_solver"
                else args.repeats
            )
            for repeat in range(repeat_count):
                rows.append(
                    {
                        "phase": "accuracy",
                        "track": "type2",
                        "variant": variant,
                        "repeat": repeat,
                        "expected": t2_n,
                    }
                )
    if args.latency_samples > 0:
        if args.tracks in {"both", "type1"}:
            for variant in TYPE1_VARIANTS:
                rows.append(
                    {
                        "phase": "latency",
                        "track": "type1",
                        "variant": variant,
                        "repeat": 0,
                        "expected": min(args.latency_samples, t1_n),
                    }
                )
        if args.tracks in {"both", "type2"}:
            for variant in (*TYPE2_VARIANTS, "t2_full_e2e"):
                rows.append(
                    {
                        "phase": "latency",
                        "track": "type2",
                        "variant": variant,
                        "repeat": 0,
                        "expected": min(args.latency_samples, t2_n),
                    }
                )
    return rows


def experiment_completeness(
    records: list[dict[str, Any]], args: argparse.Namespace
) -> dict[str, Any]:
    observed: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        observed[
            (
                str(record.get("phase")),
                str(record.get("track")),
                str(record.get("variant")),
                int(record.get("repeat", 0)),
            )
        ].append(record)

    matrix: list[dict[str, Any]] = []
    for expected in expected_experiment_jobs(args):
        key = (
            expected["phase"],
            expected["track"],
            expected["variant"],
            expected["repeat"],
        )
        rows = observed.get(key, [])
        completed = sum(row.get("status") == "completed" for row in rows)
        failed = sum(row.get("status") == "failed" for row in rows)
        infrastructure_failed = sum(
            row.get("status") == "infrastructure_failed" for row in rows
        )
        matrix.append(
            {
                **expected,
                "observed": len(rows),
                "completed": completed,
                "failed": failed,
                "infrastructure_failed": infrastructure_failed,
                "missing": max(0, int(expected["expected"]) - completed),
                "complete": completed == int(expected["expected"]),
            }
        )

    full_paper_scope = (
        args.mode == "full"
        and args.tracks == "both"
        and args.type1_limit == 0
        and args.type2_limit == 0
        and args.repeats == 3
        and args.deterministic_repeats == 1
        and args.latency_samples >= 50
    )
    complete = bool(matrix) and all(row["complete"] for row in matrix)
    infrastructure_failed = sum(
        row["infrastructure_failed"] for row in matrix
    )
    ordinary_failed = sum(row["failed"] for row in matrix)
    return {
        "complete_for_requested_subset": complete,
        "full_paper_scope": full_paper_scope,
        "complete": complete,
        "paper_ready": full_paper_scope
        and complete
        and infrastructure_failed == 0
        and ordinary_failed == 0,
        "expected_total": sum(int(row["expected"]) for row in matrix),
        "completed_total": sum(int(row["completed"]) for row in matrix),
        "failed_total": ordinary_failed,
        "infrastructure_failed_total": infrastructure_failed,
        "matrix": matrix,
    }


def bool_mean(rows: list[dict[str, Any]], getter: Callable[[dict[str, Any]], Any]) -> float:
    if not rows:
        return 0.0
    return sum(1.0 if getter(row) else 0.0 for row in rows) / len(rows)


def per_repeat_metrics(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row.get("phase") != "accuracy":
            continue
        groups[
            (
                str(row.get("track")),
                str(row.get("variant")),
                int(row.get("repeat", 0)),
            )
        ].append(row)

    output: list[dict[str, Any]] = []
    for (track, variant, repeat), rows in sorted(groups.items()):
        completed = [row for row in rows if row.get("status") == "completed"]
        base = {
            "track": track,
            "variant": variant,
            "repeat": repeat,
            "n": len(rows),
            "completed": len(completed),
            "failed": sum(row.get("status") == "failed" for row in rows),
            "infrastructure_failed": sum(
                row.get("status") == "infrastructure_failed" for row in rows
            ),
        }
        if track == "type1":
            annotated = [
                row
                for row in rows
                if (row.get("gold") or {}).get("premises_used") is not None
            ]
            base.update(
                {
                    "answer_accuracy": bool_mean(
                        rows,
                        lambda row: row.get("status") == "completed"
                        and bool(
                            (row.get("scores") or {}).get("answer_correct")
                        ),
                    ),
                    "premise_precision": statistics.fmean(
                        [
                            float((row.get("scores") or {}).get("premise_precision") or 0.0)
                            if row.get("status") == "completed"
                            else 0.0
                            for row in annotated
                        ]
                    )
                    if annotated
                    else None,
                    "premise_recall": statistics.fmean(
                        [
                            float((row.get("scores") or {}).get("premise_recall") or 0.0)
                            if row.get("status") == "completed"
                            else 0.0
                            for row in annotated
                        ]
                    )
                    if annotated
                    else None,
                    "premise_f1": statistics.fmean(
                        [
                            float((row.get("scores") or {}).get("premise_f1") or 0.0)
                            if row.get("status") == "completed"
                            else 0.0
                            for row in annotated
                        ]
                    )
                    if annotated
                    else None,
                    "combined_score": statistics.fmean(
                        [
                            float((row.get("scores") or {}).get("combined_score") or 0.0)
                            if row.get("status") == "completed"
                            else 0.0
                            for row in annotated
                        ]
                    )
                    if annotated
                    else None,
                    "full_correct": bool_mean(
                        annotated,
                        lambda row: row.get("status") == "completed"
                        and bool((row.get("scores") or {}).get("full_correct")),
                    )
                    if annotated
                    else None,
                    "premise_annotated_n": len(annotated),
                    "coverage": bool_mean(
                        rows,
                        lambda row: row.get("status") == "completed"
                        and bool(
                            str((row.get("response") or {}).get("answer") or "").strip()
                        ),
                    ),
                }
            )
        else:
            base.update(
                {
                    "answer_accuracy": bool_mean(
                        rows,
                        lambda row: row.get("status") == "completed"
                        and bool(
                            (row.get("scores") or {}).get("answer_correct")
                        ),
                    ),
                    "unit_accuracy": bool_mean(
                        rows,
                        lambda row: row.get("status") == "completed"
                        and bool((row.get("scores") or {}).get("unit_correct")),
                    ),
                    "strict_accuracy": bool_mean(
                        rows,
                        lambda row: row.get("status") == "completed"
                        and bool((row.get("scores") or {}).get("strict_correct")),
                    ),
                    "coverage": bool_mean(
                        rows,
                        lambda row: row.get("status") == "completed"
                        and bool(
                            str((row.get("response") or {}).get("answer") or "").strip()
                        ),
                    ),
                }
            )
        output.append(base)
    return output


def aggregate_ablation(per_repeat: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in per_repeat:
        groups[(str(row["track"]), str(row["variant"]))].append(row)
    output: list[dict[str, Any]] = []
    metrics_by_track = {
        "type1": [
            "answer_accuracy",
            "premise_precision",
            "premise_recall",
            "premise_f1",
            "combined_score",
            "full_correct",
            "coverage",
        ],
        "type2": [
            "answer_accuracy",
            "unit_accuracy",
            "strict_accuracy",
            "coverage",
        ],
    }
    for (track, variant), rows in sorted(groups.items()):
        result: dict[str, Any] = {
            "track": track,
            "variant": variant,
            "repeats": len(rows),
            "n_per_repeat_min": min(int(row["n"]) for row in rows),
            "n_per_repeat_max": max(int(row["n"]) for row in rows),
        }
        for metric in metrics_by_track[track]:
            mean, std = mean_std([row.get(metric) for row in rows])
            result[metric + "_mean"] = mean
            result[metric + "_std"] = std
        output.append(result)
    return output


def component_statistics(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row.get("phase") == "accuracy":
            groups[(str(row.get("track")), str(row.get("variant")))].append(row)
    output: list[dict[str, Any]] = []
    for (track, variant), rows in sorted(groups.items()):
        if track == "type1":
            eligible = sum(
                bool((row.get("input") or {}).get("metadata", {}).get("z3_eligible"))
                for row in rows
            )
            called_rows = [row for row in rows if (row.get("z3") or {}).get("called")]
            first_exec = [
                row
                for row in called_rows
                if (row.get("z3") or {}).get("executions")
            ]
            accepted = [
                row
                for row in called_rows
                if (row.get("z3") or {}).get("final_accepted")
            ]
            repair = [
                row
                for row in called_rows
                if (row.get("z3") or {}).get("repair_triggered")
            ]
            result = {
                "track": track,
                "variant": variant,
                "n": len(rows),
                "eligible": eligible,
                "called": len(called_rows),
                "codegen_success": sum(
                    bool((row.get("z3") or {}).get("codegen_success"))
                    for row in called_rows
                ),
                "first_execution_success": sum(
                    bool((row.get("z3") or {}).get("first_execution_success"))
                    for row in first_exec
                ),
                "repair_triggered": len(repair),
                "repair_execution_success": sum(
                    bool((row.get("z3") or {}).get("repair_execution_success"))
                    for row in repair
                ),
                "repair_task_correct": sum(
                    bool((row.get("z3") or {}).get("repair_execution_success"))
                    and bool((row.get("z3") or {}).get("final_accepted"))
                    and bool(
                        (row.get("z3") or {}).get(
                            "task_correct_among_accepted"
                        )
                    )
                    for row in repair
                ),
                "final_accepted": len(accepted),
                "correct_among_accepted": sum(
                    bool((row.get("z3") or {}).get("task_correct_among_accepted"))
                    for row in accepted
                ),
                "helpful_overrides": sum(
                    bool((row.get("z3") or {}).get("helpful_override")) for row in rows
                ),
                "harmful_overrides": sum(
                    bool((row.get("z3") or {}).get("harmful_override")) for row in rows
                ),
            }
            result["failed"] = result["called"] - result["final_accepted"]
            result["failure_reasons"] = canonical_json(
                dict(
                    Counter(
                        str(
                            (row.get("z3") or {}).get("failure_reason")
                            or "not_accepted"
                        )
                        for row in called_rows
                        if not (row.get("z3") or {}).get("final_accepted")
                    )
                )
            )
            result["execution_timeouts"] = sum(
                bool(execution.get("timeout"))
                for row in called_rows
                for execution in ((row.get("z3") or {}).get("executions") or [])
            )
            result.update(
                {
                    "success_rate": (
                        result["final_accepted"] / result["called"]
                        if result["called"]
                        else None
                    ),
                    "repair_success_rate": (
                        result["repair_execution_success"]
                        / result["repair_triggered"]
                        if result["repair_triggered"]
                        else None
                    ),
                    "repair_task_success_rate": (
                        result["repair_task_correct"]
                        / result["repair_triggered"]
                        if result["repair_triggered"]
                        else None
                    ),
                    "task_correct_among_successful_rate": (
                        result["correct_among_accepted"] / result["final_accepted"]
                        if result["final_accepted"]
                        else None
                    ),
                }
            )
        else:
            called_rows = [row for row in rows if (row.get("pal") or {}).get("called")]
            accepted = [
                row
                for row in called_rows
                if (row.get("pal") or {}).get("final_accepted")
            ]
            repair = [
                row
                for row in called_rows
                if (row.get("pal") or {}).get("repair_triggered")
            ]
            result = {
                "track": track,
                "variant": variant,
                "n": len(rows),
                "eligible": sum(
                    bool((row.get("flags") or {}).get("pal_eligible"))
                    for row in rows
                ),
                "called": len(called_rows),
                "codegen_success": sum(
                    bool((row.get("pal") or {}).get("codegen_success"))
                    for row in called_rows
                ),
                "first_execution_success": sum(
                    bool((row.get("pal") or {}).get("first_execution_success"))
                    for row in called_rows
                ),
                "repair_triggered": len(repair),
                "repair_execution_success": sum(
                    bool((row.get("pal") or {}).get("repair_execution_success"))
                    for row in repair
                ),
                "repair_task_correct": sum(
                    bool((row.get("pal") or {}).get("repair_execution_success"))
                    and bool((row.get("pal") or {}).get("final_accepted"))
                    and bool(
                        (row.get("pal") or {}).get(
                            "task_correct_among_accepted"
                        )
                    )
                    for row in repair
                ),
                "final_accepted": len(accepted),
                "correct_among_accepted": sum(
                    bool((row.get("pal") or {}).get("task_correct_among_accepted"))
                    for row in accepted
                ),
                "helpful_overrides": None,
                "harmful_overrides": None,
            }
            result["failed"] = result["called"] - result["final_accepted"]
            result["failure_reasons"] = canonical_json(
                dict(
                    Counter(
                        str(
                            (row.get("pal") or {}).get("failure_reason")
                            or "not_accepted"
                        )
                        for row in called_rows
                        if not (row.get("pal") or {}).get("final_accepted")
                    )
                )
            )
            result["execution_timeouts"] = sum(
                bool(execution.get("timeout"))
                for row in called_rows
                for execution in ((row.get("pal") or {}).get("executions") or [])
            )
            result.update(
                {
                    "success_rate": (
                        result["final_accepted"] / result["called"]
                        if result["called"]
                        else None
                    ),
                    "repair_success_rate": (
                        result["repair_execution_success"]
                        / result["repair_triggered"]
                        if result["repair_triggered"]
                        else None
                    ),
                    "repair_task_success_rate": (
                        result["repair_task_correct"]
                        / result["repair_triggered"]
                        if result["repair_triggered"]
                        else None
                    ),
                    "task_correct_among_successful_rate": (
                        result["correct_among_accepted"] / result["final_accepted"]
                        if result["final_accepted"]
                        else None
                    ),
                }
            )
        output.append(result)
    return output


def latency_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row.get("phase") == "latency":
            groups[(str(row.get("track")), str(row.get("variant")))].append(row)
    output: list[dict[str, Any]] = []
    for (track, variant), scheduled_rows in sorted(groups.items()):
        rows = [
            row for row in scheduled_rows if row.get("status") == "completed"
        ]
        wall = [
            float((row.get("scores") or {}).get("wall_duration_s"))
            for row in rows
            if (row.get("scores") or {}).get("wall_duration_s") is not None
        ]
        ready = [
            float((row.get("scores") or {}).get("answer_ready_duration_s"))
            for row in rows
            if (row.get("scores") or {}).get("answer_ready_duration_s") is not None
        ]
        stats = latency_stats(wall)
        ready_stats = latency_stats(ready)
        timeout_records = sum(
            bool(
                "timeout" in str(row.get("error") or "").lower()
                or any(
                    "timeout" in str(call.get("error") or "").lower()
                    for call in (row.get("llm_calls") or [])
                )
                or any(
                    bool(execution.get("timeout"))
                    for component in ("z3", "pal")
                    for execution in (
                        (row.get(component) or {}).get("executions") or []
                    )
                )
            )
            for row in scheduled_rows
        )
        output.append(
            {
                "track": track,
                "variant": variant,
                "scheduled_n": len(scheduled_rows),
                "completed_n": len(rows),
                "failed_n": sum(
                    row.get("status") == "failed" for row in scheduled_rows
                ),
                "infrastructure_failed_n": sum(
                    row.get("status") == "infrastructure_failed"
                    for row in scheduled_rows
                ),
                **stats,
                "answer_ready_mean_s": ready_stats["mean_s"],
                "answer_ready_p95_s": ready_stats["p95_s"],
                "over_60s": sum(value > 60 for value in wall),
                "sla_over_60_rate": (
                    sum(value > 60 for value in wall) / len(wall) if wall else None
                ),
                "observed_timeout_n": timeout_records,
            }
        )
    return output


def type2_overlap_sensitivity(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row.get("phase") == "accuracy" and row.get("track") == "type2":
            groups[(str(row.get("variant")), int(row.get("repeat", 0)))].append(row)
    output: list[dict[str, Any]] = []
    for (variant, repeat), rows in sorted(groups.items()):
        without_overlap = [
            row for row in rows if str(row.get("query_id")) != "DDT361"
        ]
        output.append(
            {
                "variant": variant,
                "repeat": repeat,
                "n_all": len(rows),
                "strict_accuracy_all": bool_mean(
                    rows,
                    lambda row: bool((row.get("scores") or {}).get("strict_correct")),
                ),
                "n_without_DDT361": len(without_overlap),
                "strict_accuracy_without_DDT361": bool_mean(
                    without_overlap,
                    lambda row: bool((row.get("scores") or {}).get("strict_correct")),
                ),
                "overlap_case_correct": next(
                    (
                        bool((row.get("scores") or {}).get("strict_correct"))
                        for row in rows
                        if str(row.get("query_id")) == "DDT361"
                    ),
                    None,
                ),
            }
        )
    return output


def per_query_variant_scores(
    records: list[dict[str, Any]],
    track: str,
    variant: str,
    metric: str,
) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in records:
        if (
            row.get("phase") != "accuracy"
            or row.get("track") != track
            or row.get("variant") != variant
        ):
            continue
        value = (row.get("scores") or {}).get(metric)
        if value is not None:
            grouped[str(row.get("query_id"))].append(float(value))
    return {key: statistics.fmean(values) for key, values in grouped.items()}


def paired_bootstrap(
    left: dict[str, float],
    right: dict[str, float],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    keys = sorted(set(left) & set(right))
    if not keys:
        return {"n": 0, "delta": None, "ci_low": None, "ci_high": None}
    deltas = [right[key] - left[key] for key in keys]
    observed = statistics.fmean(deltas)
    rng = random.Random(seed)
    boot: list[float] = []
    for _ in range(samples):
        boot.append(
            statistics.fmean(deltas[rng.randrange(len(deltas))] for _ in deltas)
        )
    return {
        "n": len(keys),
        "delta": observed,
        "ci_low": percentile(boot, 0.025),
        "ci_high": percentile(boot, 0.975),
    }


def bootstrap_comparisons(
    records: list[dict[str, Any]], samples: int, seed: int
) -> list[dict[str, Any]]:
    specs = [
        ("type1", "t1_cot_only", "t1_cot_z3_no_repair", "answer_correct"),
        ("type1", "t1_cot_z3_no_repair", "t1_full", "answer_correct"),
        ("type1", "t1_cot_only", "t1_cot_z3_no_repair", "combined_score"),
        ("type1", "t1_cot_z3_no_repair", "t1_full", "combined_score"),
        ("type2", "t2_cot_only", "t2_rag_solver", "strict_correct"),
        ("type2", "t2_rag_solver", "t2_rag_solver_pal", "strict_correct"),
        ("type2", "t2_rag_solver_pal", "t2_full", "strict_correct"),
    ]
    output: list[dict[str, Any]] = []
    for track, left_name, right_name, metric in specs:
        left = per_query_variant_scores(records, track, left_name, metric)
        right = per_query_variant_scores(records, track, right_name, metric)
        output.append(
            {
                "track": track,
                "metric": metric,
                "left_variant": left_name,
                "right_variant": right_name,
                **paired_bootstrap(left, right, samples=samples, seed=seed),
            }
        )
    return output


def csv_value(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.8f}"
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fields})


def display_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        if abs(value) <= 1.0:
            return f"{value:.4f}"
        return f"{value:.3f}"
    return str(value)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No data available._\n"
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| "
        + " | ".join(
            display_value(row.get(column)).replace("|", "\\|") for column in columns
        )
        + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body]) + "\n"


def latex_escape(value: Any) -> str:
    text = display_value(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def latex_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    align = "l" + "r" * (len(columns) - 1)
    lines = [
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        " & ".join(latex_escape(column) for column in columns) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(latex_escape(row.get(column)) for column in columns)
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    return "\n".join(lines)


def write_table_bundle(
    base: Path, rows: list[dict[str, Any]], columns: list[str]
) -> None:
    write_csv(base.with_suffix(".csv"), rows)
    base.with_suffix(".md").write_text(
        markdown_table(rows, columns), encoding="utf-8"
    )
    base.with_suffix(".tex").write_text(
        latex_table(rows, columns), encoding="utf-8"
    )


def official_table_rows(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for round_data in rounds:
        rows.append(
            {
                "Round": round_data.get("round"),
                "N": round_data.get("n"),
                "Total": round_data.get("total_score"),
                "Type 1 points": round_data.get("type1_points"),
                "T1 answer (%)": (
                    100 * round_data["type1_answer_accuracy"]
                    if round_data.get("type1_answer_accuracy") is not None
                    else None
                ),
                "T1 premise F1 (%)": (
                    100 * round_data["type1_premise_f1"]
                    if round_data.get("type1_premise_f1") is not None
                    else None
                ),
                "T1 combined (%)": (
                    100 * round_data["type1_combined"]
                    if round_data.get("type1_combined") is not None
                    else None
                ),
                "T1 full exact (%)": (
                    100 * round_data["type1_full_correct"]
                    if round_data.get("type1_full_correct") is not None
                    else None
                ),
                "Type 2 points": round_data.get("type2_points"),
                "T2 strict (%)": (
                    100 * round_data["type2_strict_accuracy"]
                    if round_data.get("type2_strict_accuracy") is not None
                    else None
                ),
                "Time bonus": round_data.get("time_bonus"),
                "Data correctness": (
                    f"{round_data.get('data_correctness_status')} · "
                    f"{round_data.get('data_correctness_points')}"
                ),
            }
        )
    return rows


def official_latency_rows(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for round_data in rounds:
        for group, key in [
            ("All", "latency_all"),
            ("Type 1", "latency_type1"),
            ("Type 2", "latency_type2"),
            ("P1-correct", "latency_p1_correct"),
        ]:
            stats = round_data.get(key) or {}
            rows.append(
                {
                    "Round": round_data.get("round"),
                    "Group": group,
                    "N": stats.get("n"),
                    "Mean (s)": stats.get("mean_s"),
                    "Std (s)": stats.get("std_s"),
                    "Median (s)": stats.get("median_s"),
                    "P90 (s)": stats.get("p90_s"),
                    "P95 (s)": stats.get("p95_s"),
                    "Min (s)": stats.get("min_s"),
                    "Max (s)": stats.get("max_s"),
                }
            )
    return rows


def ablation_table_rows(
    aggregate: list[dict[str, Any]], track: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in aggregate:
        if row["track"] != track:
            continue
        if track == "type1":
            rows.append(
                {
                    "Variant": row["variant"],
                    "Repeats": row["repeats"],
                    "Answer mean (%)": 100 * row["answer_accuracy_mean"]
                    if row.get("answer_accuracy_mean") is not None
                    else None,
                    "Answer SD (pp)": 100 * row["answer_accuracy_std"]
                    if row.get("answer_accuracy_std") is not None
                    else None,
                    "Premise F1 (%)": 100 * row["premise_f1_mean"]
                    if row.get("premise_f1_mean") is not None
                    else None,
                    "Combined (%)": 100 * row["combined_score_mean"]
                    if row.get("combined_score_mean") is not None
                    else None,
                    "Full correct (%)": 100 * row["full_correct_mean"]
                    if row.get("full_correct_mean") is not None
                    else None,
                }
            )
        else:
            rows.append(
                {
                    "Variant": row["variant"],
                    "Repeats": row["repeats"],
                    "Answer mean (%)": 100 * row["answer_accuracy_mean"]
                    if row.get("answer_accuracy_mean") is not None
                    else None,
                    "Answer SD (pp)": 100 * row["answer_accuracy_std"]
                    if row.get("answer_accuracy_std") is not None
                    else None,
                    "Unit mean (%)": 100 * row["unit_accuracy_mean"]
                    if row.get("unit_accuracy_mean") is not None
                    else None,
                    "Strict mean (%)": 100 * row["strict_accuracy_mean"]
                    if row.get("strict_accuracy_mean") is not None
                    else None,
                    "Strict SD (pp)": 100 * row["strict_accuracy_std"]
                    if row.get("strict_accuracy_std") is not None
                    else None,
                }
            )
    return rows


def select_case_studies(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    full_t1 = [
        row
        for row in records
        if row.get("phase") == "accuracy"
        and row.get("variant") == "t1_full"
        and row.get("repeat") == 0
        and row.get("status") == "completed"
    ]
    full_t2 = [
        row
        for row in records
        if row.get("phase") == "accuracy"
        and row.get("variant") == "t2_full"
        and row.get("repeat") == 0
        and row.get("status") == "completed"
    ]
    categories: list[tuple[str, list[dict[str, Any]], str]] = [
        (
            "Z3 corrects CoT",
            [
                row
                for row in full_t1
                if (row.get("z3") or {}).get("helpful_override")
            ],
            "Shows a formal path correcting an initially wrong neural answer.",
        ),
        (
            "PAL solves a symbolic fallback",
            [
                row
                for row in full_t2
                if (row.get("artifacts") or {}).get("solver_source") == "llm_pal"
                and (row.get("scores") or {}).get("strict_correct")
                and not (row.get("pal") or {}).get("repair_triggered")
            ],
            "Shows program generation followed by machine-executed arithmetic.",
        ),
        (
            "Self-repair recovers PAL",
            [
                row
                for row in full_t2
                if (row.get("pal") or {}).get("repair_execution_success")
                and (row.get("scores") or {}).get("strict_correct")
            ],
            "Shows a failed first program repaired into an executable correct answer.",
        ),
        (
            "Specialized symbolic solver",
            [
                row
                for row in full_t2
                if (row.get("artifacts") or {}).get("solver_source")
                in {"sympy", "circuit", "vector_solver", "resonance", "error_calc"}
                and (row.get("scores") or {}).get("strict_correct")
            ],
            "Shows a deterministic solver avoiding free-form LLM arithmetic.",
        ),
        (
            "Limitation: harmful override",
            [
                row
                for row in full_t1
                if (row.get("z3") or {}).get("harmful_override")
            ],
            "Shows why generated formalizations require gating and error analysis.",
        ),
        (
            "Z3 verifies CoT",
            [
                row
                for row in full_t1
                if (row.get("z3") or {}).get("final_accepted")
                and (row.get("scores") or {}).get("answer_correct")
            ],
            "Shows agreement between neural reasoning and an executable formal check.",
        ),
        (
            "Correct Type-1 premise attribution",
            [
                row
                for row in full_t1
                if (row.get("scores") or {}).get("answer_correct")
                and (row.get("gold") or {}).get("premises_used") is not None
                and (row.get("response") or {}).get("premises_used")
            ],
            "Shows the full logic output, including evidence attribution rather than "
            "answer accuracy alone.",
        ),
        (
            "Correct RAG/deterministic physics path",
            [
                row
                for row in full_t2
                if (row.get("scores") or {}).get("strict_correct")
                and (row.get("artifacts") or {}).get("solver_source")
                not in {"llm_pal", "llm_cot", "llm_fallback"}
            ],
            "Shows a correct answer-and-unit result from formula retrieval and a "
            "deterministic solver.",
        ),
        (
            "Representative Type-1 limitation",
            [
                row
                for row in full_t1
                if not (row.get("scores") or {}).get("answer_correct")
            ],
            "Makes a public-data failure visible instead of cherry-picking only "
            "successful examples.",
        ),
        (
            "Representative Type-2 limitation",
            [
                row
                for row in full_t2
                if not (row.get("scores") or {}).get("strict_correct")
            ],
            "Shows a remaining physics failure and the component path that produced it.",
        ),
        (
            "Representative public Type-1 outcome",
            full_t1,
            "Provides a fallback public-corpus example when rarer symbolic categories "
            "are absent in a particular rerun.",
        ),
        (
            "Representative public Type-2 outcome",
            full_t2,
            "Provides a fallback public-dev physics example when rarer symbolic "
            "categories are absent in a particular rerun.",
        ),
    ]
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for category, candidates, why in categories:
        candidate = next(
            (
                row
                for row in candidates
                if f"{row.get('track')}:{row.get('query_id')}" not in used_ids
            ),
            None,
        )
        if candidate is None:
            continue
        query_id = str(candidate.get("query_id"))
        used_ids.add(f"{candidate.get('track')}:{query_id}")
        artifacts = candidate.get("artifacts") or {}
        response = candidate.get("response") or {}
        if candidate.get("track") == "type1":
            process = (
                f"CoT proposed {artifacts.get('cot_answer')}; "
                f"Z3 decision={((candidate.get('z3') or {}).get('decision'))}; "
                f"final={response.get('answer')} with premises "
                f"{response.get('premises_used')}."
            )
        else:
            formula = artifacts.get("formula") or {}
            process = (
                f"Parser domain={((artifacts.get('parsed_physics') or {}).get('domain'))}, "
                f"target={((artifacts.get('parsed_physics') or {}).get('find'))}; "
                f"formula={formula.get('id') or formula.get('formulas')}; "
                f"final source={artifacts.get('solver_source')}."
            )
        selected.append(
            {
                "category": category,
                "query_id": query_id,
                "track": candidate.get("track"),
                "problem": (candidate.get("input") or {}).get("question"),
                "premises": (candidate.get("input") or {}).get("premises") or [],
                "processing": process,
                "output": {
                    "answer": response.get("answer"),
                    "unit": response.get("unit"),
                    "premises_used": response.get("premises_used"),
                    "explanation": response.get("explanation"),
                },
                "gold": candidate.get("gold"),
                "scores": candidate.get("scores"),
                "trace": {
                    "solver_source": artifacts.get("solver_source"),
                    "formula": artifacts.get("formula"),
                    "z3": {
                        key: (candidate.get("z3") or {}).get(key)
                        for key in (
                            "decision",
                            "first_execution_success",
                            "repair_triggered",
                            "repair_execution_success",
                            "final_accepted",
                            "failure_reason",
                            "helpful_override",
                            "harmful_override",
                        )
                    },
                    "z3_executions": [
                        {
                            key: execution.get(key)
                            for key in (
                                "attempt",
                                "ok",
                                "timeout",
                                "error",
                                "output",
                            )
                        }
                        for execution in ((candidate.get("z3") or {}).get("executions") or [])
                    ],
                    "pal": {
                        key: (candidate.get("pal") or {}).get(key)
                        for key in (
                            "first_execution_success",
                            "repair_triggered",
                            "repair_execution_success",
                            "final_accepted",
                            "failure_reason",
                        )
                    },
                    "pal_executions": [
                        {
                            key: execution.get(key)
                            for key in (
                                "attempt",
                                "ok",
                                "timeout",
                                "error",
                                "result",
                            )
                        }
                        for execution in ((candidate.get("pal") or {}).get("executions") or [])
                    ],
                    "generated_program_excerpt": truncate(
                        artifacts.get("z3_repaired_code")
                        or artifacts.get("z3_code")
                        or artifacts.get("pal_repaired_code")
                        or artifacts.get("pal_code"),
                        1800,
                    ),
                },
                "why_notable": why,
                "source_policy": (
                    "retrospective public Type-1 corpus or public Type-2 dev only"
                ),
            }
        )
        if len(selected) >= 5:
            break
    return selected


def case_studies_markdown(cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Public-data Case Studies",
        "",
        "Examples come only from the retrospective public Type-1 corpus or the "
        "public Type-2 dev split. No hidden round query is reproduced.",
        "",
    ]
    if not cases:
        lines.append(
            "_No qualifying case was found in the completed records; do not invent one._"
        )
        return "\n".join(lines) + "\n"
    for index, case in enumerate(cases, start=1):
        lines.extend(
            [
                f"## Case {index}: {case['category']}",
                "",
                f"- Query ID: `{case['query_id']}`",
                f"- Track: `{case['track']}`",
                f"- Why notable: {case['why_notable']}",
                "",
                "Problem:",
                "",
                "```text",
                truncate(case.get("problem"), 3000),
                "```",
                "",
            ]
        )
        premises = case.get("premises") or []
        if premises:
            lines.extend(["Premises:", ""])
            lines.extend(f"{i}. {value}" for i, value in enumerate(premises))
            lines.append("")
        lines.extend(
            [
                "Processing:",
                "",
                case.get("processing") or "",
                "",
                "Output:",
                "",
                "```json",
                json.dumps(
                    {
                        **(case.get("output") or {}),
                        "explanation": truncate(
                            (case.get("output") or {}).get("explanation"), 1200
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "Gold and scores:",
                "",
                "```json",
                json.dumps(
                    {
                        "gold": case.get("gold"),
                        "scores": case.get("scores"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "Sanitized component trace:",
                "",
                "```json",
                json.dumps(
                    case.get("trace") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


ARCHITECTURE_MERMAID = """flowchart LR
    I[UnifiedRequest] --> R{request.type}
    R -->|type1| C1[Question format classifier]
    C1 --> COT[Qwen CoT]
    COT --> ZG{non-open and<br/>premises ≤ 12?}
    ZG -->|yes| GZ[Exemplar retrieval + Z3 code generation]
    GZ --> EZ[Z3 program executor]
    EZ -->|execution failed| RZ[Optional one-step repair]
    EZ -->|accepted or rejected| D1[Agree / override / premise attribution]
    RZ --> D1
    ZG -->|no: bypass Z3| D1
    D1 --> S1[Answer sanitizer]

    R -->|type2| P2[Regex parser + optional Qwen augmentation]
    P2 --> FR[Formula retrieval + chaining]
    FR --> DS[SymPy + specialized solvers]
    DS --> DG{usable deterministic<br/>result?}
    DG -->|no| PAL[PAL code generation]
    PAL --> EP[PAL program executor]
    EP -->|failed| RP[Optional one-step repair]
    EP -->|success| V2[Validation + unit normalization]
    RP -->|failed| FC[Qwen CoT fallback]
    RP -->|success| V2
    FC --> V2[Validation + unit normalization]
    DG -->|yes| V2

    S1 --> O[UnifiedResponse]
    V2 --> X{presentation explainer<br/>requested?}
    X -->|yes| EX[Qwen explanation]
    X -->|no| O
    EX --> O
"""


def generate_architecture(output_dir: Path, logger: logging.Logger) -> None:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    (figure_dir / "architecture.mmd").write_text(
        ARCHITECTURE_MERMAID, encoding="utf-8"
    )
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

        fig, ax = plt.subplots(figsize=(15, 8.5))
        ax.set_xlim(0, 15)
        ax.set_ylim(0, 9)
        ax.axis("off")

        def box(
            x: float,
            y: float,
            width: float,
            height: float,
            text: str,
            color: str,
        ) -> tuple[float, float]:
            patch = FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.04,rounding_size=0.12",
                linewidth=1.4,
                edgecolor="#263238",
                facecolor=color,
            )
            ax.add_patch(patch)
            ax.text(
                x + width / 2,
                y + height / 2,
                text,
                ha="center",
                va="center",
                fontsize=9,
                wrap=True,
            )
            return x + width / 2, y + height / 2

        def arrow(
            start: tuple[float, float],
            end: tuple[float, float],
            *,
            dashed: bool = False,
        ) -> None:
            ax.add_patch(
                FancyArrowPatch(
                    start,
                    end,
                    arrowstyle="-|>",
                    mutation_scale=12,
                    linewidth=1.2,
                    linestyle="--" if dashed else "-",
                    color="#455A64",
                    connectionstyle="arc3,rad=0",
                )
            )

        input_center = box(0.4, 4.0, 1.5, 0.8, "Unified\nRequest", "#ECEFF1")
        route_center = box(2.3, 4.0, 1.4, 0.8, "Route by\nrequest.type", "#FFF3E0")
        arrow((1.9, 4.4), (2.3, 4.4))

        t1_boxes = [
            (4.2, 6.8, "Format\nclassifier", "#E3F2FD"),
            (6.1, 6.8, "Qwen\nCoT", "#E8EAF6"),
            (8.0, 6.8, "Z3 gate + code\n(non-open, ≤12)", "#E8EAF6"),
            (9.9, 6.8, "Z3 executor\n(if eligible)", "#E0F2F1"),
            (11.8, 6.8, "Repair if failed\n+ consensus", "#E0F2F1"),
            (13.4, 6.8, "Sanitize", "#E3F2FD"),
        ]
        t2_boxes = [
            (4.2, 1.4, "Regex + optional\nQwen parser", "#E3F2FD"),
            (6.1, 1.4, "Formula RAG\n+ chaining", "#FFF8E1"),
            (8.0, 1.4, "SymPy +\nspecialists", "#E0F2F1"),
            (9.9, 1.4, "PAL if no usable\nsolver result", "#E0F2F1"),
            (11.8, 1.4, "Repair → CoT\nonly on failure", "#E8EAF6"),
            (13.4, 1.4, "Validate +\nunit snap", "#E3F2FD"),
        ]
        for boxes in (t1_boxes, t2_boxes):
            centers = [
                box(x, y, 1.45, 0.9, label, color)
                for x, y, label, color in boxes
            ]
            for left, right in zip(centers, centers[1:]):
                arrow((left[0] + 0.73, left[1]), (right[0] - 0.73, right[1]))
        arrow((3.7, 4.4), (4.2, 7.25))
        arrow((3.7, 4.4), (4.2, 1.85))
        output_center = box(
            13.25,
            4.0,
            1.55,
            0.8,
            "Optional explainer\n→ UnifiedResponse",
            "#ECEFF1",
        )
        arrow((14.13, 6.8), (14.03, 4.8))
        arrow((14.13, 2.3), (14.03, 4.0))
        ax.text(7.5, 8.45, "Type 1 — Logic", ha="center", fontsize=13, weight="bold")
        ax.text(7.5, 0.55, "Type 2 — Physics", ha="center", fontsize=13, weight="bold")
        ax.text(
            7.5,
            4.45,
            "Reconstructed current-snapshot control flow; solver/repair arrows are conditional",
            ha="center",
            fontsize=9,
            color="#37474F",
        )
        fig.tight_layout()
        fig.savefig(figure_dir / "architecture.png", dpi=220, bbox_inches="tight")
        fig.savefig(figure_dir / "architecture.pdf", bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:
        logger.warning("Could not render architecture PNG/PDF: %s", exc)


def generate_reports(
    *,
    repo_root: Path,
    output_dir: Path,
    config_hash: str,
    args: argparse.Namespace,
    logger: logging.Logger,
) -> dict[str, Any]:
    metrics_dir = output_dir / "metrics"
    tables_dir = output_dir / "tables"
    cases_dir = output_dir / "cases"
    for directory in (metrics_dir, tables_dir, cases_dir):
        directory.mkdir(parents=True, exist_ok=True)

    official_paths = [
        repo_root / args.round1_log,
        repo_root / args.round2_log,
    ]
    missing_official = [str(path) for path in official_paths if not path.exists()]
    if missing_official:
        raise FileNotFoundError(
            "Required official aggregate log(s) are missing: "
            + ", ".join(missing_official)
            + ". Upload/copy the supplied logs and use --round1-log/"
            "--round2-log when their paths differ."
        )
    official = [official_round_metrics(path) for path in official_paths]
    for round_data in official:
        if round_data["p2_regression_mismatches"]:
            raise AssertionError(
                f"Official P2 regression failed for round {round_data['round']}: "
                f"{round_data['p2_regression_mismatches'][:3]}"
            )
        if round_data["type2_regression_mismatches"]:
            raise AssertionError(
                f"Official Type-2 scorer regression failed for round "
                f"{round_data['round']}: "
                f"{round_data['type2_regression_mismatches'][:3]}"
            )
        if round_data["score_regression_mismatches"]:
            raise AssertionError(
                f"Official score formula regression failed for round "
                f"{round_data['round']}: "
                f"{round_data['score_regression_mismatches'][:3]}"
            )

    official_query_sets = []
    for path in official_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        official_query_sets.append(
            {
                str(row.get("query_id"))
                for row in (payload.get("logs") or [])
                if row.get("query_id") is not None
            }
        )
    official_query_overlap_n = len(
        official_query_sets[0] & official_query_sets[1]
    )

    records = current_records(output_dir / "predictions.jsonl", config_hash)
    completeness = experiment_completeness(records, args)
    repeat_rows = per_repeat_metrics(records)
    aggregate = aggregate_ablation(repeat_rows)
    components = component_statistics(records)
    latency = latency_summary(records)
    comparisons = bootstrap_comparisons(
        records, samples=args.bootstrap_samples, seed=args.seed
    )
    overlap_sensitivity = type2_overlap_sensitivity(records)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "config_hash": config_hash,
        "official_rounds": official,
        "per_repeat": repeat_rows,
        "ablation": aggregate,
        "components": components,
        "latency": latency,
        "paired_bootstrap": comparisons,
        "type2_overlap_sensitivity": overlap_sensitivity,
        "completeness": completeness,
        "official_round_query_overlap_n": official_query_overlap_n,
        "records": {
            "total": len(records),
            "completed": sum(row.get("status") == "completed" for row in records),
            "failed": sum(row.get("status") == "failed" for row in records),
            "infrastructure_failed": sum(
                row.get("status") == "infrastructure_failed"
                for row in records
            ),
        },
        "evidence_policy": {
            "official_rounds": "organizer-provided aggregate logs",
            "ablation": "retrospective public development-set experiment",
            "other_teams": "omitted; no organizer-published leaderboard supplied",
            "hidden_case_studies": "forbidden",
        },
    }
    atomic_json(metrics_dir / "summary.json", summary)
    write_csv(metrics_dir / "per_repeat.csv", repeat_rows)
    write_csv(metrics_dir / "ablation.csv", aggregate)
    write_csv(metrics_dir / "component_stats.csv", components)
    write_csv(metrics_dir / "latency.csv", latency)
    write_csv(metrics_dir / "paired_bootstrap.csv", comparisons)
    write_csv(metrics_dir / "type2_overlap_sensitivity.csv", overlap_sensitivity)
    write_csv(metrics_dir / "completeness.csv", completeness["matrix"])
    atomic_json(metrics_dir / "quality_gate.json", completeness)

    official_rows = official_table_rows(official)
    write_table_bundle(
        tables_dir / "official_results",
        official_rows,
        [
            "Round",
            "N",
            "Total",
            "Type 1 points",
            "T1 answer (%)",
            "T1 premise F1 (%)",
            "T1 combined (%)",
            "T1 full exact (%)",
            "Type 2 points",
            "T2 strict (%)",
            "Time bonus",
            "Data correctness",
        ],
    )
    official_latency = official_latency_rows(official)
    write_table_bundle(
        tables_dir / "official_latency",
        official_latency,
        [
            "Round",
            "Group",
            "N",
            "Mean (s)",
            "Std (s)",
            "Median (s)",
            "P90 (s)",
            "P95 (s)",
            "Min (s)",
            "Max (s)",
        ],
    )
    t1_rows = ablation_table_rows(aggregate, "type1")
    write_table_bundle(
        tables_dir / "ablation_type1",
        t1_rows,
        [
            "Variant",
            "Repeats",
            "Answer mean (%)",
            "Answer SD (pp)",
            "Premise F1 (%)",
            "Combined (%)",
            "Full correct (%)",
        ],
    )
    t2_rows = ablation_table_rows(aggregate, "type2")
    write_table_bundle(
        tables_dir / "ablation_type2",
        t2_rows,
        [
            "Variant",
            "Repeats",
            "Answer mean (%)",
            "Answer SD (pp)",
            "Unit mean (%)",
            "Strict mean (%)",
            "Strict SD (pp)",
        ],
    )
    write_table_bundle(
        tables_dir / "solver_statistics",
        components,
        [
            "track",
            "variant",
            "n",
            "eligible",
            "called",
            "codegen_success",
            "first_execution_success",
            "repair_triggered",
            "repair_execution_success",
            "repair_success_rate",
            "repair_task_correct",
            "repair_task_success_rate",
            "final_accepted",
            "failed",
            "failure_reasons",
            "execution_timeouts",
            "success_rate",
            "correct_among_accepted",
            "task_correct_among_successful_rate",
        ],
    )
    write_table_bundle(
        tables_dir / "ablation_latency",
        latency,
        [
            "track",
            "variant",
            "scheduled_n",
            "completed_n",
            "failed_n",
            "infrastructure_failed_n",
            "mean_s",
            "std_s",
            "median_s",
            "p90_s",
            "p95_s",
            "min_s",
            "max_s",
            "sla_over_60_rate",
            "observed_timeout_n",
        ],
    )
    write_table_bundle(
        tables_dir / "type2_overlap_sensitivity",
        overlap_sensitivity,
        [
            "variant",
            "repeat",
            "n_all",
            "strict_accuracy_all",
            "n_without_DDT361",
            "strict_accuracy_without_DDT361",
            "overlap_case_correct",
        ],
    )

    cases = select_case_studies(records)
    atomic_json(cases_dir / "case_studies.json", cases)
    (cases_dir / "case_studies.md").write_text(
        case_studies_markdown(cases), encoding="utf-8"
    )
    generate_architecture(output_dir, logger)

    readiness_banner = (
        "> **PAPER-READY:** the full requested matrix is complete and has no "
        "failed/infrastructure-failed jobs."
        if completeness["paper_ready"]
        else "> **NOT PAPER-READY:** the requested full matrix is incomplete, "
        "is only a smoke/dry subset, or contains failed jobs. Resume/fix the run "
        "before copying controlled-experiment tables into the paper."
    )
    report_lines = [
        "# EXACT 2026 Paper Experiment Results",
        "",
        readiness_banner,
        "",
        f"Completeness: {completeness['completed_total']}/"
        f"{completeness['expected_total']} logical jobs completed; "
        f"ordinary failures={completeness['failed_total']}; "
        f"infrastructure failures={completeness['infrastructure_failed_total']}.",
        "",
        "## Evidence labels",
        "",
        "- Official round values are recomputed only from organizer-provided aggregate logs.",
        "- Ablations are retrospective public-data experiments: an undeclared-split "
        "Type-1 corpus and the public Type-2 dev split, not unseen-test results.",
        "- Other-team comparison is omitted because no organizer-published leaderboard was supplied.",
        "- Hidden evaluation questions are never copied into case-study artifacts.",
        "",
        "## Official results",
        "",
        markdown_table(
            official_rows,
            [
                "Round",
                "N",
                "Total",
                "Type 1 points",
                "T1 answer (%)",
                "T1 premise F1 (%)",
                "T1 combined (%)",
                "T1 full exact (%)",
                "Type 2 points",
                "T2 strict (%)",
                "Time bonus",
                "Data correctness",
            ],
        ),
        "Data correctness remains pending in the supplied logs; the portal totals "
        "must therefore be described as recorded/provisional official round scores.",
        "Official formulas: Type 1 = 25 × (answer accuracy + premise F1) / 2; "
        "Type 2 = 25 × strict accuracy; time bonus = Σ 0.1 × P1 × "
        "max(0, 1 − duration/60). The portal rounds only after using per-query "
        "values (Round 1: 39.377861... → 39.38, even though the separately "
        "displayed components sum to 39.37).",
        f"The supplied rounds use different sample versions and have "
        f"{official_query_overlap_n} query-ID overlap; Round 1→2 differences are "
        "descriptive, not paired or causal estimates.",
        "",
        "## Type 1 ablation",
        "",
        markdown_table(
            t1_rows,
            [
                "Variant",
                "Repeats",
                "Answer mean (%)",
                "Answer SD (pp)",
                "Premise F1 (%)",
                "Combined (%)",
                "Full correct (%)",
            ],
        ),
        "Type-1 answer accuracy uses N=808 per full repeat. Premise F1, "
        "combined score, and full-correct use only the N=797 public records "
        "with non-empty premise annotations.",
        "## Type 2 ablation",
        "",
        markdown_table(
            t2_rows,
            [
                "Variant",
                "Repeats",
                "Answer mean (%)",
                "Answer SD (pp)",
                "Unit mean (%)",
                "Strict mean (%)",
                "Strict SD (pp)",
            ],
        ),
        "## Component statistics",
        "",
        markdown_table(
            components,
            [
                "track",
                "variant",
                "called",
                "first_execution_success",
                "repair_triggered",
                "repair_execution_success",
                "repair_success_rate",
                "repair_task_correct",
                "repair_task_success_rate",
                "final_accepted",
                "failed",
                "failure_reasons",
                "success_rate",
                "correct_among_accepted",
            ],
        ),
        "Execution success and benchmark correctness are reported separately. "
        "Z3/PAL success means final accepted executable output divided by logical calls; "
        "repair execution success means executable repaired output divided by "
        "repair activations; repair task success additionally requires the final "
        "benchmark answer to be correct. Counts pool all configured repeats.",
        "",
        "## Official reported latency",
        "",
        markdown_table(
            official_latency,
            [
                "Round",
                "Group",
                "N",
                "Mean (s)",
                "Std (s)",
                "Median (s)",
                "P90 (s)",
                "P95 (s)",
                "Min (s)",
                "Max (s)",
            ],
        ),
        "These are organizer-reported per-request end-to-end durations from "
        "`duration_seconds`; they are not model-only inference time.",
        "",
        "## Controlled ablation latency",
        "",
        markdown_table(
            latency,
            [
                "track",
                "variant",
                "scheduled_n",
                "completed_n",
                "failed_n",
                "infrastructure_failed_n",
                "mean_s",
                "std_s",
                "median_s",
                "p90_s",
                "p95_s",
                "min_s",
                "max_s",
                "sla_over_60_rate",
                "observed_timeout_n",
            ],
        ),
        "Accuracy runs may reuse paired cached neural stages across variants. "
        "The latency table uses one separate uncached, no-retry stratified "
        "profile with telemetry buffered until the pipeline timer stops. It is "
        "application-pipeline latency, not model-only inference latency. "
        "`sla_over_60_rate` is merely the share of successful records exceeding "
        "60 s; observed timeouts are counted separately.",
        "",
        "## Reproducibility caveats",
        "",
        "- Type 1 public data has no declared train/dev/test split.",
        "- Type 2 metrics retain every public dev example in the denominator.",
        "- Formula KB example text exactly overlaps public dev item DDT361; "
        "the main denominator remains 200 and a with/without-DDT361 sensitivity "
        "table is generated.",
        "- The paper runner uses validated, scrubbed child processes with a hard "
        "timeout; these are not a security sandbox. The official production "
        "snapshot used different in-process/thread executors.",
        "- A 4-bit Colab run is a non-parity model condition and must be labeled as such.",
        "",
        "See `cases/case_studies.md` and `figures/architecture.{png,pdf,mmd}`.",
        "",
    ]
    (output_dir / "paper_results.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )
    ready_marker = output_dir / "PAPER_READY"
    if completeness["paper_ready"]:
        ready_marker.write_text(
            "Full matrix complete; see metrics/quality_gate.json.\n",
            encoding="utf-8",
        )
    elif ready_marker.exists():
        ready_marker.unlink()
    return summary


def preflight_public_data(
    type1: list[PublicExample],
    type2: list[PublicExample],
) -> dict[str, Any]:
    t1_mcq = sum(item.metadata.get("format") == "mcq" for item in type1)
    t1_ynu = sum(item.metadata.get("format") == "ynu" for item in type1)
    t1_eligible = sum(bool(item.metadata.get("z3_eligible")) for item in type1)
    t1_annotated = sum(
        bool(item.metadata.get("premise_annotation_available")) for item in type1
    )
    t1_letter_answers = sum(
        normalize_logic_answer(item.gold_answer) in {"A", "B", "C", "D"}
        for item in type1
    )
    prefixes: dict[str, int] = defaultdict(int)
    for item in type2:
        prefixes[str(item.metadata.get("prefix"))] += 1
    observed = {
        "type1_total": len(type1),
        "type1_mcq": t1_mcq,
        "type1_ynu": t1_ynu,
        "type1_z3_eligible": t1_eligible,
        "type1_premise_annotated": t1_annotated,
        "type1_letter_answers": t1_letter_answers,
        "type2_total": len(type2),
        "type2_prefixes": dict(sorted(prefixes.items())),
    }
    expected = {
        "type1_total": 808,
        # 360 questions have an explicit A-D option layout. Only 241 have a
        # letter gold answer; 119 option-layout questions are labeled Unknown.
        "type1_mcq": 360,
        "type1_ynu": 448,
        "type1_z3_eligible": 553,
        "type1_premise_annotated": 797,
        "type1_letter_answers": 241,
        "type2_total": 200,
    }
    mismatches = {
        key: {"expected": value, "observed": observed.get(key)}
        for key, value in expected.items()
        if observed.get(key) != value
    }
    if mismatches:
        raise AssertionError(f"Public dataset invariants changed: {mismatches}")
    return observed


def prepare_semantic_rag_on_cpu(
    disabled: bool,
    logger: logging.Logger,
    embedding_model: str,
    embedding_model_revision: str,
) -> dict[str, Any]:
    if disabled:
        os.environ["FORMULA_RAG_DISABLE_SEMANTIC"] = "1"
        logger.warning("Semantic FAISS retrieval disabled; keyword retrieval remains.")
        return {"enabled": False, "status": "disabled_by_cli"}
    try:
        os.environ.pop("FORMULA_RAG_DISABLE_SEMANTIC", None)
        os.environ["FORMULA_RAG_EMBEDDING_MODEL"] = embedding_model
        os.environ["FORMULA_RAG_EMBEDDING_REVISION"] = embedding_model_revision
        from pipeline.type2 import formula_rag

        formula_rag._ensure_faiss_loaded()
        model = getattr(formula_rag, "_faiss_model", None)
        if model is not None and hasattr(model, "to"):
            model.to("cpu")
        status = "loaded" if getattr(formula_rag, "_faiss_index", None) is not None else "fallback"
        logger.info("Semantic formula retrieval status=%s (embedding model on CPU).", status)
        return {
            "enabled": True,
            "status": status,
            "embedding_device": "cpu",
            "embedding_model": embedding_model,
            "embedding_model_revision": embedding_model_revision,
        }
    except Exception as exc:
        logger.warning("Semantic RAG unavailable; keyword fallback will be used: %s", exc)
        return {"enabled": True, "status": "fallback", "error": str(exc)}


def warmup_reasoner(reasoner: Any, backend: str, logger: logging.Logger) -> dict[str, Any]:
    started = time.perf_counter()
    served_models: list[str] = []
    if backend == "openai" and not reasoner.check_server():
        raise RuntimeError(
            f"LLM endpoint is not reachable at {safe_url(reasoner.api_base)}"
        )
    if backend == "openai":
        try:
            served_models = [
                str(item.id)
                for item in reasoner._get_client().models.list().data
            ]
        except Exception:
            served_models = []
    text = reasoner._chat(
        "You are a concise assistant.",
        "Reply with exactly: READY",
        max_tokens=8,
        temperature=0.0,
    )
    duration = time.perf_counter() - started
    if not text:
        raise RuntimeError("LLM warm-up returned an empty response.")
    logger.info("LLM warm-up completed in %.2fs.", duration)
    return {
        "completed_at": utc_now(),
        "duration_s": duration,
        "response_nonempty": True,
        "served_model_ids": served_models,
        "resolved_model_revision": getattr(
            reasoner, "resolved_model_revision", None
        ),
    }


def sanitize_args(args: argparse.Namespace) -> dict[str, Any]:
    result = dict(vars(args))
    if result.get("api_base"):
        result["api_base"] = safe_url(str(result["api_base"]))
    return result


def choose_output_dir(
    desired: Path,
    config_hash: str,
    logger: logging.Logger,
    *,
    resume: bool,
) -> Path:
    manifest_path = desired / "run_config.json"
    if not manifest_path.exists() and (resume or not desired.exists()):
        return desired
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        existing = {}
    if existing.get("config_hash") == config_hash and resume:
        return desired
    if resume:
        alternative = desired.with_name(
            desired.name + "_" + config_hash[:12]
        )
        alternative_manifest = alternative / "run_config.json"
        if alternative_manifest.exists():
            try:
                alternative_config = json.loads(
                    alternative_manifest.read_text(encoding="utf-8")
                )
            except Exception:
                alternative_config = {}
            if alternative_config.get("config_hash") == config_hash:
                return alternative
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            alternative = desired.with_name(
                desired.name
                + "_"
                + config_hash[:12]
                + "_"
                + timestamp
            )
        elif alternative.exists() and (
            not alternative.is_dir() or any(alternative.iterdir())
        ):
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            alternative = desired.with_name(
                desired.name
                + "_"
                + config_hash[:12]
                + "_"
                + timestamp
            )
    else:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        alternative = desired.with_name(
            desired.name + "_" + config_hash[:12] + "_" + timestamp
        )
    logger.warning(
        "Using %s instead of appending incompatible or explicitly non-resumed "
        "records to %s.",
        alternative,
        desired,
    )
    return alternative


def run_self_tests(repo_root: Path) -> None:
    t1 = load_type1_public(repo_root / "Logic_Based_Educational_Queries.json")
    t2 = load_type2_public(repo_root / "data/physics/physics_dev.csv")
    preflight_public_data(t1, t2)
    encoder_manifest = json.loads(
        (repo_root / "data/formula_index/encoder.json").read_text(encoding="utf-8")
    )
    assert encoder_manifest["model"] == DEFAULT_EMBEDDING_MODEL
    assert encoder_manifest["revision"] == DEFAULT_EMBEDDING_REVISION
    assert encoder_manifest["embedding_dimension"] == 384
    from pipeline.type2 import formula_rag

    os.environ["FORMULA_RAG_DISABLE_SEMANTIC"] = "1"
    formula_rag._faiss_index = None
    formula_rag._faiss_docs = None
    formula_rag._faiss_model = None
    formula_rag._ensure_faiss_loaded("/path/that/must/not/be/read")
    assert formula_rag._faiss_index is None
    os.environ.pop("FORMULA_RAG_DISABLE_SEMANTIC", None)
    assert all(
        item.options == ["Yes", "No", "Uncertain"]
        for item in t1
        if item.metadata.get("format") == "ynu"
    )
    assert all(
        not item.options
        for item in t1
        if item.metadata.get("format") == "mcq"
    )

    round1 = official_round_metrics(
        repo_root / "exact_eval_round1_Cay_Nha_La_Vuon.json"
    )
    round2 = official_round_metrics(
        repo_root / "exact_eval_round2_Cay_Nha_La_Vuon.json"
    )
    assert round1["total_score"] == 39.38
    assert round2["total_score"] == 44.8
    assert abs(float(round1["type1_answer_accuracy"]) - 0.68) < 1e-12
    assert abs(float(round2["type1_answer_accuracy"]) - 0.88) < 1e-12
    assert not round1["p2_regression_mismatches"]
    assert not round2["p2_regression_mismatches"]
    assert not round1["type2_regression_mismatches"]
    assert not round2["type2_regression_mismatches"]
    assert not round1["score_regression_mismatches"]
    assert not round2["score_regression_mismatches"]

    t1_score = score_type1("A", [0, 2], "A", [0, 1, 2])
    assert t1_score["answer_correct"]
    assert abs(float(t1_score["premise_f1"]) - 0.8) < 1e-12

    t2_score = score_type2("0.4", "J", "400", "mJ")
    assert t2_score["answer_correct"]
    assert t2_score["unit_correct"]
    assert t2_score["strict_correct"]
    missing_unit_score = score_type2("0.4", "", "400", "mJ")
    assert missing_unit_score["answer_correct"]
    assert not missing_unit_score["unit_correct"]
    assert not missing_unit_score["strict_correct"]
    unit_score = score_type2("400", "mJ", "400", "mJ")
    assert unit_score["strict_correct"]
    assert score_type2("0.004524", "T", "4.524", "mT")["strict_correct"]
    assert score_type2("0.001", "kg", "1", "g")["strict_correct"]
    assert not score_type2("5", "V/m", "5", "N/C")["strict_correct"]
    unsupported_gold_units = {
        normalize_unit(component)
        for item in t2
        for component in split_semicolon(item.gold_unit)
        if normalize_unit(component) not in UNIT_FACTORS
        or normalize_unit(component) not in UNIT_FAMILIES
    }
    assert not unsupported_gold_units, unsupported_gold_units

    z3_code = """
from z3 import *
P = Bool('P')
s = Solver()
s.add(P)
solve_yes_no(s, P)
"""
    z3_output = safe_z3_execute(repo_root, z3_code, timeout=8)
    assert z3_output and "Yes" in z3_output
    assert safe_z3_execute(
        repo_root, "import os\nprint(os.environ)", timeout=2
    ) is None

    pal = safe_pal_execute(
        repo_root, "answer = 2 + 3\nunit = 'J'", timeout=5
    )
    assert pal == {"answer": "5", "unit": "J"}
    assert (
        safe_pal_execute(repo_root, "import os\nanswer = 5", timeout=2) is None
    )

    with tempfile.TemporaryDirectory(prefix="exact-paper-test-") as temp:
        root = Path(temp)
        writer = JsonlWriter(root / "test.jsonl", fsync=True)
        writer.write({"ok": 1})
        writer.close()
        with (root / "test.jsonl").open("a", encoding="utf-8") as handle:
            handle.write('{"partial":')
        assert list(read_jsonl(root / "test.jsonl")) == [{"ok": 1}]
        logger = setup_logging(root, verbose=False)
        generate_architecture(root, logger)
        assert (root / "figures/architecture.mmd").exists()

        desired = root / "resume-run"
        desired.mkdir()
        atomic_json(
            desired / "run_config.json",
            {"config_hash": "config-a"},
        )
        assert choose_output_dir(
            desired, "config-a", logger, resume=True
        ) == desired
        alternate = choose_output_dir(
            desired, "config-b-1234567890", logger, resume=True
        )
        assert alternate.name.endswith("config-b-123")
        alternate.mkdir()
        atomic_json(
            alternate / "run_config.json",
            {"config_hash": "config-b-1234567890"},
        )
        assert choose_output_dir(
            desired,
            "config-b-1234567890",
            logger,
            resume=True,
        ) == alternate
        assert choose_output_dir(
            desired, "config-a", logger, resume=False
        ) != desired

        checkpoint = root / "predictions.jsonl"
        checkpoint_writer = JsonlWriter(checkpoint)
        for status in ("failed", "completed"):
            checkpoint_writer.write(
                {
                    "config_hash": "config",
                    "phase": "accuracy",
                    "variant": "t1_full",
                    "repeat": 0,
                    "query_id": "dedupe",
                    "status": status,
                }
            )
        checkpoint_writer.close()
        assert len(current_records(checkpoint, "config")) == 1
        assert current_records(checkpoint, "config")[0]["status"] == "completed"
        assert len(completed_keys(checkpoint, "config")) == 1

        cache = StageCache(root / "cache.jsonl", enabled=True)
        event_writer = JsonlWriter(root / "events.jsonl")
        trace = QueryTrace(
            run_id="self-test",
            config_hash="config",
            phase="accuracy",
            track="type1",
            variant="t1_full",
            repeat=0,
            seed=2026,
            query_id="seed-cache",
            events_writer=event_writer,
            cache=cache,
            cache_enabled=True,
            code_timeout=1.0,
        )
        cache_key = stage_key(trace, "seed_stage", ("x",), {})
        cache.put(
            cache_key,
            {
                "status": "ok",
                "logical_duration_s": 0.1,
                "result": {"answer": "Yes"},
                "llm_calls_consumed": 1,
            },
        )

        class FakeReasoner(PaperReasonerMixin):
            pass

        fake = FakeReasoner()
        with trace_context(trace):
            cached_result = fake._record_public_method(
                "seed_stage",
                lambda value: {"unexpected": value},
                ("x",),
                {},
            )
        assert cached_result == {"answer": "Yes"}
        assert trace.llm_call_index == 1
        assert trace.next_llm_seed() == 2026 + 100_003
        trace.flush_events()

        failed_trace = dataclasses.replace(
            trace,
            query_id="infra-cache",
            stages=defaultdict(list),
            component_logs=[],
            llm_calls=[],
            z3={"executions": []},
            pal={"executions": []},
            flags={},
            artifacts={},
            infrastructure_error=None,
            llm_call_index=0,
            pending_events=[],
        )

        def infrastructure_fallback(value: str) -> dict[str, str]:
            active = current_trace()
            assert active is not None
            active.infrastructure_error = "TimeoutError: synthetic"
            active.next_llm_seed()
            return {"fallback": value}

        with trace_context(failed_trace):
            fake._record_public_method(
                "infra_stage",
                infrastructure_fallback,
                ("x",),
                {},
            )
        failed_key = stage_key(failed_trace, "infra_stage", ("x",), {})
        assert cache.get(failed_key) is None
        assert failed_trace.stages["infra_stage"][0]["status"] == (
            "infrastructure_error"
        )
        failed_trace.flush_events()
        event_writer.close()
        cache.close()

    print(
        "SELF-TEST PASS: loaders, official P2 regression, scorers, restricted "
        "Z3/PAL executors, JSONL recovery, and architecture generation."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Run all EXACT 2026 paper experiments from one Python file.",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "smoke", "dry-run", "official-only", "self-test"],
        default="full",
    )
    parser.add_argument("--tracks", choices=["both", "type1", "type2"], default="both")
    parser.add_argument(
        "--backend", choices=["auto", "openai", "transformers"], default="auto"
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("PAPER_LLM_BASE_URL", ""),
        help="OpenAI-compatible /v1 base URL; when omitted, use local Transformers.",
    )
    parser.add_argument(
        "--api-key-env",
        default="PAPER_LLM_API_KEY",
        help="Environment variable containing an optional endpoint API key.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--model-revision",
        default="main",
        help="HF revision; mutable names are resolved and pinned before the run.",
    )
    parser.add_argument(
        "--quantization",
        choices=["auto", "none", "4bit", "8bit"],
        default="auto",
    )
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1024,
        help="Global upper bound for each LLM stage's generated tokens.",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=120.0,
        help=(
            "Hard request timeout for endpoints; soft generation deadline for "
            "local Transformers."
        ),
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="SentenceTransformer encoder used by semantic formula retrieval.",
    )
    parser.add_argument(
        "--embedding-model-revision",
        default=DEFAULT_EMBEDDING_REVISION,
        help=(
            "Hugging Face revision for the semantic retrieval encoder. Mutable "
            "revisions are resolved to an immutable commit before execution."
        ),
    )
    parser.add_argument("--code-timeout", type=float, default=8.0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--deterministic-repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEEDS[0])
    parser.add_argument("--latency-samples", type=int, default=50)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--type1-limit", type=int, default=0)
    parser.add_argument("--type2-limit", type=int, default=0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument(
        "--cache-shared-stages",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--resume", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--disable-semantic-rag", action="store_true")
    parser.add_argument(
        "--install-deps", choices=["auto", "yes", "no"], default="auto"
    )
    parser.add_argument("--mount-drive", action="store_true")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--run-name", default="full_ablation")
    parser.add_argument(
        "--round1-log", default="exact_eval_round1_Cay_Nha_La_Vuon.json"
    )
    parser.add_argument(
        "--round2-log", default="exact_eval_round2_Cay_Nha_La_Vuon.json"
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.repeats < 1:
        raise ValueError("--repeats must be >= 1")
    if args.deterministic_repeats < 1:
        raise ValueError("--deterministic-repeats must be >= 1")
    if args.temperature < 0:
        raise ValueError("--temperature must be >= 0")
    if args.code_timeout <= 0 or args.llm_timeout <= 0:
        raise ValueError("Timeouts must be positive")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be >= 0")
    if args.progress_every <= 0:
        raise ValueError("--progress-every must be > 0")
    if args.type1_limit < 0 or args.type2_limit < 0:
        raise ValueError("Dataset limits must be >= 0")
    if args.latency_samples < 0:
        raise ValueError("--latency-samples must be >= 0")
    if args.bootstrap_samples < 1:
        raise ValueError("--bootstrap-samples must be >= 1")
    if args.max_tokens < 1:
        raise ValueError("--max-tokens must be >= 1")
    if args.backend == "openai" and not args.api_base:
        raise ValueError("--backend openai requires --api-base")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args)
    repo_root = find_repo_root(Path.cwd())
    os.chdir(repo_root)
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if args.mode == "smoke":
        args.type1_limit = args.type1_limit or 4
        args.type2_limit = args.type2_limit or 8
        args.repeats = 1
        args.deterministic_repeats = 1
        args.latency_samples = min(args.latency_samples, 2)
        args.bootstrap_samples = min(args.bootstrap_samples, 200)
        if args.run_name == "full_ablation":
            args.run_name = "smoke"

    # Self-test does not need a model backend or semantic RAG packages.
    if args.mode == "self-test":
        args.backend = "openai"
        args.api_base = args.api_base or "http://127.0.0.1:9/v1"
        args.disable_semantic_rag = True

    ensure_dependencies(args)
    if args.mode == "self-test":
        run_self_tests(repo_root)
        return 0

    bootstrap_output = Path(tempfile.gettempdir()) / "exact-paper-bootstrap"
    bootstrap_output.mkdir(parents=True, exist_ok=True)
    bootstrap_logger = setup_logging(bootstrap_output, args.verbose)
    maybe_mount_drive(args.mount_drive, bootstrap_logger)

    official_paths = [
        repo_root / args.round1_log,
        repo_root / args.round2_log,
    ]
    missing_official = [str(path) for path in official_paths if not path.exists()]
    if missing_official:
        raise FileNotFoundError(
            "The official aggregate logs are required but missing: "
            + ", ".join(missing_official)
            + ". Upload them in Colab or pass --round1-log and --round2-log."
        )
    official_source_manifest = [
        {"filename": path.name, "sha256": sha256_file(path)}
        for path in official_paths
    ]

    type1_all = load_type1_public(
        repo_root / "Logic_Based_Educational_Queries.json"
    )
    type2_all = load_type2_public(repo_root / "data/physics/physics_dev.csv")
    data_invariants = preflight_public_data(type1_all, type2_all)
    dataset_manifest = public_dataset_manifest(repo_root)
    source_manifest = code_source_manifest(repo_root)

    if args.type1_limit > 0:
        type1_examples = stratified_subset(type1_all, args.type1_limit, args.seed)
    else:
        type1_examples = type1_all
    if args.type2_limit > 0:
        type2_examples = stratified_subset(type2_all, args.type2_limit, args.seed)
    else:
        type2_examples = type2_all

    backend = resolve_backend(args)
    quantization = resolve_quantization(args, backend)
    accelerator = accelerator_identity(backend)
    resolved_model_revision = args.model_revision
    if backend == "transformers" and args.mode not in {"dry-run", "official-only"}:
        resolved_model_revision = resolve_hf_revision(
            args.model, args.model_revision, bootstrap_logger
        )
    resolved_embedding_model_revision = args.embedding_model_revision
    if not args.disable_semantic_rag and args.mode not in {"dry-run", "official-only"}:
        resolved_embedding_model_revision = resolve_hf_revision(
            args.embedding_model,
            args.embedding_model_revision,
            bootstrap_logger,
        )

    if args.mode in {"dry-run", "official-only"}:
        rag_status = {
            "enabled": not args.disable_semantic_rag,
            "status": "not_initialized_in_non_execution_mode",
            "embedding_model": args.embedding_model,
            "embedding_model_revision": resolved_embedding_model_revision,
        }
    else:
        rag_status = prepare_semantic_rag_on_cpu(
            args.disable_semantic_rag,
            bootstrap_logger,
            args.embedding_model,
            resolved_embedding_model_revision,
        )
        if (
            not args.disable_semantic_rag
            and rag_status.get("status") != "loaded"
        ):
            raise RuntimeError(
                "Semantic RAG was requested but did not load successfully. "
                "The run is stopped to avoid mixing retrieval conditions on "
                "resume. Fix the dependency/network issue or explicitly pass "
                "--disable-semantic-rag for a hashed keyword-only condition."
            )

    config_payload = {
        "schema_version": SCHEMA_VERSION,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "git": git_metadata(repo_root),
        "code_source_manifest": source_manifest,
        "official_source_manifest": official_source_manifest,
        "mode": args.mode,
        "tracks": args.tracks,
        "backend": backend,
        "api_base": safe_url(args.api_base) if args.api_base else None,
        "model": args.model,
        "requested_model_revision": args.model_revision,
        "resolved_model_revision": resolved_model_revision,
        "embedding_model": args.embedding_model,
        "requested_embedding_model_revision": args.embedding_model_revision,
        "resolved_embedding_model_revision": resolved_embedding_model_revision,
        "quantization": quantization,
        "accelerator": accelerator,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "llm_timeout": args.llm_timeout,
        "max_retries": args.max_retries,
        "repeats": args.repeats,
        "deterministic_repeats": args.deterministic_repeats,
        "seed": args.seed,
        "type1_ids": [item.query_id for item in type1_examples],
        "type2_ids": [item.query_id for item in type2_examples],
        "dataset_manifest": dataset_manifest,
        "variants": {
            "type1": TYPE1_VARIANTS,
            "type2": TYPE2_VARIANTS,
        },
        "scoring": {
            "type1_premise": "set-F1; unannotated excluded",
            "type2_numeric_relative_tolerance": 0.02,
            "missing_unparseable": "incorrect; never skipped",
            "strict_unit": (
                "prefix-normalized canonical family; scaled equivalents accepted, "
                "N/C and V/m remain distinct"
            ),
        },
        "executor": {
            "restricted_subprocess": True,
            "hard_timeout_seconds": args.code_timeout,
        },
        "cache_shared_stages": args.cache_shared_stages,
        "latency_samples": args.latency_samples,
        "bootstrap_samples": args.bootstrap_samples,
        "semantic_rag": rag_status,
    }
    config_hash = stable_hash(config_payload)
    desired_output = output_root(repo_root, args)
    output_dir = choose_output_dir(
        desired_output,
        config_hash,
        bootstrap_logger,
        resume=args.resume,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(output_dir, args.verbose)
    run_id = f"{args.run_name}-{config_hash[:12]}"
    existing_run_config: dict[str, Any] = {}
    existing_config_path = output_dir / "run_config.json"
    if existing_config_path.exists():
        try:
            existing_run_config = json.loads(
                existing_config_path.read_text(encoding="utf-8")
            )
        except Exception:
            existing_run_config = {}
    session_started_at = utc_now()

    work_estimate = estimate_work(
        type1_examples,
        type2_examples,
        args.repeats,
        args.deterministic_repeats,
        args.latency_samples,
    )
    run_config = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": existing_run_config.get("created_at", session_started_at),
        "sessions": [
            *(existing_run_config.get("sessions") or []),
            {
                "started_at": session_started_at,
                "resume": args.resume,
                "accelerator": accelerator,
            },
        ],
        "config_hash": config_hash,
        "arguments": sanitize_args(args),
        "resolved": {
            "repo_root": str(repo_root),
            "output_dir": str(output_dir),
            "backend": backend,
            "quantization": quantization,
            "requested_model_revision": args.model_revision,
            "resolved_model_revision": resolved_model_revision,
            "embedding_model": args.embedding_model,
            "requested_embedding_model_revision": args.embedding_model_revision,
            "resolved_embedding_model_revision": resolved_embedding_model_revision,
            "accelerator": accelerator,
        },
        "data_invariants": data_invariants,
        "dataset_manifest": dataset_manifest,
        "official_source_manifest": official_source_manifest,
        "code_source_manifest": source_manifest,
        "semantic_rag": rag_status,
        "work_estimate": work_estimate,
        "ablation_definitions": {
            "t1_cot_only": "CoT + deterministic post-processing; Z3 disabled",
            "t1_cot_z3_no_repair": "CoT + exemplar-augmented Z3; repair disabled",
            "t1_full": (
                "Current Type-1 control flow with at most one Z3 repair; "
                "paper-owned non-production executor"
            ),
            "t2_cot_only": "Direct raw-question CoT; no parser/RAG/PAL",
            "t2_rag_solver": "Regex parser + formula RAG + deterministic solvers",
            "t2_rag_solver_pal": "T2-B + first-pass PAL; no repair/CoT",
            "t2_full": "LLM-augmented parser + RAG/solvers + PAL + one repair + CoT",
            "t2_full_e2e": "T2-D plus LLM presentation explainer; latency only",
        },
    }
    atomic_json(output_dir / "run_config.json", run_config)
    atomic_json(output_dir / "dataset_manifest.json", dataset_manifest)
    environment = environment_metadata(repo_root, args, backend, quantization)
    environment["resolved_model_revision"] = resolved_model_revision
    environment["resolved_embedding_model_revision"] = (
        resolved_embedding_model_revision
    )
    environment["experiment_accelerator_identity"] = accelerator
    atomic_json(output_dir / "environment.json", environment)
    sessions_writer = JsonlWriter(output_dir / "sessions.jsonl", fsync=True)
    sessions_writer.write(
        {
            "session_started_at": session_started_at,
            "run_id": run_id,
            "config_hash": config_hash,
            "resume": args.resume,
            "accelerator": accelerator,
        }
    )
    sessions_writer.close()
    logger.info("Output: %s", output_dir)
    logger.info("Work estimate: %s", canonical_json(work_estimate))

    if quantization in {"4bit", "8bit"}:
        logger.warning(
            "This is a quantized Colab condition, not FP16 production parity. "
            "The generated report will label it explicitly."
        )

    if args.mode in {"dry-run", "official-only"}:
        generate_reports(
            repo_root=repo_root,
            output_dir=output_dir,
            config_hash=config_hash,
            args=args,
            logger=logger,
        )
        print(f"{args.mode} complete: {output_dir}")
        return 0

    cache = StageCache(
        output_dir / "stage_cache.jsonl", enabled=args.cache_shared_stages
    )
    api_key = os.environ.get(args.api_key_env, "not-needed")
    Reasoner = build_reasoner_class()
    reasoner = Reasoner(
        backend=backend,
        api_base=args.api_base,
        api_key=api_key,
        model_name=args.model,
        model_revision=resolved_model_revision,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        llm_timeout=args.llm_timeout,
        quantization=quantization,
        cache=cache,
        logger=logger,
    )
    restore_hooks = install_reasoner_hooks(reasoner, logger)
    try:
        previous_warmup: dict[str, Any] = {}
        if (output_dir / "warmup.json").exists():
            try:
                previous_warmup = json.loads(
                    (output_dir / "warmup.json").read_text(encoding="utf-8")
                )
            except Exception:
                previous_warmup = {}
        warmup = warmup_reasoner(reasoner, backend, logger)
        previous_revision = previous_warmup.get("resolved_model_revision")
        current_revision = warmup.get("resolved_model_revision")
        previous_models = previous_warmup.get("served_model_ids") or []
        current_models = warmup.get("served_model_ids") or []
        if previous_revision and current_revision and previous_revision != current_revision:
            raise RuntimeError(
                "Refusing to resume with a different resolved model revision: "
                f"{previous_revision} != {current_revision}"
            )
        if previous_models and current_models and previous_models != current_models:
            raise RuntimeError(
                "Refusing to resume because the endpoint's served model IDs "
                f"changed: {previous_models} != {current_models}"
            )
        atomic_json(output_dir / "warmup.json", warmup)
        environment["resolved_model_revision"] = warmup.get(
            "resolved_model_revision"
        )
        atomic_json(output_dir / "environment.json", environment)
        run_matrix(
            repo_root=repo_root,
            output_dir=output_dir,
            args=args,
            run_id=run_id,
            config_hash=config_hash,
            reasoner=reasoner,
            cache=cache,
            type1_examples=type1_examples,
            type2_examples=type2_examples,
            logger=logger,
        )
        summary = generate_reports(
            repo_root=repo_root,
            output_dir=output_dir,
            config_hash=config_hash,
            args=args,
            logger=logger,
        )
        logger.info("Completed %s records.", summary["records"]["completed"])
    finally:
        restore_hooks()
        cache.close()

    print(f"Paper experiment artifacts: {output_dir}")
    print(f"Main report: {output_dir / 'paper_results.md'}")
    if STOP_REQUESTED:
        print("Run stopped safely after checkpoint; execute the same command to resume.")
        return 130
    if args.mode == "full" and not summary["completeness"]["paper_ready"]:
        print(
            "NOT PAPER-READY: some requested jobs are missing or failed. "
            "Inspect metrics/quality_gate.json and rerun the same command."
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
