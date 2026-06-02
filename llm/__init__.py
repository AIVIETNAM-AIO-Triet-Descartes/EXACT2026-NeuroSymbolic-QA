import os
import yaml
from loguru import logger
from llm.llm_reasoner import LLMReasoner, create_reasoner


def _load_config() -> dict:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "configs", "config.yaml",
    )
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_llm_cfg(cfg: dict) -> dict:
    """
    Resolve the active LLM backend config.

    If `llm.profiles` exists, merge the profile selected by `llm.active`
    over the shared `llm` keys (profile values win). Backward-compatible:
    a flat `llm` block with no `profiles` is returned as-is.
    """
    llm = dict(cfg.get("llm", {}))
    profiles = llm.get("profiles")
    if not profiles:
        return llm  # legacy flat config

    active = llm.get("active", "dev")
    if active not in profiles:
        raise KeyError(
            f"llm.active='{active}' not found in profiles {list(profiles)}. "
            f"Check configs/config.yaml."
        )
    resolved = {k: v for k, v in llm.items() if k not in ("profiles", "active")}
    resolved.update(profiles[active])
    resolved["_active"] = active
    return resolved


config = _load_config()

_reasoner_instance = None


def get_shared_reasoner() -> LLMReasoner:
    global _reasoner_instance
    if _reasoner_instance is None:
        llm_cfg = _resolve_llm_cfg(config)
        logger.info(
            f"[LLM_CONFIG] profile='{llm_cfg.get('_active', 'flat')}' "
            f"api_base={llm_cfg['api_base']} model={llm_cfg['model_name']}"
        )
        _reasoner_instance = create_reasoner(
            base_url=llm_cfg["api_base"],
            model_name=llm_cfg["model_name"],
            api_key=llm_cfg.get("api_key", "not-needed"),
            temperature=llm_cfg.get("temperature", 0.1),
        )
    return _reasoner_instance


# ── vLLM server health-check singleton (Fix B, 2026-06-02) ───────────────────
# Shared across all pipeline nodes that call LLM (physics_parser, explainer,
# cot_solver, etc.). Probe once per process, cache result for the batch.
#
# None  = not yet probed
# True  = server responded OK on last probe
# False = server was DOWN (LLM calls will be skipped by callers)

_LLM_SERVER_OK: bool | None = None


def llm_server_available() -> bool:
    """
    Probe vLLM server reachability once per process, cache the result.

    Uses a lightweight GET /v1/models request with a 3 s connect timeout
    (matches the connect timeout in LLMReasoner._get_client / Fix A).

    Returns True if server is up, False otherwise. Subsequent calls in the
    same process return the cached value immediately without network I/O.

    The cache is intentionally *not* reset on failure — if the server is down
    at the start of a batch we assume it stays down for the whole batch.
    Call reset_llm_server_cache() (tests only) to force a re-probe.

    Import pattern for pipeline nodes:
        from llm import llm_server_available
        if llm_server_available():
            reasoner = get_shared_reasoner()
            ...
    """
    global _LLM_SERVER_OK
    if _LLM_SERVER_OK is not None:
        return _LLM_SERVER_OK

    try:
        import httpx
        llm_cfg = _resolve_llm_cfg(config)
        base_url = llm_cfg.get("api_base", "http://localhost:8000/v1")
        models_url = base_url.rstrip("/").removesuffix("/v1") + "/v1/models"
        with httpx.Client(timeout=httpx.Timeout(3.0, connect=3.0)) as client:
            resp = client.get(models_url)
        _LLM_SERVER_OK = resp.status_code == 200
    except Exception as e:
        logger.warning(
            f"[LLM_HEALTH] vLLM probe failed ({e}); "
            f"LLM calls disabled for this batch"
        )
        _LLM_SERVER_OK = False

    status = "UP" if _LLM_SERVER_OK else "DOWN"
    logger.info(f"[LLM_HEALTH] vLLM server: {status} (cached for process lifetime)")
    return _LLM_SERVER_OK


def reset_llm_server_cache() -> None:
    """Force re-probe on next llm_server_available() call. Intended for tests only."""
    global _LLM_SERVER_OK
    _LLM_SERVER_OK = None
