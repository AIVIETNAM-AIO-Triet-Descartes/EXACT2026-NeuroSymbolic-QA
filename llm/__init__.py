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
