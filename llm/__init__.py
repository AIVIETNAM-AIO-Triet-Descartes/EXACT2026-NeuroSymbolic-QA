"""
LLM module — config-driven shared LLMReasoner singleton.

`get_shared_reasoner()` builds ONE LLMReasoner from configs/config.yaml:
  - `llm.active` selects a profile;
  - `profiles[active]` (api_base, model_name) is merged OVER the shared `llm.*`
    keys (api_key, temperature, max_tokens).
Switching dev (llama.cpp) <-> prod (vLLM) is therefore CONFIG-ONLY — flip
`llm.active`. Every pipeline LLM call (both tracks) goes through this one seam,
so no track code changes when the backend changes.
"""

from pathlib import Path
from functools import lru_cache

import yaml
from loguru import logger

from llm.llm_reasoner import LLMReasoner

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "config.yaml"


def _load_llm_config() -> dict:
    """Read configs/config.yaml and merge the active profile over shared keys."""
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"[LLM] cannot read {_CONFIG_PATH}: {e}; using defaults")
        return {}

    llm = cfg.get("llm", {}) or {}
    merged = {k: v for k, v in llm.items() if k not in ("profiles", "active")}
    active = llm.get("active")
    profile = (llm.get("profiles") or {}).get(active, {}) if active else {}
    merged.update(profile)   # profile (api_base, model_name) wins
    return merged


@lru_cache(maxsize=1)
def get_shared_reasoner() -> LLMReasoner:
    """Config-driven singleton LLMReasoner (one per process)."""
    c = _load_llm_config()
    reasoner = LLMReasoner(
        api_base=c.get("api_base", "http://localhost:8000/v1"),
        model_name=c.get("model_name", "Qwen/Qwen2.5-7B-Instruct"),
        api_key=c.get("api_key", "not-needed"),
        temperature=c.get("temperature", 0.1),
        max_tokens=c.get("max_tokens", 1024),
    )
    logger.info(
        f"[LLM] shared reasoner → {reasoner.api_base} ({reasoner.model_name})"
    )
    return reasoner


@lru_cache(maxsize=1)
def llm_server_available() -> bool:
    """Real health check (cached per process): does the server answer /v1/models?"""
    try:
        return get_shared_reasoner().check_server()
    except Exception as e:
        logger.warning(f"[LLM] availability check failed: {e}")
        return False
